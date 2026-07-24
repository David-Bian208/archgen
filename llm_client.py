"""
排布 (PaiBu) LLM 客户端 — 海报拆卡片
从 config.yaml 或环境变量读取配置，调用 DeepSeek API（OpenAI 兼容）。
"""
import json
import os
import re
import httpx
from pathlib import Path


# ---- 配置加载 ----
def _load_config():
    """从 config.yaml 或环境变量加载配置"""
    cfg = {}
    # 优先从环境变量
    cfg["api_key"] = os.getenv("DEEPSEEK_API_KEY", "")
    cfg["base_url"] = os.getenv("PAIBU_LLM_BASE_URL", "https://api.deepseek.com/v1")
    cfg["model"] = os.getenv("PAIBU_LLM_MODEL", "deepseek-v4-flash")
    cfg["timeout"] = int(os.getenv("PAIBU_LLM_TIMEOUT", "120"))
    # 其次从 config.yaml
    yaml_path = Path(__file__).parent / "config.yaml"
    if yaml_path.exists():
        try:
            import yaml
            with open(yaml_path) as f:
                yc = yaml.safe_load(f)
            llm = yc.get("llm", {})
            if not cfg["api_key"]:
                cfg["api_key"] = llm.get("api_key", "")
            if not os.getenv("PAIBU_LLM_BASE_URL"):
                cfg["base_url"] = llm.get("base_url", cfg["base_url"])
            if not os.getenv("PAIBU_LLM_MODEL"):
                cfg["model"] = llm.get("model", cfg["model"])
            cfg["timeout"] = llm.get("timeout", cfg["timeout"])
        except Exception:
            pass
    return cfg


_config = _load_config()
_API_KEY = _config["api_key"]
_BASE_URL = f"{_config['base_url'].rstrip('/')}/chat/completions"
_MODEL = _config["model"]
_TIMEOUT = _config["timeout"]


def chat_json(system_prompt: str, user_prompt: str, temperature: float = 0.1, retry: int = 3) -> dict:
    """调用 LLM 并返回 JSON。自动重试截断/空响应。"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_API_KEY}",
    }
    payload = {
        "model": _MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": 4096,
    }

    last_error = None
    for attempt in range(retry):
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.post(_BASE_URL, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = (data["choices"][0]["message"]["content"] or "").strip()

            if not content:
                last_error = "LLM 返回空内容"
                if attempt < retry - 1:
                    continue
                raise RuntimeError(last_error)

            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                content = content[start:end + 1]

            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                last_error = e
                fixed = content[:e.pos]
                for i in range(len(fixed) - 1, -1, -1):
                    if fixed[i] in "]}":
                        fixed = fixed[:i + 1]
                        break
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass
        except (json.JSONDecodeError, RuntimeError) as e:
            last_error = e
            if attempt >= retry - 1:
                raise RuntimeError(f"LLM JSON 解析失败（重试{retry}次）: {last_error}")
        except Exception as e:
            last_error = e

    raise RuntimeError(f"LLM JSON 解析失败（重试{retry}次）: {last_error}")


def extract_cards_from_article(article_text: str, detail_level: str = "medium") -> dict:
    """用真实 LLM 拆卡片（第一站）。"""
    from stage1_extract_prompt_v4 import build_stage1_prompt
    system, user = build_stage1_prompt(article_text, detail_level)
    result = chat_json(system, user)
    return result


def enrich_card_items(card: dict) -> dict:
    """用 LLM 丰富单张卡片的内容（详细模式）。"""
    import copy
    enriched = copy.deepcopy(card)
    items = card.get("items", [])
    if not items:
        return enriched

    targets = []
    for it in items:
        n = len(it.get("text", ""))
        if n <= 10:
            targets.append("20-30字")
        elif n <= 20:
            targets.append("25-40字")
        else:
            targets.append("保持原长度或微调")

    items_text = "\n".join(
        f'- {it.get("bold","") + "：" if it.get("bold") else ""}{it.get("text","")} （目标：{t}）'
        for it, t in zip(items, targets)
    )

    system = """你是一个内容扩展器。用户会给你一个卡片的要点列表，每条后面有目标字数要求。

输出纯 JSON：
```json
{"items": [{"bold": "原标题（不变）", "text": "扩展后的正文"}]}
```

规则：
- bold 字段原样保留，不要改
- text 字段只写正文，不要把 bold 的内容再写一遍
- text 严格按照目标字数扩展，增加具体细节、举例或量化描述
- 不要编造原文没有的事实，只做合理展开"""

    user = f"请按目标字数扩展以下内容：\n\n{items_text}"
    try:
        result = chat_json(system, user, temperature=0.3)
        new_items = result.get("items", [])
        if new_items and len(new_items) == len(items):
            for i, it in enumerate(new_items):
                items[i]["text"] = it.get("text", items[i].get("text", ""))
        enriched["items"] = items
    except Exception:
        pass
    return enriched


def compact_card_items(card: dict) -> dict:
    """用 LLM 压缩单张卡片的内容（简洁模式）。"""
    import copy
    compacted = copy.deepcopy(card)
    items = card.get("items", [])
    if not items:
        return compacted

    items_text = "\n".join(
        f'- {it.get("bold","") + "：" if it.get("bold") else ""}{it.get("text","")}'
        for it in items
    )

    system = """你是一个内容精炼器。用户会给你一个卡片的要点列表，你的任务是把每条要点压缩到最精简的表达。

输出纯 JSON：
```json
{"items": [{"bold": "原标题（不变）", "text": "压缩后的正文"}]}
```

规则：
- bold 字段原样保留，不要改
- text 字段只写正文，不要把 bold 的内容再写一遍
- text 压缩到 8-15 字，只保留最核心的信息
- 去掉修饰词、举例、冗余描述
- 不能改变原意"""

    user = f"请压缩以下内容，每条 8-15 字：\n\n{items_text}"
    try:
        result = chat_json(system, user, temperature=0.1)
        new_items = result.get("items", [])
        if new_items and len(new_items) == len(items):
            for i, it in enumerate(new_items):
                items[i]["text"] = it.get("text", items[i].get("text", ""))
        compacted["items"] = items
    except Exception:
        pass
    return compacted
