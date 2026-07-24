"""
bin_packer.py — v4.0 三站接力第二站
装箱引擎：卡片列表 → 行列分配

核心逻辑：
1. 计算每张卡片的列型约束（max_slots_in_row）
2. 贪心遍历，分配到行
3. 溢出时合并相邻 low list 卡片
4. 输出：rows[M]，每行含 1-3 个卡片 + 列型信息

所有决策确定性，无 LLM 参与。
"""
from typing import List, Dict, Tuple, Optional

# ============================================================
# 画布参数
# ============================================================
CANVAS = {
    "portrait": {
        "max_rows": 5,
        "max_cols": 2,
        "row_height": 232,
        "hero_height": 280,
        "width": 1080,
        "height": 1440,
    },
    "landscape": {
        "max_rows": 4,
        "max_cols": 3,
        "row_height": 210,
        "hero_height": 240,
        "width": 1920,
        "height": 1080,
    },
}


# ============================================================
# 第一层：列型约束计算
# ============================================================

def normalize_primary(cards: List[dict]) -> List[dict]:
    """
    强制第 1 张卡片为 primary，其他卡片不能是 primary。

    处理 4 种情况：
    - 0 张 primary → 第 1 张改 primary
    - 1 张且是第 1 张 → 不动
    - 1 张但不是第 1 张 → 原 primary 降 secondary，第 1 张升 primary
    - ≥2 张 primary → 只留第 1 张，其他全降 secondary

    返回处理后的 cards（原列表不修改）。
    """
    if not cards:
        return cards

    result = [dict(c) for c in cards]  # 浅拷贝

    # 找所有 primary 的索引
    primary_indices = [i for i, c in enumerate(result) if c.get("semantic_weight") == "primary"]

    if not primary_indices:
        # 0 张 primary → 第 1 张改 primary
        result[0]["semantic_weight"] = "primary"
    elif len(primary_indices) == 1 and primary_indices[0] == 0:
        # 1 张且是第 1 张 → 不动
        pass
    else:
        # 1 张但不是第 1 张，或 ≥2 张 primary → 全降 secondary，第 1 张升 primary
        for i in primary_indices:
            result[i]["semantic_weight"] = "secondary"
        result[0]["semantic_weight"] = "primary"

    return result


# ============================================================
# 1.5 层：主动预合并（防溢出）
# ============================================================

def _can_pre_merge(card_a: dict, card_b: dict) -> bool:
    """
    两张卡片是否可以 preMerge。
    比 mergeOverflow 更严格：
    - 都 low density（用有效密度判定）
    - 都 list 型
    - 都不是 primary
    - 不是 relation 配对（配对留给装箱的拼车逻辑）
    - 合并后 items ≤ 6
    """
    if _effective_density(card_a) != "low" or _effective_density(card_b) != "low":
        return False
    if card_a.get("content_shape") != "list" or card_b.get("content_shape") != "list":
        return False
    if card_a.get("semantic_weight") == "primary" or card_b.get("semantic_weight") == "primary":
        return False
    # 有 relation 的不合并（留给拼车逻辑）
    if card_a.get("relation") or card_b.get("relation"):
        return False
    total_items = len(card_a.get("items", [])) + len(card_b.get("items", []))
    if total_items > 6:
        return False
    return True


