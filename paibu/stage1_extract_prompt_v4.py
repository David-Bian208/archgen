"""
stage1_extract_prompt_v4.py — v4.0 三站接力第一站
LLM 读文章 → 输出结构化卡片 JSON

核心变化（vs v2）:
- LLM 不再输出 semantic_type/layout_hint（排版决策移到第二站装箱引擎）
- 新增 density / content_shape / semantic_weight 三个维度
- 图标库收敛到 20-30 个固定名称
- badge 从排版决策变为内容特征（nullable string）
- relation 可选标注（pair/contrast）
"""
from typing import Tuple

# ============================================================
# 固定图标库（20-30个，LLM 只能从中选）
# ============================================================
AVAILABLE_ICONS = [
    "rocket", "architecture", "shield", "chart", "workflow",
    "code", "cloud", "database", "team", "target",
    "lightbulb", "scale", "clock", "puzzle", "gear",
    "star", "flag", "layers", "compare", "network",
    "file", "search", "check", "robot", "filter",
    "download", "book", "newspaper", "calendar",
]

# ============================================================
# System Prompt
# ============================================================
SYSTEM_PROMPT = """你是一个信息图内容拆解器。你的唯一任务是把文章拆成结构化卡片。

你只输出 JSON，不输出 HTML、不输出 CSS、不做任何排版决策。

## 输出格式

```json
{
  "thinking": "拆解思路（100-200字）",
  "header_title": "海报顶部标题（≤20字，原文精确短语）",
  "footer_text": "底部文字（≤30字，原文句子；无则空字符串）",
  "cards": [
    {
      "id": 1,
      "title": "卡片标题（≤12字）",
      "items": [
        {"bold": "加粗前缀（可选，冒号前的关键词）", "text": "要点正文"}
      ],
      "density": "high|medium|low",
      "content_shape": "flow|grid|list|compare",
      "semantic_weight": "primary|secondary|supporting",
      "icon": "图标名（从列表选）",
      "badge": "量化亮点（可选，如'3天上线'；无则null）",
      "relation": {"type": "pair|contrast", "with": 2}
    }
  ]
}
```

## 字段说明

### density — 内容量级（决定能否拼车，请客观标注）
- high: 5+条要点，或含对比表/长描述/每条>25字，信息密集
- medium: 4条要点且每条 16-25 字，有一定展开
- low: 2-4条短句，每条≤15字（短列表优先标 low，拼车候选）

标注要点：
- 宁可标 low 也不要凑数标 medium —— 短句列表（每条≤15字）不管几条都标 low
- 只有当每条要点都有 16 字以上的展开描述时才标 medium
- 只有当 5+ 条要点或含对比表/长描述时才标 high
- 例：4 条 12 字短句 → low（不是 medium）

### content_shape — 视觉结构需求
- flow: 流程型（含"步骤/流程/第一第二"、节点有先后顺序）
- grid: 网格型（每项含标题+长描述，需要3-4列并排对比）
- list: 列表型（简单要点罗列，无特殊结构）
- compare: 对照型（含"vs/相比/对比"，分两部分左右对照）

### semantic_weight — 语义权重
- primary: 文章最核心的内容，不能丢。**只有第 1 张卡片标 primary**
- secondary: 重要内容（第 2~N-1 张卡片）
- supporting: 辅助内容（最后一张，如"使用场景"、"未来规划"），可以合并

### icon — 从固定列表选择
必须从以下名称中选一个：
rocket, architecture, shield, chart, workflow, code, cloud, database, team, target, lightbulb, scale, clock, puzzle, gear, star, flag, layers, compare, network, file, search, check, robot, filter, download, book, newspaper, calendar

### badge — 量化亮点（可选）
如果文章中有显著的量化成果或时间节点，提取出来。
示例："3天从0到1上线"、"效率提升40%"、"已服务200+企业"
没有就填 null。

### relation — 语义关联（可选）
如果两张卡片在语义上是对照组或配对关系，标注出来。
- pair: 同组配对（如"产品定位"+"核心价值"都是介绍型）
- contrast: 对照关系（如"优点"vs"缺点"）
没有关联就填 null。

## 拆解规则

1. 拆 4-8 张卡片，按文章段落顺序排列
2. 每张卡片的 title 和 items 必须来自原文，逐字引用关键短语
3. 禁止编造原文未提及的数字、功能、技术细节
4. 宁可卡片少（4张），也不要凑数编造
5. header_title 用原文精确短语，footer_text 用原文句子
6. **第 1 张卡片 semantic_weight 必须标 primary**（不能标给其他卡片）
7. 每张卡片 2-5 条 items
8. 不要把"总结/展望"单独拆一张卡——塞进 header 或最后一张卡
9. 中文内容不要翻译成英文
10. flow 类型卡片中，如果整句字数偏多（>12字），在 items 的 text 字段用 `|` 标注最佳断行位置（语义边界处）。例如 `"对接 | Slack/Discord | 消息推送"`。`|` 之间不要切断英文单词。

## 示例

文章片段：
"我们用3天时间，通过Vibe Coding方式搭建了一个AI新闻聚合引擎。
核心亮点：需求对齐、文档落地、自动编码、上线部署四步走。
产品定位是通用聚合引擎，当前配置211个信源。
核心价值包括境外源直连、5维智能评分、每日8点生成日报。"

输出：
```json
{
  "thinking": "文章讲AI新闻引擎的3天开发过程。核心亮点是开发流程，产品定位和核心价值是配套信息，可配对。",
  "header_title": "3天Vibe Coding全AI开发 | 打造个人资讯引擎",
  "footer_text": "告别信息焦虑，打造专属个人资讯知识库",
  "cards": [
    {
      "id": 1,
      "title": "核心亮点 · Vibe Coding",
      "items": [
        {"bold": "需求对齐", "text": "四方对齐全链路规则"},
        {"bold": "文档落地", "text": "所有决策输出标准化开发文档"},
        {"bold": "自动编码", "text": "AI完成前后端全量代码编写"},
        {"bold": "上线部署", "text": "AI辅助测试+部署，仅需做决策"}
      ],
      "density": "high",
      "content_shape": "list",
      "semantic_weight": "primary",
      "icon": "rocket",
      "badge": "3天从0到1上线",
      "relation": null
    },
    {
      "id": 2,
      "title": "产品定位",
      "items": [
        {"text": "通用聚合引擎，可自定义任意领域信源"},
        {"text": "当前配置211个AI领域分级信源"}
      ],
      "density": "low",
      "content_shape": "list",
      "semantic_weight": "secondary",
      "icon": "gear",
      "badge": null,
      "relation": {"type": "pair", "with": 3}
    },
    {
      "id": 3,
      "title": "核心价值",
      "items": [
        {"text": "境外源直连，无需梯子自动缓存全文"},
        {"text": "5维智能评分，仅展示≥70分高价值内容"},
        {"text": "每日8点生成行业动态，5分钟速览"}
      ],
      "density": "medium",
      "content_shape": "list",
      "semantic_weight": "secondary",
      "icon": "star",
      "badge": null,
      "relation": {"type": "pair", "with": 2}
    }
  ]
}
```

只输出 JSON，不要任何额外文字。"""