def pre_merge(cards: List[dict], canvas_type: str) -> List[dict]:
    """
    卡片过多时主动合并相邻卡片。

    触发阈值：cards > max_rows + 1
      - 竖版：cards > 6 时触发
      - 横版：cards > 5 时触发

    合并策略：
    - 遍历相邻卡片对，找可合并且总 items 最少的一对
    - 合并后 density 保持 low（如果总 items ≤ 6），让卡片还能参与拼车
    - 合并后 content_shape = list
    """
    if not cards:
        return cards

    canvas = CANVAS[canvas_type]
    max_rows = canvas["max_rows"]
    # 新阈值：medium 能拼车后，竖版 9 张 / 横版 10 张以内无需合并
    threshold = max_rows * 2 if canvas_type == "portrait" else max_rows * 3

    result = [dict(c) for c in cards]

    while len(result) > threshold:
        # 找所有可合并的相邻对
        best_idx = None
        best_items_count = 999
        for i in range(len(result) - 1):
            if _can_pre_merge(result[i], result[i + 1]):
                total = len(result[i].get("items", [])) + len(result[i + 1].get("items", []))
                if total < best_items_count:
                    best_items_count = total
                    best_idx = i

        if best_idx is None:
            # 没有可合并的，停止
            break

        # 执行合并
        a = result[best_idx]
        b = result[best_idx + 1]
        total_items = len(a.get("items", [])) + len(b.get("items", []))
        # 两张都是 flow → 合并后保持 flow（可以形成更长的步骤链）
        # 其他情况 → list（安全默认）
        a_shape = a.get("content_shape", "list")
        b_shape = b.get("content_shape", "list")
        merged_shape = "flow" if a_shape == "flow" and b_shape == "flow" else "list"
        
        merged = {
            "id": a.get("id"),
            "title": f'{a.get("title", "")} · {b.get("title", "")}',
            "items": a.get("items", []) + b.get("items", []),
            # 总 items ≤ 6 保持 low（还能拼车），否则升 medium
            "density": "low" if total_items <= 6 else "medium",
            "content_shape": merged_shape,
            "semantic_weight": a.get("semantic_weight", "secondary"),
            "icon": a.get("icon", "file"),
            "badge": a.get("badge") or b.get("badge"),
            "relation": None,
            "merged_from": [a.get("id"), b.get("id")],
        }
        result[best_idx] = merged
        result.pop(best_idx + 1)

    return result


def _effective_density(card: dict) -> str:
    """
    根据卡片实际内容计算"有效密度"，覆盖 LLM 的标注。

    LLM 倾向于把 4 条短句标成 medium，但视觉上 4 条短句在半宽里放得下，
    应该按 low 处理触发拼车。

    规则（取 LLM 标注和客观判定中更宽松的一个，但阈值收紧了）：
    - items ≤ 3 且 avg_len ≤ 15 且 max_len ≤ 22 → 客观 low
    - items ≥ 6 或某条 > 35 字 → 客观 high
    - 其他 → 客观 medium

    如果客观判定比 LLM 标注更宽松（low vs medium），取客观的；
    如果客观判定更严格（high vs medium），尊重 LLM 的 medium。
    
    例外：primary 权重卡片永不降级（核心内容保持完整性）。
    """
    items = card.get("items", [])
    n_items = len(items)
    lengths = [len(it.get("text", "")) for it in items]
    max_chars = max(lengths, default=0)
    avg_chars = sum(lengths) / max(len(lengths), 1)

    # primary 卡片：尊重 LLM，不降级
    llm_density = card.get("density", "medium")
    if card.get("semantic_weight") == "primary":
        return llm_density

    # 客观判定
    if n_items <= 3 and avg_chars <= 15 and max_chars <= 22:
        objective = "low"
    elif n_items >= 6 or max_chars > 35:
        objective = "high"
    else:
        objective = "medium"

    # 取更宽松的（low > medium > high，数字越小越宽松）
    severity = {"low": 1, "medium": 2, "high": 3}
    if severity.get(objective, 2) < severity.get(llm_density, 2):
        return objective  # 客观更宽松，降级
    return llm_density  # 否则尊重 LLM


# ============================================================
# content_shape 稳定性校验（代码层兜底）
# ============================================================

_FLOW_EVIDENCE_KEYWORDS = [
    "步骤", "流程", "阶段", "首先", "然后", "接着", "之后", "最后",
    "第一步", "第二步", "第三步", "第四步", "第五步",
    "第一", "第二", "第三", "第四", "第五",
]

def _has_flow_evidence(card: dict) -> bool:
    """检查卡片内容是否有流程证据（至少命中 2 条）。"""
    evidence = 0
    items = card.get("items", [])
    title = card.get("title", "")

    # 标题含流程关键词
    if any(kw in title for kw in _FLOW_EVIDENCE_KEYWORDS):
        evidence += 1

    # item bold 含数字编号
    for item in items:
        bold = item.get("bold") or ""
        if any(kw in bold for kw in _FLOW_EVIDENCE_KEYWORDS):
            evidence += 1
            break

    # text 含流程关键词或 → 箭头
    for item in items:
        text = item.get("text") or ""
        if any(kw in text for kw in _FLOW_EVIDENCE_KEYWORDS):
            evidence += 1
            break
        if "→" in text or "->" in text:
            evidence += 1
            break

    # LLM 标注了 | 断点（flow 专有特征）
    for item in items:
        text = item.get("text") or ""
        if "|" in text:
            evidence += 1
            break

    # 3+ items 本身就是 flow 的弱证据（list 很少需要 3+ 步横向排开）
    if len(items) >= 3:
        evidence += 1

    # 至少 2 条证据
    return evidence >= 2


def normalize_content_shapes(cards: list) -> list:
    """
    完全透传 content_shape，不做任何自动修正。
    用户在编辑面板手动选择类型后，100% 尊重用户意愿。
    """
    return cards


def max_slots_for(card: dict, canvas_type: str) -> int:
    """
    计算卡片在一行中最多能跟几张卡片共处。
    返回 1 = 强制独占整行；返回 >1 = 可以拼车。
    """
    shape = card.get("content_shape", "list")
    # 用有效密度覆盖 LLM 标注（防止 LLM 把短句列表标 medium 导致不拼车）
    density = _effective_density(card)
    weight = card.get("semantic_weight", "secondary")

    # 规则1: flow/grid/compare → 独占（视觉结构不容切割）
    if shape in ("flow", "grid", "compare"):
        return 1

    # 规则2: high density → 独占（半行塞不下）
    if density == "high":
        return 1

    # 规则3: primary 权重 → 独占（最重要的内容给足空间）
    if weight == "primary":
        return 1

    # 以下为拼车候选
    if canvas_type == "portrait":
        # 竖版：low/medium density 的 list/compare 能双列
        if shape in ("list", "compare") and density in ("low", "medium"):
            return 2
        return 1

    if canvas_type == "landscape":
        # 横版：宽度充足，low/medium list 都可 3 列（便于溢出时塞回前面行）
        if shape == "list":
            if density in ("low", "medium"):
                return 3
        if shape == "compare":
            if density in ("low", "medium"):
                return 2
        return 1

    return 1


# ============================================================
# 第二层：贪心装箱
# ============================================================

def _find_pair_partner(card: dict, remaining: List[dict]) -> Optional[int]:
    """
    查找 relation 标记的配对卡片在 remaining 列表中的索引。
    返回 remaining 中的索引，找不到返回 None。
    """
    rel = card.get("relation")
    if not rel:
        return None

    target_id = rel.get("with")
    if target_id is None:
        return None

    for i, c in enumerate(remaining):
        if c.get("id") == target_id:
            return i
    return None