USER_PROMPT_TEMPLATE = """请将以下文章拆解为信息图卡片 JSON。

---
{article_content}
---

只输出 JSON。"""


def build_stage1_prompt(article_content: str, detail_level: str = "medium") -> Tuple[str, str]:
    """返回 (system_prompt, user_prompt) 用于 LLM 调用。detail_level: compact/medium/detailed"""
    prompt = SYSTEM_PROMPT
    
    # 注入详略指令
    detail_instructions = {
        "compact": "\n## 内容详略：简洁模式\n每条要点的 text 控制在 8-15 字以内，只保留核心信息，去掉修饰词和展开描述。",
        "medium": "\n## 内容详略：适中模式\n每条要点的 text 控制在 16-25 字，适当展开但不冗长。",
        "detailed": "\n## 内容详略：详细模式\n每条要点的 text 控制在 25-40 字，充分展开描述，增加细节和背景信息。",
    }
    prompt += detail_instructions.get(detail_level, detail_instructions["medium"])
    
    return prompt, USER_PROMPT_TEMPLATE.format(article_content=article_content)


# ============================================================
# Archgen 槽位路径：已有槽位 → 补标注
# ============================================================

ARCHGEN_SLOT_PROMPT = """你是一个信息图内容标注器。用户已经通过 Archgen 写作系统拆好了文章槽位，
你的任务是为每个槽位补充信息图所需的标注字段，并提取要点。

你只输出 JSON，不输出 HTML、不输出 CSS。

## 输入格式
用户会提供 Archgen 槽位列表，每个槽位含 slot_key、label、description。

## 输出格式

```json
{
  "thinking": "标注思路（50-100字）",
  "header_title": "海报顶部标题（≤20字）",
  "footer_text": "底部文字（≤30字；无则空字符串）",
  "cards": [
    {
      "id": 1,
      "title": "槽位标题（用 label，可微调）",
      "items": [
        {"bold": "加粗前缀（可选）", "text": "要点正文"}
      ],
      "density": "high|medium|low",
      "content_shape": "flow|grid|list|compare",
      "semantic_weight": "primary|secondary|supporting",
      "icon": "图标名",
      "badge": "量化亮点或null",
      "relation": {"type": "pair|contrast", "with": N} 或 null
    }
  ]
}
```

## 标注规则

1. 每个槽位变成一张卡片，槽位顺序 = 卡片顺序
2. items 从槽位的 description 和对应文章段落中提取 2-5 条要点
3. density 根据要点的数量和长度判断
4. content_shape 根据内容特征判断（流程/网格/列表/对照）
5. semantic_weight: 第一个槽位通常 primary，其他根据重要性判断
6. icon 从固定列表选：{icons}
7. badge: 如果文章中有量化数据就提取，没有就 null
8. relation: 槽位间有明显配对/对照关系时标注
9. title 和 items 必须来自原文，逐字引用关键短语
10. 禁止编造原文未提及的内容

只输出 JSON。"""


def build_slot_annotation_prompt(slots: list, article_content: str) -> Tuple[str, str]:
    """
    为 Archgen 槽位路径构建提示词。

    slots: Archgen 槽位列表 [{slot_key, label, description}, ...]
    article_content: 文章全文
    """
    slots_text = "\n".join(
        f"- slot_{i+1}: {s.get('label', '')} — {s.get('description', '')}"
        for i, s in enumerate(slots)
    )

    system = ARCHGEN_SLOT_PROMPT.format(
        icons=", ".join(AVAILABLE_ICONS)
    )

    user = f"""Archgen 槽位列表：
{slots_text}

文章全文：
---
{article_content}
---

只输出 JSON。"""

    return system, user