def pack(cards: List[dict], canvas_type: str = "portrait") -> List[dict]:
    """
    贪心装箱：把 N 张卡片分配到 M 行。

    输入: cards — 第一站输出的卡片列表
    输出: rows — 每行含 {slots: [...], cols: N}

    内部步骤:
    1. normalize_primary: 强制第 1 张 primary
    2. pre_merge: 卡片过多时主动合并（防溢出）
    3. 贪心装箱
    4. merge_overflow: 溢出兜底

    rows 结构:
    [
        {"slots": [card1], "cols": 1},           # 独占行
        {"slots": [card2, card3], "cols": 2},    # 双列行
        {"slots": [card4], "cols": 1},           # 独占行
        ...
    ]
    """
    canvas = CANVAS[canvas_type]
    max_rows = canvas["max_rows"]
    max_cols = canvas["max_cols"]

    # 步骤 1: 强制第 1 张 primary
    cards = normalize_primary(cards)

    # 步骤 1.5: 校验 content_shape 稳定性（代码层兜底 LLM 波动）
    cards = normalize_content_shapes(cards)

    # 步骤 2: 卡片过多时主动合并
    cards = pre_merge(cards, canvas_type)

    rows: List[dict] = []
    # remaining 是待分配的卡片列表（副本，不修改原数据）
    remaining = list(cards)
    current_row: Optional[dict] = None  # {"slots": [], "cols_used": 0, "max_cols": N}

    while remaining:
        card = remaining.pop(0)
        constraint = max_slots_for(card, canvas_type)

        # Case A: 强制独占 → 封当前行，开新独占行
        if constraint == 1:
            if current_row:
                rows.append(current_row)
                current_row = None
            rows.append({"slots": [card], "cols": 1})
            continue

        # Case B: 拼车候选 → 尝试拼入当前行
        if current_row and current_row["cols_used"] < current_row["max_cols"]:
            # 检查当前行是否兼容（取两者的 min）
            combined_max = min(current_row["max_cols"], constraint)
            if current_row["cols_used"] < combined_max:
                current_row["slots"].append(card)
                current_row["cols_used"] += 1
                current_row["max_cols"] = combined_max
                if current_row["cols_used"] >= current_row["max_cols"]:
                    rows.append(current_row)
                    current_row = None
                continue

        # Case C: 当前行无法拼入 → 封行，开新行
        if current_row:
            rows.append(current_row)

        # 开新行前，检查是否有 relation 配对可以一起放
        current_row = {
            "slots": [card],
            "cols_used": 1,
            "max_cols": constraint,
        }

        # 尝试找配对搭档（优先 relation 标记，兜底任意兼容卡片）
        if constraint >= 2 and remaining:
            partner_idx = _find_pair_partner(card, remaining)
            # 兜底：找剩余中任意可拼车的卡片
            if partner_idx is None:
                for j, other in enumerate(remaining):
                    oc = max_slots_for(other, canvas_type)
                    if oc >= 2:
                        partner_idx = j
                        break
            if partner_idx is not None:
                # 先检查 partner_constraint，再决定是否 pop（防止丢弃）
                partner = remaining[partner_idx]
                partner_constraint = max_slots_for(partner, canvas_type)
                if partner_constraint >= 2:
                    # 满足拼车条件，正式 pop
                    partner = remaining.pop(partner_idx)
                    combined = min(constraint, partner_constraint)
                    current_row["slots"].append(partner)
                    current_row["cols_used"] = 2
                    current_row["max_cols"] = combined
                    if current_row["cols_used"] >= current_row["max_cols"]:
                        rows.append(current_row)
                        current_row = None
                # 不满足条件时，partner 留在 remaining 中，后续正常处理

    # 收尾
    if current_row:
        rows.append(current_row)

    # 溢出处理
    if len(rows) > max_rows:
        rows = merge_overflow(rows, max_rows, canvas_type)

    # 最后一道防线：把超出的拼车候选塞回前面有空位的行
    if len(rows) > max_rows:
        rows = force_fit_overflow(rows, max_rows, canvas_type)

    return rows


# ============================================================
# 第三层：溢出合并
# ============================================================

def _can_merge(card_a: dict, card_b: dict, canvas_type: str, allow_medium: bool = False) -> bool:
    """
    两张卡片是否可以合并。

    allow_medium=False（第一轮）：严格要求 low+low
    allow_medium=True（第二轮）：放宽到 low+medium / medium+medium
    """
    eff_a = _effective_density(card_a)
    eff_b = _effective_density(card_b)

    # 第一轮：都必须是 low
    if not allow_medium:
        if eff_a != "low" or eff_b != "low":
            return False
    else:
        # 第二轮：允许 low/medium 组合，但不允许 high
        if eff_a == "high" or eff_b == "high":
            return False

    # 必须 list 型（flow/grid/compare 不合并）
    if card_a.get("content_shape") != "list" or card_b.get("content_shape") != "list":
        return False

    # primary 权重不合并（最重要的内容不能丢独立性）
    if card_a.get("semantic_weight") == "primary" or card_b.get("semantic_weight") == "primary":
        return False

    # 合并后 items 不超过 8 条
    total_items = len(card_a.get("items", [])) + len(card_b.get("items", []))
    if total_items > 8:
        return False
    return True


def _merge_score(card_a: dict, card_b: dict, idx_a: int, idx_b: int) -> float:
    """合并优先级评分。分数越高越优先合并。"""
    # 原文位置距离（用 id 差近似）
    id_a = card_a.get("id", idx_a)
    id_b = card_b.get("id", idx_b)
    pos_score = 1.0 / (abs(id_a - id_b) + 1)

    # relation 加成
    relation_bonus = 0.0
    rel_a = card_a.get("relation")
    rel_b = card_b.get("relation")
    if rel_a and rel_a.get("with") == id_b:
        relation_bonus = 0.5
    if rel_b and rel_b.get("with") == id_a:
        relation_bonus = 0.5

    return pos_score + relation_bonus


def _do_merge(card_a: dict, card_b: dict) -> dict:
    """执行合并，返回新卡片"""
    return {
        "id": card_a.get("id"),
        "title": f'{card_a.get("title", "")} · {card_b.get("title", "")}',
        "items": card_a.get("items", []) + card_b.get("items", []),
        "density": "medium",  # 合并后提升 density
        "content_shape": "list",
        "semantic_weight": card_a.get("semantic_weight", "secondary"),
        "icon": card_a.get("icon", "file"),
        "badge": card_a.get("badge") or card_b.get("badge"),
        "relation": None,
        "merged_from": [card_a.get("id"), card_b.get("id")],
    }


def _try_merge_round(rows: List[dict], max_rows: int, canvas_type: str, allow_medium: bool) -> List[dict]:
    """执行一轮合并。返回合并后的 rows。"""
    if len(rows) <= max_rows:
        return rows

    # 找所有可合并的相邻行对
    candidates: List[Tuple[int, float]] = []
    for i in range(len(rows) - 1):
        row_a = rows[i]
        row_b = rows[i + 1]
        # 只合并两个独占行（各只有 1 张卡）
        if len(row_a["slots"]) == 1 and len(row_b["slots"]) == 1:
            card_a = row_a["slots"][0]
            card_b = row_b["slots"][0]
            if _can_merge(card_a, card_b, canvas_type, allow_medium=allow_medium):
                score = _merge_score(card_a, card_b, i, i + 1)
                candidates.append((i, score))

    # 按分数降序合并
    candidates.sort(key=lambda x: x[1], reverse=True)

    merged_indices: set = set()
    for idx, _ in candidates:
        if len(rows) <= max_rows:
            break
        if idx in merged_indices or (idx + 1) in merged_indices:
            continue

        row_a = rows[idx]
        row_b = rows[idx + 1]
        card_a = row_a["slots"][0]
        card_b = row_b["slots"][0]

        merged_card = _do_merge(card_a, card_b)
        rows[idx] = {"slots": [merged_card], "cols": 1}
        rows[idx + 1] = None  # 标记删除
        merged_indices.add(idx)
        merged_indices.add(idx + 1)

    # 清理被标记为 None 的行
    rows = [r for r in rows if r is not None]
    return rows


def merge_overflow(rows: List[dict], max_rows: int, canvas_type: str) -> List[dict]:
    """
    行数超限时，分两轮合并相邻卡片：
    - 第一轮（严格）：low+low 合并
    - 第二轮（放宽）：low+medium / medium+medium 合并（仍限制总 items ≤ 8）

    绝不删内容，只合并。两轮后仍超 → JS 自缩放兜底。
    """
    if len(rows) <= max_rows:
        return rows

    # 第一轮：严格 low+low
    rows = _try_merge_round(rows, max_rows, canvas_type, allow_medium=False)
    if len(rows) <= max_rows:
        return rows

    # 第二轮：放宽到 medium+medium
    rows = _try_merge_round(rows, max_rows, canvas_type, allow_medium=True)
    return rows


def force_fit_overflow(rows: List[dict], max_rows: int, canvas_type: str) -> List[dict]:
    """
    最后一道防线：把超出的拼车候选塞回前面有空位的行。

    场景：横版 6 张卡片，#2#3 拼车成 2 列（max_cols=3，还有 1 空位），
    但 #6 被 #5 flow 隔断，开新行导致 5 行 > 4 行限制。

    逻辑：
    1. 从最后一行开始，取拼车候选卡片
    2. 向前查找有空位的行（cols < max_cols 且塞入后不违反卡片的 max_slots）
    3. 塞入，删空行
    4. 重复直到行数 ≤ max_rows 或无法塞入
    """
    while len(rows) > max_rows:
        last_row = rows[-1]
        last_slots = last_row.get("slots", [])

        # 只处理拼车候选（非独占卡片）
        movable_cards = []
        for slot in last_slots:
            constraint = max_slots_for(slot, canvas_type)
            if constraint > 1:  # 拼车候选
                movable_cards.append(slot)

        if not movable_cards:
            break  # 最后一行都是独占卡片，无法移动

        # 尝试把每张可移动卡片塞到前面的行
        placed = False
        for card in movable_cards:
            card_constraint = max_slots_for(card, canvas_type)

            for i in range(len(rows) - 1):
                row = rows[i]
                row_slots = row.get("slots", [])
                row_cols = len(row_slots)
                max_cols = CANVAS[canvas_type]["max_cols"]

                if row_cols >= max_cols:
                    continue  # 行已满

                # 检查塞入后是否违反行内所有卡片的 max_slots
                new_cols = row_cols + 1
                if new_cols > card_constraint:
                    continue  # 超过这张卡片的 max_slots
                if any(new_cols > max_slots_for(s, canvas_type) for s in row_slots):
                    continue  # 超过行内某张卡片的 max_slots

                # 塞入
                row_slots.append(card)
                last_slots.remove(card)
                placed = True
                break

            if placed:
                break

        if not placed:
            break  # 无法塞入任何卡片

        # 如果最后一行空了，删除
        if not last_slots:
            rows.pop()

    return rows


# ============================================================
# 辅助：行信息摘要（调试用）
# ============================================================

def rows_summary(rows: List[dict]) -> str:
    """生成行分配摘要，用于调试和日志。"""
    lines = []
    for i, row in enumerate(rows):
        slots = row["slots"]
        cols = len(slots)
        titles = " | ".join(s.get("title", "?")[:10] for s in slots)
        shapes = ", ".join(f'{s.get("content_shape","?")}/{s.get("density","?")}' for s in slots)
        lines.append(f"  Row {i+1} [{cols}col]: {titles}  ({shapes})")
    return "\n".join(lines)


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    # 模拟 5-27 文章的卡片数据
    test_cards = [
        {
            "id": 1,
            "title": "核心亮点 · Vibe Coding",
            "items": [{"bold": "需求对齐", "text": "四方对齐"}, {"bold": "文档落地", "text": "标准化文档"}],
            "density": "high",
            "content_shape": "list",
            "semantic_weight": "primary",
            "icon": "rocket",
            "badge": "3天从0到1上线",
            "relation": None,
        },
        {
            "id": 2,
            "title": "产品定位",
            "items": [{"text": "通用聚合引擎"}, {"text": "211个信源"}],
            "density": "low",
            "content_shape": "list",
            "semantic_weight": "secondary",
            "icon": "gear",
            "badge": None,
            "relation": {"type": "pair", "with": 3},
        },
        {
            "id": 3,
            "title": "核心价值",
            "items": [{"text": "境外源直连"}, {"text": "5维评分"}, {"text": "每日8点日报"}],
            "density": "low",
            "content_shape": "list",
            "semantic_weight": "secondary",
            "icon": "star",
            "badge": None,
            "relation": {"type": "pair", "with": 2},
        },
        {
            "id": 4,
            "title": "技术架构优势",
            "items": [{"bold": "双LLM降本", "text": "V3.2+V4 Pro"}, {"bold": "双层去重", "text": "URL+语义"}, {"bold": "分级管控", "text": "S/A/B三级"}],
            "density": "high",
            "content_shape": "grid",
            "semantic_weight": "secondary",
            "icon": "architecture",
            "badge": None,
            "relation": None,
        },
        {
            "id": 5,
            "title": "全自动化生产流程",
            "items": [{"text": "采集"}, {"text": "去重"}, {"text": "评分"}, {"text": "撰写"}, {"text": "分发"}],
            "density": "high",
            "content_shape": "flow",
            "semantic_weight": "secondary",
            "icon": "workflow",
            "badge": None,
            "relation": None,
        },
        {
            "id": 6,
            "title": "多场景适配",
            "items": [{"bold": "个人浏览", "text": "网页筛选导出"}, {"bold": "开发调用", "text": "无鉴权API"}, {"bold": "AI协作", "text": "Claude+Cursor"}],
            "density": "high",
            "content_shape": "grid",
            "semantic_weight": "supporting",
            "icon": "layers",
            "badge": None,
            "relation": None,
        },
    ]

    print("=" * 60)
    print("竖版 (portrait) 装箱结果:")
    print("=" * 60)
    rows = pack(test_cards, "portrait")
    print(rows_summary(rows))
    print(f"\n总行数: {len(rows)} / {CANVAS['portrait']['max_rows']}")

    print("\n" + "=" * 60)
    print("横版 (landscape) 装箱结果:")
    print("=" * 60)
    rows = pack(test_cards, "landscape")
    print(rows_summary(rows))
    print(f"\n总行数: {len(rows)} / {CANVAS['landscape']['max_rows']}")
