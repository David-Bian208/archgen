"""API 接口定义 - ArchGen v2.0"""

import uuid
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Body
from fastapi.responses import FileResponse, JSONResponse

from src.knowledge_base import KnowledgeBaseReader
from src.classifier import ContentClassifier
from src.framework_matcher import FrameworkMatcher
from src.data_checker import DataCompletenessChecker
from src.extractor_agent import StructureExtractor
from src.html_generator import HTMLGenerator
from src.screenshot import ScreenshotService
from src.local_folder_reader import LocalFolderReader
from src.source_tag_processor import SourceTagProcessor, get_source_tag_processor
from src.supplement_storage import SupplementStorage, get_supplement_storage, record_session_metadata, cleanup_expired_supplements

logger = logging.getLogger(__name__)

router = APIRouter()

async_tasks: Dict[str, Dict] = {}

_app = None


def set_app(app):
    """设置 app 引用"""
    global _app
    _app = app


def _get_config(section: str) -> Dict:
    """获取配置段"""
    if _app and hasattr(_app.state, "config"):
        return _app.state.config.get(section, {})
    return {}


def _success(data=None, msg="success"):
    """成功响应"""
    return {"code": 0, "msg": msg, "data": data}


def _error(code=1, msg="error", data=None):
    """错误响应"""
    return {"code": code, "msg": msg, "data": data}


# ===== 知识库接口（保留，兼容旧版） =====

@router.get("/api/kb/categories")
async def get_kb_categories():
    """获取知识库分类列表"""
    try:
        kb = KnowledgeBaseReader(_get_config("knowledge_base"))
        categories = kb.list_categories()
        return _success(categories)
    except Exception as e:
        logger.error(f"获取知识库分类失败: {e}")
        return _error(msg=str(e))


@router.post("/api/workflow/supplement/ai-auto")
async def ai_auto_supplement(request: Dict = Body(...)):
    """AI 自动补充：整合 AI-Pulse API + 知识库 + 上下文

    请求体：
    {
        "session_id": "会话 ID",
        "missing_item": "缺失项描述",
        "mcp_summary": "MCP 摘要",
        "selected_cases": [],  // 用户从 AI-Pulse 检索中勾选的案例
        "kb_context": ""  // 知识库补充内容
    }

    返回：
    {
        "code": 0,
        "data": {
            "content": "AI 推断的补充内容",
            "inference_note": "推断依据说明",
            "source": "ai-pulse+kb|ai-pulse|kb|ai_inference"  // 内容来源
        }
    }
    """
    session_id = request.get("session_id", "")
    missing_item = request.get("missing_item", "")
    mcp_summary = request.get("mcp_summary", "")
    selected_cases = request.get("selected_cases", [])
    kb_context = request.get("kb_context", "")

    llm_config = _get_config("llm")
    base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = llm_config.get("api_key", "")
    model = llm_config.get("model", "deepseek-chat")
    timeout = llm_config.get("timeout", 60)

    persona_summary = ""
    try:
        persona_parsed = _get_persona_parsed()
        if persona_parsed:
            persona_summary = persona_parsed.get("summary", "")
    except:
        pass

    # Step 1: 自动调用 AI-Pulse API 检索外部案例
    ai_pulse_cases = []
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            # 从缺失项提取搜索关键词
            keywords = " ".join(missing_item.replace("，", " ").replace("、", " ").split()[:5])
            ai_pulse_url = "http://localhost:8887/api/v1/list"
            ai_pulse_resp = await client.get(
                ai_pulse_url,
                params={"q": keywords, "mode": "selected", "size": 3}
            )
            if ai_pulse_resp.status_code == 200:
                ai_pulse_data = ai_pulse_resp.json()
                items = ai_pulse_data.get("items", [])
                for item in items:
                    ai_pulse_cases.append({
                        "title": item.get("title", ""),
                        "source": item.get("source", "AI-Pulse"),
                        "summary": item.get("summary", ""),
                        "url": item.get("url", ""),
                        "score": item.get("final_score", 0),
                    })
            else:
                logger.warning(f"AI-Pulse 检索返回非200: {ai_pulse_resp.status_code}")
    except Exception as e:
        logger.warning(f"AI-Pulse 检索失败: {e}")
        ai_pulse_cases = []

    # 合并用户勾选案例和 AI-Pulse 自动检索的案例
    all_cases = selected_cases + ai_pulse_cases

    # 判断内容来源
    has_ai_pulse = len(all_cases) > 0
    has_kb = kb_context and len(kb_context.strip()) > 0

    if has_ai_pulse and has_kb:
        content_source = "ai-pulse+kb"
    elif has_ai_pulse:
        content_source = "ai-pulse"
    elif has_kb:
        content_source = "kb"
    else:
        content_source = "ai_inference"

    # 格式化 AI-Pulse 案例
    cases_context = ""
    if all_cases:
        cases_list = "\n".join([
            f"• 【{c.get('title', '')}】\n  来源：{c.get('source', 'AI-Pulse')}\n  摘要：{c.get('summary', '')}"
            for c in all_cases
        ])
        cases_context = f"\n【AI-Pulse 检索到的相关案例】（请优先引用这些案例）\n{cases_list}"

    # 格式化知识库上下文
    kb_context_str = ""
    if kb_context:
        kb_context_str = f"\n【知识库补充内容】（AI生成时请优先引用以下内容）\n{kb_context}"

    # 推断依据说明模板
    source_note_map = {
        "ai-pulse+kb": "基于 AI-Pulse 检索案例 + 知识库内容 + 上下文推理",
        "ai-pulse": "基于 AI-Pulse 检索案例 + 上下文推理",
        "kb": "基于知识库内容 + 上下文推理",
        "ai_inference": "AI-Pulse 和知识库均无匹配内容，采用纯 AI 上下文推理补充",
    }

    prompt = f"""你是一个内容策划专家。请根据以下信息，为指定的缺失项生成补充内容。

【工作流说明】
1. 系统已通过 AI-Pulse API 自动检索到外部案例（见下方"AI-Pulse 检索案例"）
2. 系统已加载绑定的知识库内容（见下方"知识库补充内容"）
3. 你需要基于 MCP 摘要 + AI-Pulse 案例 + 知识库内容，做上下文推断补充

【缺失项】
{missing_item}

【MCP 素材摘要】
{mcp_summary}
{cases_context}{kb_context_str}

【作者身份定位】（只影响语言风格，不影响内容事实）
{persona_summary}

请为这个缺失项生成补充内容，要求：
1. 优先引用 AI-Pulse 检索到的案例中的信息（如有）
2. 其次引用知识库内容（如有）
3. 结合 MCP 摘要中的已有信息做推断
4. 如果 AI-Pulse 和知识库都没有足够信息，基于常识做合理推断，并在 inference_note 中标注【纯 AI 推理】
5. 语言风格要符合作者身份定位（简洁、实战导向）
6. 内容要具体、可操作

返回 JSON 格式（不要 markdown 代码块）：
{{
  "content": "生成的补充内容",
  "inference_note": "说明推断依据，例如：'{source_note_map[content_source]}'"
}}

注意：
- 必须体现 AI-Pulse 案例中的关键信息（公司名、数据、效果等）
- 宁可内容少而精，不要编造

请直接返回 JSON：
"""

    try:
        import httpx
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2048,
                    "temperature": 0.3,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()

        parsed_content = result["choices"][0]["message"]["content"].strip()
        parsed_content = parsed_content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        supplement = json_mod.loads(parsed_content)
        
        # 添加来源信息
        supplement["source"] = content_source

        return _success(supplement)
    except Exception as e:
        logger.error(f"AI 自动补充失败: {e}")
        return _error(msg=str(e))


@router.post("/api/workflow/supplement/add")
async def add_supplement(request: Dict = Body(...)):
    """
    添加补充内容（用户手动补充或 AI-Pulse 返回后调用）

    请求体：
    {
        "session_id": "会话 ID",
        "type": "case/persona/data/framework",
        "dimension": "案例/数据/画像/框架",
        "content": "补充内容正文",
        "source": "ai-pulse/manual/file",
        "source_detail": {},  // 可选，来源详情
        "domain_tags": [],    // 可选，领域标签
    }
    """
    session_id = request.get("session_id", "")
    if not session_id:
        return _error(code=400, msg="缺少 session_id 参数")

    try:
        storage = get_supplement_storage(session_id)
        supplement_id = storage.add_supplement(
            supplement_type=request.get("type", "case"),
            dimension=request.get("dimension", ""),
            content=request.get("content", ""),
            source=request.get("source", "manual"),
            source_detail=request.get("source_detail", {}),
            domain_tags=request.get("domain_tags", []),
        )
        return _success({"supplement_id": supplement_id})
    except Exception as e:
        logger.error(f"添加补充内容失败: {e}")
        return _error(msg=str(e))


@router.post("/api/workflow/supplement/confirm")
async def confirm_supplement(request: Dict = Body(...)):
    """
    确认补充内容（标记为 confirmed，LLM 将能感知到）

    请求体：
    {
        "session_id": "会话 ID",
        "supplement_id": "supp_xxx",
    }
    """
    session_id = request.get("session_id", "")
    supplement_id = request.get("supplement_id", "")
    if not session_id or not supplement_id:
        return _error(code=400, msg="缺少 session_id 或 supplement_id 参数")

    try:
        storage = get_supplement_storage(session_id)
        success = storage.confirm_supplement(supplement_id)
        if success:
            return _success({"message": "已确认"})
        return _error(code=404, msg="补充内容不存在")
    except Exception as e:
        logger.error(f"确认补充内容失败: {e}")
        return _error(msg=str(e))


@router.post("/api/workflow/supplement/list")
async def list_supplements(request: Dict = Body(...)):
    """
    获取当前 Session 所有补充内容

    请求体：
    {
        "session_id": "会话 ID",
        "confirmed_only": false,  // 可选，默认返回全部
    }
    """
    session_id = request.get("session_id", "")
    if not session_id:
        return _error(code=400, msg="缺少 session_id 参数")

    try:
        storage = get_supplement_storage(session_id)
        confirmed_only = request.get("confirmed_only", False)
        supplements = storage.get_all(confirmed_only=confirmed_only)
        stats = storage.get_stats()
        return _success({"supplements": supplements, "stats": stats})
    except Exception as e:
        logger.error(f"获取补充内容列表失败: {e}")
        return _error(msg=str(e))


@router.post("/api/workflow/supplement/export")
async def export_supplements_to_domain(request: Dict = Body(...)):
    """
    导出 Session 补充内容到领域知识库（P1 预留接口）

    请求体：
    {
        "session_id": "会话 ID",
        "domain_tag": "ai-efficiency",
        "supplement_ids": [],  // 可选，导出指定的（None = 导出全部已确认的）
    }
    """
    session_id = request.get("session_id", "")
    domain_tag = request.get("domain_tag", "")
    if not session_id or not domain_tag:
        return _error(code=400, msg="缺少 session_id 或 domain_tag 参数")

    try:
        storage = get_supplement_storage(session_id)
        supplement_ids = request.get("supplement_ids", None)
        result = storage.export_to_domain(domain_tag, supplement_ids)
        return _success(result)
    except Exception as e:
        logger.error(f"导出到领域库失败: {e}")
        return _error(msg=str(e))


@router.post("/api/workflow/session/metadata")
async def record_metadata(request: Dict = Body(...)):
    """
    记录项目元数据（埋点）

    请求体：
    {
        "session_id": "会话 ID",
        "domain_tag": "ai-efficiency",
        "generation_mode": "standard",
        "user_satisfaction": 5,  // 可选，1-5 星
        "exported_to_domain": false,
    }
    """
    session_id = request.get("session_id", "")
    if not session_id:
        return _error(code=400, msg="缺少 session_id 参数")

    try:
        metadata = record_session_metadata(
            session_id=session_id,
            domain_tag=request.get("domain_tag", ""),
            generation_mode=request.get("generation_mode", ""),
            user_satisfaction=request.get("user_satisfaction"),
            exported_to_domain=request.get("exported_to_domain", False),
        )
        return _success(metadata)
    except Exception as e:
        logger.error(f"记录元数据失败: {e}")
        return _error(msg=str(e))


@router.post("/api/workflow/supplement/cleanup")
async def run_cleanup(request: Dict = Body(default={})):
    """
    清理过期的 Session 补充数据

    请求体：
    {
        "days": 30,  // 保留天数，默认 30
    }
    """
    try:
        days = request.get("days", 30)
        result = cleanup_expired_supplements(days)
        return _success(result)
    except Exception as e:
        logger.error(f"清理过期数据失败: {e}")
        return _error(msg=str(e))


@router.post("/api/workflow/supplement/ai-pulse")
async def ai_pulse_supplement(request: Dict = Body(...)):
    """
    AI-Pulse 补充：调用 AI-Pulse API 获取行业案例补充内容
    
    请求体：
    {
        "session_id": "会话 ID",
        "missing_item": "缺失项描述",
        "keywords": ["关键词1", "关键词2"]  // 可选，默认从 missing_item 提取
    }
    """
    from src.ai_pulse_client import AIPulseClient
    
    session_id = request.get("session_id", "")
    missing_item = request.get("missing_item", "")
    keywords = request.get("keywords", [])
    
    if not missing_item:
        return _error(code=400, msg="缺少 missing_item 参数")
    
    # 如果没有关键词，从缺失项描述中提取
    if not keywords:
        # 简单分词（实际可用 LLM 提取关键词）
        keywords = [missing_item[:20]]
    
    ai_pulse_config = _get_config("ai_pulse")
    if not ai_pulse_config.get("enabled", False):
        return _success({
            "cases": [],
            "message": "AI-Pulse 服务未启用，请手动补充",
        })
    
    try:
        import httpx
        client = AIPulseClient(
            base_url=ai_pulse_config.get("base_url", "http://8.130.148.166:8887"),
            timeout=ai_pulse_config.get("timeout", 5),  # 降低超时到5秒
        )
        
        # 第1次：用用户提供的关键词搜索
        cases = await client.fetch_latest_cases(
            keywords=keywords,
            days=7,
            take=5,
        )
        
        if not cases:
            # 第2次：用缺失项描述的前半部分搜索
            shorter_kw = [missing_item[:10]]
            cases = await client.fetch_latest_cases(
                keywords=shorter_kw,
                days=7,
                take=5,
            )
        
        if not cases:
            # 第3次：空关键词，获取热门案例
            cases = await client.fetch_latest_cases(
                keywords=[],
                days=7,
                take=5,
            )
        
        if not cases:
            return _success({
                "cases": [],
                "message": "未找到相关案例，请尝试手动补充",
            })
        
        # 格式化案例数据
        formatted_cases = []
        for case in cases:
            formatted_cases.append({
                "id": case.get("id", ""),
                "title": case.get("title", ""),
                "summary": case.get("summary", ""),
                "source": case.get("source", ""),
                "published_at": case.get("published_at", ""),
                "score": case.get("score", 0),
                "category": case.get("category", ""),
                "url": case.get("url", ""),
                "tags": case.get("tags", []),
            })
        
        return _success({
            "cases": formatted_cases,
            "total": len(formatted_cases),
            "keywords": keywords,
        })
    except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadTimeout) as e:
        logger.warning(f"AI-Pulse 服务超时: {e}")
        return _success({
            "cases": [],
            "message": "AI-Pulse 服务暂不可用，请尝试手动补充",
        })
    except Exception as e:
        logger.error(f"AI-Pulse 补充失败: {e}")
        return _success({
            "cases": [],
            "message": f"AI-Pulse 检索异常: {str(e)[:100]}",
        })


@router.post("/api/workflow/supplement/ai-infer")
async def ai_infer_supplement(request: Dict = Body(...)):
    """
    AI 推断补充：基于已有案例/内容进行推断生成
    支持多种场景：
    1. API案例+MCP推断
    2. 已有内容优化建议
    3. 纯MCP推断
    
    请求体：
    {
        "session_id": "会话 ID",
        "missing_item": "缺失项描述",
        "mcp_summary": "MCP 摘要",
        "selected_cases": [...],  // API 检索案例
        "existing_content": "已有补充内容"  // 可选，用于优化建议场景
    }
    """
    session_id = request.get("session_id", "")
    missing_item = request.get("missing_item", "")
    mcp_summary = request.get("mcp_summary", "")
    selected_cases = request.get("selected_cases", [])
    existing_content = request.get("existing_content", "")
    
    llm_config = _get_config("llm")
    base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = llm_config.get("api_key", "")
    model = llm_config.get("model", "deepseek-chat")
    timeout = llm_config.get("timeout", 60)
    
    persona_summary = ""
    try:
        persona_parsed = _get_persona_parsed()
        if persona_parsed:
            persona_summary = persona_parsed.get("summary", "")
    except:
        pass
    
    cases_context = ""
    if selected_cases:
        cases_list = "\n".join([
            f"• 【{c.get('title', '')}】\n  来源：{c.get('source', '')}\n  摘要：{c.get('summary', '')}"
            for c in selected_cases
        ])
        cases_context = f"\n【API 检索到的相关案例】\n{cases_list}"
    
    existing_context = ""
    if existing_content:
        existing_context = f"\n【已有补充内容】（请在此基础上优化）\n{existing_content}"
    
    if existing_content:
        prompt = f"""你是一个内容策划专家。请基于以下信息，为指定缺失项提供优化建议。

【缺失项】
{missing_item}

【MCP 素材摘要】
{mcp_summary}
{cases_context}
{existing_context}

【作者身份定位】
{persona_summary}

═══════════ 核心原则（必须严格执行）═══════════

【Cherry 补充原则】
1. 边界原则：用户原文说了什么 = 边界，绝不越界添加用户没说的观点
2. 增厚原则：用户说了但只说半句 = 帮他说完（拆层、加类比、加假设案例）
3. 不发明原则：用户完全没说的 = 不替他说，如需补充必须用疑问句式
4. 提问>断言：不确定时用"这可能意味着..."而不是"这是..."

【素材来源优先级】（严格按顺序使用）
- 第1层（最高优先）：用户原文中隐含但未展开的内容（标注：[原文推导]）
- 第2层：用户原文中类比指向的内容，帮用户说完（标注：[类比展开]）
- 第3层：公开资料中的通用知识（必须标注"根据公开资料..."）
- 第4层（绝对禁止）：编造具体数据（"据统计 80%..."）、编造人名/公司案例、编造研究报告

【补充比例控制】
- 原文 200 字 → 补充后理想 600-800 字（3-4倍）
- 超过 5 倍说明可能过度解读，请精简

请提供优化建议：
1. 指出已有内容的不足之处
2. 补充具体数据、案例或信息
3. 优化语言结构和表达
4. 确保内容可操作、有说服力

返回 JSON 格式：
{{
  "content": "优化后的完整内容",
  "supplement_type": "thicken",
  "confidence": 0.85,
  "inference_note": "说明优化要点"
}}

supplement_type 取值说明（必须选一个）：
- "thicken"（增厚）：用户说了但只说半句，需要展开/拆层/加类比。这类补充风险低，可自动采纳。
- "fill"（补全）：用户完全没说，但逻辑链有缺口（如缺反驳、缺边界条件）。这类补充可能改变文章走向，需用户确认。
- "infer"（推断）：基于公开资料的通用知识补充。需标注来源，用户确认后采纳。

confidence 评分标准（0-1）：
- 0.8-1.0：高置信度，补充内容与用户原文紧密相关
- 0.6-0.8：中置信度，补充内容合理但与原文关联度一般
- <0.6：低置信度，建议用户仔细审查

注意：
- 保留原有内容中有价值的部分
- 补充具体、可操作的信息
- 所有补充内容必须在开头标注来源：[原文推导]/[类比展开]/[公开资料]
- 宁可内容少而精，不要编造

请直接返回 JSON：
"""
    else:
        prompt = f"""你是一个内容策划专家。请根据以下信息，为指定的缺失项生成补充内容。

【工作流说明】
1. 用户已通过 AI-Pulse API 检索到外部案例（见下方"API 检索案例"）
2. 用户已勾选了需要的案例
3. 你需要基于 MCP 摘要 + 用户勾选的 API 案例，做上下文推断补充

【缺失项】
{missing_item}

【MCP 素材摘要】
{mcp_summary}
{cases_context}

【作者身份定位】（只影响语言风格，不影响内容事实）
{persona_summary}

═══════════ 核心原则（必须严格执行）═══════════

【Cherry 补充原则】
1. 边界原则：用户原文说了什么 = 边界，绝不越界添加用户没说的观点
2. 增厚原则：用户说了但只说半句 = 帮他说完（拆层、加类比、加假设案例）
3. 不发明原则：用户完全没说的 = 不替他说，如需补充必须用疑问句式
4. 提问>断言：不确定时用"这可能意味着..."而不是"这是..."

【素材来源优先级】（严格按顺序使用）
- 第1层（最高优先）：用户原文/MCP摘要中隐含但未展开的内容（标注：[原文推导]）
- 第2层：用户类比指向的内容，帮用户说完（标注：[类比展开]）
- 第3层：公开资料中的通用知识（必须标注"根据公开资料..."）
- 第4层（绝对禁止）：编造具体数据（"据统计 80%..."）、编造人名/公司案例、编造研究报告

【补充比例控制】
- 理想补充比例：原文 200 字 → 补充后 600-800 字（3-4倍）
- 超过 5 倍说明可能过度解读，请精简

请为这个缺失项生成补充内容，要求：
1. 优先引用 API 案例中的信息
2. 结合 MCP 摘要中的已有信息做推断
3. 如果 API 案例和 MCP 中都没有足够信息，基于公开资料做合理推断，并标注[公开资料]
4. 语言风格要符合作者身份定位（简洁、实战导向）
5. 内容要具体、可操作
6. 不确定时，用"这可能意味着..."句式，不要用断言

返回 JSON 格式（不要 markdown 代码块）：
{{
  "content": "生成的补充内容",
  "supplement_type": "fill",
  "confidence": 0.75,
  "inference_note": "说明推断依据，例如：'基于 API 案例 X + MCP 中的 Y 推断'"
}}

supplement_type 取值说明（必须选一个）：
- "thicken"（增厚）：用户说了但只说半句，需要展开/拆层/加类比。这类补充风险低，可自动采纳。
- "fill"（补全）：用户完全没说，但逻辑链有缺口（如缺反驳、缺边界条件）。这类补充可能改变文章走向，需用户确认。
- "infer"（推断）：基于公开资料的通用知识补充。需标注来源，用户确认后采纳。

confidence 评分标准（0-1）：
- 0.8-1.0：高置信度，补充内容与用户原文紧密相关
- 0.6-0.8：中置信度，补充内容合理但与原文关联度一般
- <0.6：低置信度，建议用户仔细审查

注意：
- 必须体现 API 案例中的关键信息（公司名、数据、效果等）
- 所有补充内容必须在开头标注来源：[原文推导]/[类比展开]/[公开资料]/[AI推断]
- 宁可内容少而精，不要编造

请直接返回 JSON：
"""
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2048,
                    "temperature": 0.3,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()
        
        parsed_content = result["choices"][0]["message"]["content"].strip()
        parsed_content = parsed_content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        supplement = json_mod.loads(parsed_content)
        
        # 确保返回格式包含新字段（Phase 3）
        supplement.setdefault("supplement_type", "infer")
        supplement.setdefault("confidence", 0.7)
        
        # 验证 supplement_type 取值范围
        valid_types = ["thicken", "fill", "infer"]
        if supplement.get("supplement_type") not in valid_types:
            supplement["supplement_type"] = "infer"
        
        # 验证 confidence 取值范围
        try:
            conf = float(supplement.get("confidence", 0.7))
            supplement["confidence"] = max(0.0, min(1.0, conf))
        except:
            supplement["confidence"] = 0.7
        
        return _success(supplement)
    except Exception as e:
        logger.error(f"AI 推断失败: {e}")
        return _error(msg=str(e))


@router.get("/api/kb/files")
async def get_kb_files(category: Optional[str] = None):
    """列出知识库文件"""
    try:
        kb = KnowledgeBaseReader(_get_config("knowledge_base"))
        files = kb.list_directory(category)
        return _success(files)
    except Exception as e:
        logger.error(f"列出知识库文件失败: {e}")
        return _error(msg=str(e))


@router.post("/api/kb/read")
async def read_kb_file(request: Dict = Body(...)):
    """读取知识库文件内容"""
    file_path = request.get("file_path")
    if not file_path:
        return _error(code=400, msg="缺少 file_path 参数")
    try:
        kb = KnowledgeBaseReader(_get_config("knowledge_base"))
        content = kb.read_file(file_path)
        if content is None:
            return _error(code=404, msg="文件不存在或无法读取")
        return _success({"content": content, "file_path": file_path})
    except Exception as e:
        logger.error(f"读取文件失败: {e}")
        return _error(msg=str(e))


# ===== 本地文件夹接口（新增） =====

ALLOWED_EXTENSIONS = {".md", ".txt", ".markdown", ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp"}
TEXT_EXTENSIONS = {".md", ".txt", ".markdown"}


@router.post("/api/folders/verify")
async def verify_folder(request: Dict = Body(...)):
    """验证文件夹是否存在并可读取"""
    folder_path = request.get("path", "")
    if not folder_path:
        return _error(code=400, msg="缺少 path 参数")
    try:
        path = Path(folder_path)
        if not path.exists():
            return _error(code=404, msg="文件夹不存在")
        if not path.is_dir():
            return _error(code=400, msg="路径不是文件夹")
        list(path.iterdir())
        return _success({"status": "connected", "path": str(path)})
    except PermissionError:
        return _error(code=403, msg="没有读取权限")
    except Exception as e:
        return _error(msg=str(e))


def _build_folder_tree(path: Path, base_path: Path, max_depth: int = 5, current_depth: int = 0) -> List[Dict]:
    """构建文件夹树形结构（优化版：排除隐藏文件夹、限制深度、快速统计）"""
    tree = []

    if current_depth >= max_depth:
        return tree

    # 排除隐藏文件夹
    subdirs = sorted(
        [d for d in path.iterdir() if d.is_dir() and not d.name.startswith('.')],
        key=lambda x: x.name
    )
    for subdir in subdirs:
        # 快速统计：只统计当前层的文件 + 子文件夹内的文件（不递归到深层）
        file_count = sum(
            1 for f in subdir.iterdir()
            if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS
        )
        # 加上子文件夹内的文件数
        for subsub in subdir.iterdir():
            if subsub.is_dir() and not subsub.name.startswith('.'):
                file_count += sum(
                    1 for f in subsub.iterdir()
                    if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS
                )
        children = _build_folder_tree(subdir, base_path, max_depth, current_depth + 1)
        tree.append({
            "type": "folder",
            "name": subdir.name,
            "path": str(subdir.relative_to(base_path)),
            "full_path": str(subdir),
            "children": children,
            "file_count": file_count,
        })

    # 只处理允许扩展名的文件
    files = sorted(
        [f for f in path.iterdir() if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS],
        key=lambda x: x.name
    )
    for file_path in files:
        rel_path = str(file_path.relative_to(base_path))
        tree.append({
            "type": "file",
            "name": file_path.name,
            "path": rel_path,
            "full_path": str(file_path),
            "size": file_path.stat().st_size,
        })

    return tree


@router.post("/api/folders/list")
async def list_folder_files(request: Dict = Body(...)):
    """列出文件夹结构（返回树形结构，包含子文件夹）"""
    folder_path = request.get("path", "")
    if not folder_path:
        return _error(code=400, msg="缺少 path 参数")
    try:
        path = Path(folder_path)
        if not path.exists() or not path.is_dir():
            return _error(code=404, msg="文件夹不存在")

        tree = _build_folder_tree(path, path)
        return _success(tree)
    except PermissionError:
        return _error(code=403, msg="没有读取权限")
    except Exception as e:
        return _error(msg=str(e))


@router.post("/api/folders/read")
async def read_folder_file(request: Dict = Body(...)):
    """读取文件夹中的文件内容"""
    folder_path = request.get("folder_path", "")
    file_path = request.get("file_path", "")
    if not folder_path or not file_path:
        return _error(code=400, msg="缺少 folder_path 或 file_path 参数")
    try:
        full_path = Path(folder_path) / file_path
        if not full_path.exists():
            return _error(code=404, msg="文件不存在")
        content = full_path.read_text(encoding="utf-8")
        return _success({"content": content, "file_path": str(full_path)})
    except UnicodeDecodeError:
        return _error(code=400, msg="文件不是文本格式")
    except PermissionError:
        return _error(code=403, msg="没有读取权限")
    except Exception as e:
        return _error(msg=str(e))


# ===== 分类器接口 =====

@router.get("/api/categories")
async def get_categories():
    """获取分类列表"""
    classifier = ContentClassifier(_get_config("llm"))
    return _success(classifier.get_categories())


@router.post("/api/classify/intent")
async def classify_by_intent(request: Dict = Body(...)):
    """语义理解分类"""
    text = request.get("text", "")
    if not text:
        return _error(code=400, msg="缺少 text 参数")
    try:
        classifier = ContentClassifier(_get_config("llm"))
        result = classifier.classify_by_intent(text)
        return _success(result)
    except Exception as e:
        logger.error(f"分类失败: {e}")
        return _error(msg=str(e))


# ===== 框架匹配接口 =====

@router.post("/api/frameworks/match")
async def match_frameworks(request: Dict = Body(...)):
    """框架匹配"""
    text = request.get("text", "")
    category = request.get("category")
    top_n = request.get("top_n", 10)
    mcp_summary = request.get("mcp_summary", "")
    if not text:
        return _error(code=400, msg="缺少 text 参数")
    try:
        matcher = FrameworkMatcher(_get_config("llm"))
        result = matcher.match_frameworks(text, category, top_n)

        # 确保返回新增字段
        for fw in result:
            fw.setdefault("usage_guide", "")
            fw.setdefault("logic_description", "")
            fw.setdefault("full_description", "")
            # 添加关键词标签
            fw_def = matcher.FRAMEWORKS.get(fw["key"], {})
            fw["keywords"] = fw_def.get("keywords", [])[:8]  # 最多显示 8 个关键词
            fw["full_description"] = fw_def.get("full_description", "")

        if mcp_summary:
            for fw in result:
                preflight = matcher.preflight_check(mcp_summary, fw["key"])
                fw["preflight"] = preflight

        return _success(result)
    except Exception as e:
        logger.error(f"框架匹配失败: {e}")
        return _error(msg=str(e))


@router.post("/api/frameworks")
async def get_all_frameworks(request: Dict = Body(...)):
    """
    获取所有框架定义（用于自定义选择）
    支持传入 text 进行匹配评分和字段预检
    """
    matcher = FrameworkMatcher()
    all_fw = matcher.get_all_frameworks()
    text = request.get("text", "")
    mcp_summary = request.get("mcp_summary", "")
    search_text = mcp_summary or text
    
    result = []
    for key, fw in all_fw.items():
        fw_info = {
            "key": key,
            "name": fw["name"],
            "description": fw["description"],
            "usage_guide": fw.get("usage_guide", ""),
            "logic_description": fw.get("logic_description", ""),
            "layout_style": fw["layout_style"],
            "categories": fw["categories"],
        }
        # 如果有文本，计算匹配度和字段预检
        if search_text:
            # 计算匹配度（关键词+语义）
            kw_scores = matcher._keyword_match(search_text)
            sem_scores = matcher._semantic_match(search_text)
            score = kw_scores.get(key, 0) * matcher.KEYWORD_WEIGHT + sem_scores.get(key, 0) * matcher.SEMANTIC_WEIGHT
            fw_info["score"] = round(score, 3)
            fw_info["preflight"] = matcher.preflight_check(search_text, key)
        
        result.append(fw_info)
    
    return _success(result)


@router.get("/api/frameworks/detail/{framework_key}")
async def get_framework(framework_key: str):
    """获取框架详情"""
    matcher = FrameworkMatcher()
    fw = matcher.get_framework(framework_key)
    if not fw:
        return _error(code=404, msg="框架不存在")
    return _success(fw)


@router.post("/api/data/preflight")
async def data_preflight(request: Dict = Body(...)):
    """
    数据预检：评估框架字段的数据可获取性（轻量，关键词匹配）

    请求体：
    {
        "text": "MCP 总结或用户输入内容",
        "framework_key": "swot"
    }
    """
    text = request.get("text", "")
    framework_key = request.get("framework_key", "")
    if not text or not framework_key:
        return _error(code=400, msg="缺少 text 或 framework_key 参数")
    try:
        matcher = FrameworkMatcher()
        result = matcher.preflight_check(text, framework_key)
        return _success(result)
    except Exception as e:
        logger.error(f"数据预检失败: {e}")
        return _error(msg=str(e))


@router.post("/api/data/ai_generate")
async def ai_generate_field(request: Dict = Body(...)):
    """
    AI 辅助生成单个字段

    请求体：
    {
        "framework_key": "system",
        "field_key": "overview",
        "field_label": "系统概述",
        "existing_data": {"title": "Agent 分析"},
        "source_text": "MCP 总结或用户输入"
    }
    """
    framework_key = request.get("framework_key", "")
    field_key = request.get("field_key", "")
    field_label = request.get("field_label", "")
    existing_data = request.get("existing_data", {})
    source_text = request.get("source_text", "")

    if not framework_key or not field_key:
        return _error(code=400, msg="缺少 framework_key 或 field_key 参数")

    try:
        llm_config = _get_config("llm")
        headers = {
            "Authorization": f"Bearer {llm_config.get('api_key', '')}",
            "Content-Type": "application/json",
        }

        existing_context = ""
        if existing_data:
            existing_context = f"\n已填写的其他字段：\n{json.dumps(existing_data, ensure_ascii=False, indent=2)}"

        source_context = f"\n参考资料：\n{source_text[:3000]}" if source_text else ""

        prompt = f"""你是一个专业的分析师。请帮我填写「{field_label}」这个字段。

框架类型：{framework_key}
字段名称：{field_key}
字段含义：{field_label}{existing_context}{source_context}

请直接输出该字段的内容（JSON 数组格式或字符串），不要输出其他说明。
"""

        import httpx
        async with httpx.AsyncClient(timeout=llm_config.get("timeout", 30)) as client:
            response = await client.post(
                f"{llm_config.get('base_url', 'https://api.deepseek.com/v1')}/chat/completions",
                headers=headers,
                json={
                    "model": llm_config.get("model", "deepseek-chat"),
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                    "temperature": 0,  # 固定为 0，确保相同输入产生一致输出
                },
            )
            response.raise_for_status()
            result = response.json()

        content = result["choices"][0]["message"]["content"].strip()
        return _success({"content": content})

    except Exception as e:
        logger.error(f"AI 辅助生成失败: {e}")
        return _error(msg=str(e))


@router.post("/api/data/autopopulate")
async def data_autopopulate(request: Dict = Body(...)):
    """
    数据自动填充：使用 LLM 从原文萃取数据，填充框架字段

    请求体：
    {
        "text": "MCP 总结或用户输入内容",
        "framework_key": "business_canvas"
    }
    """
    text = request.get("text", "")
    framework_key = request.get("framework_key", "")
    if not text or not framework_key:
        return _error(code=400, msg="缺少 text 或 framework_key 参数")
    try:
        matcher = FrameworkMatcher(_get_config("llm"))
        result = matcher.autopopulate(text, framework_key)
        return _success(result)
    except Exception as e:
        logger.error(f"数据自动填充失败: {e}")
        return _error(msg=str(e))


# ===== 数据检查接口 =====

@router.post("/api/data/check")
async def check_data_completeness(request: Dict = Body(...)):
    """数据完整性检查"""
    data = request.get("data", {})
    framework_key = request.get("framework_key")
    if not framework_key:
        return _error(code=400, msg="缺少 framework_key 参数")
    try:
        checker = DataCompletenessChecker()
        result = checker.check_completeness(data, framework_key)
        return _success(result)
    except Exception as e:
        logger.error(f"数据检查失败: {e}")
        return _error(msg=str(e))


# ===== 生成接口 =====

@router.post("/api/generate")
async def generate_diagram(
    framework_key: str = Form(...),
    text: str = Form(...),
    style: str = Form("minimal"),
    size: str = Form("default"),
):
    """生成架构图"""
    try:
        logger.info(f"收到生成请求: 框架={framework_key}")

        extractor = StructureExtractor(_get_config("llm"))
        data = extractor.extract(text, framework_key)

        generator = HTMLGenerator(_get_config("storage"))
        html = generator.render(data, framework_key, style, size)

        output_dir = Path(_get_config("storage").get("output_dir", "output"))
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{uuid.uuid4().hex}.png"

        screenshot = ScreenshotService()
        await screenshot.capture(html, str(output_path), size)

        logger.info(f"生成完成: {output_path}")
        return FileResponse(str(output_path), media_type="image/png", filename="diagram.png")

    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=f"功能未实现: {str(e)}")
    except Exception as e:
        logger.error(f"生成失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.post("/api/generate/preview")
async def generate_preview(request: Dict = Body(...)):
    """生成预览（返回 HTML）"""
    framework_key = request.get("framework_key")
    data = request.get("data", {})
    source_text = request.get("source_text", "")
    style = request.get("style", "minimal")
    size = request.get("size", "default")

    if not framework_key:
        return _error(code=400, msg="缺少 framework_key 参数")

    try:
        generator = HTMLGenerator(_get_config("storage"))
        # 容缺模式：LLM 基于用户数据和原文补全缺失字段
        if source_text and data:
            extractor = StructureExtractor(_get_config("llm"))
            try:
                extracted = extractor.extract(source_text, framework_key, user_data=data)
                html = generator.render(extracted, framework_key, style, size)
            except Exception as llm_err:
                logger.warning(f"LLM 提取失败，直接使用用户数据: {llm_err}")
                html = generator.render(data, framework_key, style, size)
        else:
            html = generator.render(data, framework_key, style, size)
        return _success({"html": html})
    except Exception as e:
        logger.error(f"预览生成失败: {e}")
        return _error(msg=str(e))


@router.post("/api/generate/async")
async def generate_diagram_async(
    background_tasks: BackgroundTasks,
    framework_key: str = Form(...),
    text: str = Form(...),
    style: str = Form("minimal"),
    size: str = Form("default"),
):
    """异步生成架构图"""
    task_id = str(uuid.uuid4())
    async_tasks[task_id] = {"status": "pending", "progress": 0}
    background_tasks.add_task(_process_async, task_id, framework_key, text, style, size)
    return _success({"task_id": task_id})


@router.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    """查询异步任务进度"""
    if task_id not in async_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    return _success(async_tasks[task_id])


# ===== 辅助接口 =====

@router.get("/api/styles")
async def get_styles():
    """获取支持的样式"""
    return _success(HTMLGenerator.STYLES)


@router.get("/api/sizes")
async def get_sizes():
    """获取支持的尺寸"""
    return _success(HTMLGenerator.SIZES)


@router.get("/api/health")
async def health_check():
    """健康检查"""
    return _success({"status": "ok", "version": "2.0.0"})


# ===== 方向建议接口 =====

@router.post("/api/directions/analyze")
async def analyze_directions(request: Dict = Body(...)):
    """
    混合模式方向推荐：关键词初筛 + LLM 精排。
    返回方向建议列表，每个包含推荐理由。
    """
    summary = request.get("summary", "")
    
    if not summary:
        return _error(code=400, msg="缺少 summary 参数")
    
    # 方向模板
    direction_templates = [
        {
            "name": "技术深度分析",
            "description": "从技术架构、算法实现、系统性能等角度深入分析，适合技术博客、架构文档。",
            "keywords": ["架构", "算法", "模型", "实现", "技术", "代码", "框架", "系统", "API", "性能", "协议", "接口"],
            "frameworks": ["系统架构分析", "流程分析", "因果分析"],
            "supplement_hints": ["具体技术实现细节", "性能测试数据", "代码示例"],
        },
        {
            "name": "商业趋势解读",
            "description": "从商业模式、市场竞争、投融资等角度分析行业趋势，适合商业分析、投资参考。",
            "keywords": ["商业", "市场", "融资", "营收", "模式", "竞品", "战略", "投资", "估值", "盈利", "客户", "收入"],
            "frameworks": ["商业模式画布", "SWOT 分析", "PESTEL 分析"],
            "supplement_hints": ["商业模式数据", "竞品融资情况", "市场规模预测"],
        },
        {
            "name": "应用场景拆解",
            "description": "从具体应用场景、用户痛点、解决方案等角度分析，适合产品分析、案例研究。",
            "keywords": ["产品", "功能", "用户", "体验", "设计", "交互", "需求", "场景", "痛点", "用例", "实践"],
            "frameworks": ["用户旅程地图", "流程分析", "对比分析"],
            "supplement_hints": ["用户画像", "使用场景数据", "效果评估指标"],
        },
        {
            "name": "竞品对比评估",
            "description": "对比多个方案/产品的优劣势，给出选型建议，适合技术选型、产品对比。",
            "keywords": ["对比", "比较", "差异", "优势", "劣势", "选型", "vs", "评估", "竞争", "替代", "选择"],
            "frameworks": ["对比分析", "SWOT 分析", "主张型分析"],
            "supplement_hints": ["更多竞品数据", "性能对比指标", "价格信息"],
        },
        {
            "name": "行业研究报告",
            "description": "从宏观环境、政策影响、市场规模等角度撰写行业报告，适合投资分析、战略规划。",
            "keywords": ["趋势", "预测", "行业", "宏观", "环境", "政策", "规模", "增长", "未来", "发展", "影响"],
            "frameworks": ["PESTEL 分析", "主张型分析", "对比分析"],
            "supplement_hints": ["行业统计数据", "政策文件引用", "专家观点"],
        },
    ]
    
    import re
    
    def calc_coverage(template, summary_text):
        """计算某个方向的资料覆盖度（基于关键词匹配）"""
        score = 0.25
        
        target_keywords = template["keywords"]
        match_count = sum(1 for kw in target_keywords if kw in summary_text)
        keyword_ratio = match_count / len(target_keywords)
        score += keyword_ratio * 0.55
        
        word_count = len(summary_text)
        if word_count > 3000:
            score += 0.15
        elif word_count > 1500:
            score += 0.1
        elif word_count > 500:
            score += 0.05
            
        return min(round(score, 2), 1.0)
    
    # Step 1: 关键词初筛，取 Top 3 给 LLM 精排
    candidates = []
    for tpl in direction_templates:
        coverage = calc_coverage(tpl, summary)
        candidates.append({
            "template": tpl,
            "coverage": coverage,
        })
    candidates.sort(key=lambda x: x["coverage"], reverse=True)
    top_candidates = candidates[:3]
    
    # Step 2: LLM 精排（如果 LLM 失败，降级为关键词结果）
    llm_scores = {}
    try:
        llm_config = _get_config("llm")
        
        direction_list = "\n".join([f"- {c['template']['name']}: {c['template']['description']}" for c in top_candidates])
        
        prompt = f"""基于以下资料总结，请分析该资料最适合哪些写作方向：

资料总结：
{summary[:3000]}

请从以下方向中，选出最适合的 5 个，按适合程度排序，并给出评分和简短理由：
{direction_list}

评分标准：
- 0.8-1.0: 强烈推荐（资料非常充足，完全适合该方向）
- 0.6-0.8: 推荐（资料较充足，基本适合该方向）
- 0.4-0.6: 可以考虑（资料一般，需要补充一些内容）
- 0.2-0.4: 不太适合（资料较少，勉强可以写）

返回 JSON 格式（不要 markdown 代码块）：
[{{"name": "方向名", "score": 0.85, "reason": "因为资料中...", "confidence_label": "强烈推荐|推荐|可以考虑|不太适合"}}]
"""
        
        import httpx
        async with httpx.AsyncClient(timeout=llm_config.get("timeout", 30)) as client:
            response = await client.post(
                f"{llm_config.get('base_url', 'https://api.deepseek.com/v1')}/chat/completions",
                headers={"Authorization": f"Bearer {llm_config.get('api_key', '')}"},
                json={
                    "model": llm_config.get("model", "deepseek-chat"),
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 512,
                    "temperature": 0.2,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()
        
        content = result["choices"][0]["message"]["content"].strip()
        content = content.replace("```json", "").replace("```", "").strip()
        import json
        llm_scores = json.loads(content)
        logger.info(f"LLM 方向精排: {llm_scores}")
    except Exception as e:
        logger.warning(f"LLM 方向精排失败，降级为关键词匹配: {e}")
        llm_scores = []
    
    # Step 3: 合并关键词覆盖度和 LLM 评分
    directions = []
    file_count = len(re.findall(r'##\s', summary))
    
    for tpl in direction_templates:
        coverage = calc_coverage(tpl, summary)
        
        # 查找 LLM 评分
        llm_info = None
        if llm_scores:
            for item in llm_scores:
                if item.get("name") == tpl["name"]:
                    llm_info = item
                    break
        
        # 综合评分：关键词覆盖度 * 0.4 + LLM评分 * 0.6
        if llm_info:
            final_score = round(coverage * 0.4 + llm_info.get("score", 0.5) * 0.6, 2)
            reason = llm_info.get("reason", "")
            confidence_label = llm_info.get("confidence_label", "")
        else:
            final_score = coverage
            reason = f"资料中关键词覆盖度为 {int(coverage * 100)}%"
            # 自动生成置信度标签
            if final_score >= 0.8:
                confidence_label = "强烈推荐"
            elif final_score >= 0.6:
                confidence_label = "推荐"
            elif final_score >= 0.4:
                confidence_label = "可以考虑"
            else:
                confidence_label = "不太适合"
        
        covered = max(1, int(final_score * file_count)) if file_count > 0 else 1
        
        # 置信度颜色
        confidence_colors = {
            "强烈推荐": "green",
            "推荐": "arcoblue",
            "可以考虑": "orange",
            "不太适合": "gray",
        }
        
        directions.append({
            "name": tpl["name"],
            "description": tpl["description"],
            "coverage": final_score,
            "coveredCount": covered,
            "totalCount": file_count or 1,
            "frameworks": tpl["frameworks"],
            "needsSupplement": tpl["supplement_hints"],
            "reason": reason,
            "confidence_label": confidence_label,
            "confidence_color": confidence_colors.get(confidence_label, "gray"),
        })
    
    # 按综合评分排序，固定返回5个（不足5个也返回）
    directions.sort(key=lambda x: x["coverage"], reverse=True)
    
    if not directions:
        directions = [{
            "name": "综合分析报告",
            "description": "从多个维度全面分析该主题，适合通用性研究。",
            "coverage": 0.5,
            "coveredCount": max(1, (file_count or 1) // 2),
            "totalCount": file_count or 1,
            "frameworks": ["主张型分析", "系统架构分析"],
            "needsSupplement": ["具体数据支撑"],
            "reason": "资料内容较为综合，适合多角度分析",
        }]
    
    return _success(directions[:5])


@router.post("/api/content/structure")
async def generate_content_structure(request: Dict = Body(...)):
    """
    根据方向和原文，生成内容结构和 AI 提示。
    返回分段结构，每段包含：标题、AI 提示、建议字数、原文参考。
    """
    direction_name = request.get("direction_name", "")
    summary = request.get("summary", "")
    topic_needed = request.get("topic_needed", "")  # MCP 建议补充内容
    
    if not direction_name:
        return _error(code=400, msg="缺少 direction_name 参数")
    
    # 不同方向的内容结构模板
    structure_templates = {
        "技术深度分析": {
            "intro": {
                "title": "引言",
                "hint": "简要介绍技术背景和研究动机。说明为什么这个技术值得深入分析，当前面临的主要挑战是什么。",
                "word_count": "100-200",
            },
            "sections": [
                {
                    "title": "技术架构解析",
                    "hint": "从整体架构角度拆解该系统/技术。描述核心组件、数据流向、模块之间的交互关系。可配架构图说明。",
                    "word_count": "300-500",
                },
                {
                    "title": "核心算法/实现原理",
                    "hint": "深入分析关键技术实现。选取 1-2 个最具代表性的算法或技术方案，详细说明其工作原理、创新点和局限。",
                    "word_count": "300-500",
                },
                {
                    "title": "性能与优化",
                    "hint": "评估该技术方案的效能表现。包括性能指标、瓶颈分析、优化方向。有数据支撑更好。",
                    "word_count": "200-300",
                },
                {
                    "title": "应用场景与实践",
                    "hint": "列举该技术在实际场景中的应用案例。描述具体用法、解决的问题和效果。",
                    "word_count": "200-300",
                },
            ],
            "conclusion": {
                "title": "总结与展望",
                "hint": "总结该技术的核心价值和发展前景。指出当前局限和未来可能的突破方向。",
                "word_count": "150-250",
            },
        },
        "商业趋势解读": {
            "intro": {
                "title": "行业概览",
                "hint": "概述当前行业现状和市场规模。说明分析对象在行业中的位置。",
                "word_count": "150-250",
            },
            "sections": [
                {
                    "title": "市场格局与竞争态势",
                    "hint": "分析主要参与者和市场份额分布。描述竞争格局是垄断、寡头还是分散。",
                    "word_count": "250-400",
                },
                {
                    "title": "商业模式拆解",
                    "hint": "深入分析核心盈利模式和收入来源。说明价值主张、客户群体和定价策略。",
                    "word_count": "250-400",
                },
                {
                    "title": "发展趋势与驱动因素",
                    "hint": "分析推动行业发展的关键因素（技术、政策、消费等）。预测未来 1-3 年的发展趋势。",
                    "word_count": "250-400",
                },
                {
                    "title": "风险与挑战",
                    "hint": "指出行业面临的主要风险和不确定性。包括政策风险、技术风险、市场风险等。",
                    "word_count": "200-300",
                },
            ],
            "conclusion": {
                "title": "投资建议与展望",
                "hint": "给出综合判断和投资参考建议。说明看好或看淡的理由。",
                "word_count": "150-250",
            },
        },
        "应用场景拆解": {
            "intro": {
                "title": "场景概述",
                "hint": "简要描述所分析的应用场景和用户痛点。说明为什么这个场景值得研究。",
                "word_count": "100-200",
            },
            "sections": [
                {
                    "title": "用户画像与需求分析",
                    "hint": "描述目标用户特征和使用场景。分析用户的核心需求和期望。",
                    "word_count": "250-400",
                },
                {
                    "title": "解决方案设计",
                    "hint": "详细描述针对该场景的解决方案。包括功能设计、交互流程、技术选型等。",
                    "word_count": "300-500",
                },
                {
                    "title": "实施效果评估",
                    "hint": "评估方案的实际效果。包括用户反馈、数据指标、ROI 等。有对比数据更好。",
                    "word_count": "200-300",
                },
                {
                    "title": "经验总结与可复用性",
                    "hint": "总结该场景下的成功经验和可复用的方法论。说明哪些做法可以推广到其他场景。",
                    "word_count": "200-300",
                },
            ],
            "conclusion": {
                "title": "展望与建议",
                "hint": "对该场景的未来发展做出预测。给出行内从业者的实用建议。",
                "word_count": "150-250",
            },
        },
        "竞品对比评估": {
            "intro": {
                "title": "对比背景",
                "hint": "说明对比的目的和选取的竞品范围。定义评价维度和权重。",
                "word_count": "100-200",
            },
            "sections": [
                {
                    "title": "竞品概览",
                    "hint": "逐一介绍参与对比的各方案/产品。包括定位、核心特点、市场份额等。",
                    "word_count": "250-400",
                },
                {
                    "title": "多维度对比分析",
                    "hint": "从性能、成本、易用性、扩展性等维度逐项对比。用表格或雷达图呈现更直观。",
                    "word_count": "300-500",
                },
                {
                    "title": "优劣势总结",
                    "hint": "归纳各方案的核心优势和明显短板。指出各自的适用场景。",
                    "word_count": "250-400",
                },
                {
                    "title": "选型建议",
                    "hint": "根据不同使用场景给出选型建议。说明什么情况下选 A、什么情况下选 B。",
                    "word_count": "200-300",
                },
            ],
            "conclusion": {
                "title": "结论",
                "hint": "给出综合结论。如果有明显赢家则明确指出，否则说明各有所长。",
                "word_count": "100-200",
            },
        },
        "行业研究报告": {
            "intro": {
                "title": "执行摘要",
                "hint": "用一段话概括报告的核心发现和结论。让读者快速了解全文要点。",
                "word_count": "150-250",
            },
            "sections": [
                {
                    "title": "宏观环境分析（PEST）",
                    "hint": "从政策、经济、社会、技术四个维度分析外部环境对行业的影响。",
                    "word_count": "300-500",
                },
                {
                    "title": "行业现状与规模",
                    "hint": "描述行业当前发展水平和市场规模。用数据说明增长趋势。",
                    "word_count": "250-400",
                },
                {
                    "title": "产业链与竞争格局",
                    "hint": "分析产业链上下游关系和主要参与者。描述竞争格局和集中度。",
                    "word_count": "250-400",
                },
                {
                    "title": "发展趋势预测",
                    "hint": "基于当前态势预测未来 3-5 年的发展方向。指出关键转折点和机遇。",
                    "word_count": "250-400",
                },
                {
                    "title": "政策与建议",
                    "hint": "分析相关政策影响。给政府、企业、投资者不同角色的建议。",
                    "word_count": "200-300",
                },
            ],
            "conclusion": {
                "title": "结语",
                "hint": "总结全文核心观点。重申最重要的发现和预测。",
                "word_count": "100-200",
            },
        },
        "综合分析报告": {
            "intro": {
                "title": "引言",
                "hint": "简要介绍分析主题和背景。说明分析的目的和范围。",
                "word_count": "100-200",
            },
            "sections": [
                {
                    "title": "现状分析",
                    "hint": "描述当前情况的各方面表现。从多个角度客观陈述事实。",
                    "word_count": "250-400",
                },
                {
                    "title": "问题与挑战",
                    "hint": "指出当前存在的主要问题和面临的挑战。分析问题的成因和影响。",
                    "word_count": "200-300",
                },
                {
                    "title": "机遇与优势",
                    "hint": "分析有利条件和潜在机遇。说明可以把握的机会和已有的优势。",
                    "word_count": "200-300",
                },
                {
                    "title": "对策与建议",
                    "hint": "提出针对性的解决方案和建议。分优先级和可行性进行排序。",
                    "word_count": "250-400",
                },
            ],
            "conclusion": {
                "title": "总结",
                "hint": "概括全文要点。给出综合判断和最终建议。",
                "word_count": "100-200",
            },
        },
    }
    
    # 获取对应方向的结构模板
    template = structure_templates.get(direction_name, structure_templates["综合分析报告"])
    
    # 构建段落标题列表，用于 LLM 分发
    all_section_titles = []
    if template.get("intro"):
        all_section_titles.append({"key": "intro", "title": template["intro"]["title"]})
    for i, sec in enumerate(template.get("sections", [])):
        all_section_titles.append({"key": f"section_{i}", "title": sec["title"]})
    if template.get("conclusion"):
        all_section_titles.append({"key": "conclusion", "title": template["conclusion"]["title"]})
    
    # LLM 智能生成段落提纲 + 逐段分析：为每个段落生成写作思路，并分析原文匹配度
    pre_filled = {}
    section_outlines = {}
    section_analysis = {}
    llm_success = False
    try:
        llm_config = _get_config("llm")
        
        section_outline = "\n".join([f"- [{s['key']}] {s['title']}" for s in all_section_titles])
        
        # 获取身份定位文件内容（如果存在）
        persona_content = _get_persona_summary()
        persona_context = f"\n\n作者身份定位：\n{persona_content}" if persona_content else ""
        
        # MCP 建议补充内容
        mcp_needed_context = f"\n\nMCP 分析建议补充：\n{topic_needed}" if topic_needed else ""
        
        prompt = f"""你是一个专业的内容策划师。请根据以下资料，为文章的每个段落生成详细写作提纲。

资料总结：
{summary[:4000]}

文章结构：
{section_outline}
{persona_context}{mcp_needed_context}

【内容比例策略】
- 理论内容≤20%，实战内容≥80%
- 如果案例/素材不足，请在提纲中标注【案例占位符】位置
- 每个段落的 evidence 字段应该明确标注：
  * 有真实案例 → 案例简述（1-2句）
  * 无真实案例 → [📌 待补充：xxx 类型案例]

要求：
1. 为每个段落生成详细写作提纲，包含以下5个字段：
   - core_point: 核心观点（该段落要表达什么，1-2句话）
   - evidence: 论据支撑（用什么数据/案例/理论支撑，1-2句话）
   - angle: 写作角度（从什么角度切入，1句话）
   - materials: 可用素材（参考资料中哪些内容可以用，1-2句话）
   - notes: 注意事项（需要避免什么，1句话）
2. 每个字段都要具体、明确，信息量充足
3. 分析原文充足程度：
   - "use_original": 原文内容充足，提纲可直接基于原文
   - "supplement": 原文有部分相关内容，提纲需要结合原文和补充内容
   - "add_new": 原文缺少该部分内容，提纲主要靠逻辑推演或外部知识
4. 如果是 supplement 或 add_new，在 suggestion 中说明需要补充什么
5. **如果提供了"MCP 分析建议补充"，请在相关段落中体现这些建议，说明在哪个段落补充什么内容**
6. 返回 JSON 格式（不要 markdown 代码块）：
{{
  "outlines": {{
    "intro": {{
      "core_point": "核心观点...",
      "evidence": "论据支撑...",
      "angle": "写作角度...",
      "materials": "可用素材...",
      "notes": "注意事项..."
    }},
    "section_0": {{...}},
    ...
  }},
  "analysis": {{
    "intro": {{"type": "use_original|supplement|add_new", "suggestion": "建议内容"}},
    ...
  }}
}}

注意：提纲不是正文，是写作思路和方向指引。每个字段都要具体，不要泛泛而谈。
当案例不足时，请在 evidence 中使用占位符格式。

请直接返回 JSON：
"""
        
        import httpx
        async with httpx.AsyncClient(timeout=llm_config.get("timeout", 60)) as client:
            response = await client.post(
                f"{llm_config.get('base_url', 'https://api.deepseek.com/v1')}/chat/completions",
                headers={"Authorization": f"Bearer {llm_config.get('api_key', '')}"},
                json={
                    "model": llm_config.get("model", "deepseek-chat"),
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 8192,
                    "temperature": 0.2,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()
        
        content = result["choices"][0]["message"]["content"].strip()
        content = content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        parsed = json_mod.loads(content)
        section_outlines = parsed.get("outlines", {})
        section_analysis = parsed.get("analysis", {})
        llm_success = True
        logger.info(f"LLM 提纲生成完成，{len(section_outlines)} 个段落")
    except Exception as e:
        logger.warning(f"LLM 提纲生成失败: {e}，使用默认提示作为回退")
        for section_info in all_section_titles:
            section_outlines[section_info["key"]] = section_info.get("hint", "")
            section_analysis[section_info["key"]] = {
                "type": "add_new",
                "suggestion": "根据段落标题和提示撰写内容"
            }
    
    # 为每个段落添加提纲、置信度和分析建议
    analysis_type_labels = {
        "use_original": "原文充足",
        "supplement": "建议补充",
        "add_new": "需要添加",
    }
    analysis_type_colors = {
        "use_original": "green",
        "supplement": "orangered",
        "add_new": "gray",
    }
    
    def build_section_with_outline(section_info, outline_data, analysis_data):
        key = section_info["key"]
        title = section_info["title"]
        hint = section_info.get("hint", "")
        word_count = section_info.get("word_count", "")
        
        outline = outline_data.get(key, "")
        analysis = analysis_data.get(key, {})
        analysis_type = analysis.get("type", "add_new")
        analysis_suggestion = analysis.get("suggestion", "")
        
        # 判断置信度（基于原文充足程度）
        if analysis_type == "use_original":
            confidence = "high"
        elif analysis_type == "supplement":
            confidence = "medium"
        else:
            confidence = "low"
        
        return {
            "key": key,
            "title": title,
            "hint": hint,
            "word_count": word_count,
            "outline": outline,
            "confidence": confidence,
            "analysis_type": analysis_type,
            "analysis_label": analysis_type_labels.get(analysis_type, "需要添加"),
            "analysis_color": analysis_type_colors.get(analysis_type, "gray"),
            "analysis_suggestion": analysis_suggestion,
        }
    
    # 构建返回结构
    result_structure = {
        "direction": direction_name,
        "intro": build_section_with_outline(
            {"key": "intro", "title": template["intro"]["title"], "hint": template["intro"]["hint"], "word_count": template["intro"]["word_count"]},
            section_outlines, section_analysis
        ) if template.get("intro") else None,
        "sections": [
            build_section_with_outline(
                {"key": f"section_{i}", "title": sec["title"], "hint": sec["hint"], "word_count": sec["word_count"]},
                section_outlines, section_analysis
            )
            for i, sec in enumerate(template.get("sections", []))
        ],
        "conclusion": build_section_with_outline(
            {"key": "conclusion", "title": template["conclusion"]["title"], "hint": template["conclusion"]["hint"], "word_count": template["conclusion"]["word_count"]},
            section_outlines, section_analysis
        ) if template.get("conclusion") else None,
        "original_reference": summary[:500] if len(summary) > 500 else summary,
        "total_sections": len(template.get("sections", [])),
    }
    
    return _success(result_structure)


@router.post("/api/content/outline_versions")
async def generate_outline_versions(request: Dict = Body(...)):
    """
    为单个段落生成 3 个不同风格的写作提纲版本。
    
    请求体：
    {
        "direction_name": "技术深度分析",
        "section_key": "intro",
        "section_title": "引言",
        "section_hint": "简要介绍技术背景...",
        "summary": "MCP 总结全文",
        "topic_needed": "MCP 建议补充内容"
    }
    """
    direction_name = request.get("direction_name", "")
    section_key = request.get("section_key", "")
    section_title = request.get("section_title", "")
    section_hint = request.get("section_hint", "")
    summary = request.get("summary", "")
    topic_needed = request.get("topic_needed", "")
    
    if not direction_name or not section_key:
        return _error(code=400, msg="缺少 direction_name 或 section_key 参数")
    
    try:
        llm_config = _get_config("llm")
        
        persona_content = _get_persona_summary()
        persona_context = f"\n\n作者身份定位：\n{persona_content}" if persona_content else ""
        mcp_needed_context = f"\n\nMCP 分析建议补充：\n{topic_needed}" if topic_needed else ""
        
        prompt = f"""你是一个专业的内容策划师。请为文章的【{section_title}】段落生成 3 个不同风格的写作提纲。

资料总结：
{summary[:3000]}

段落名称：{section_title}
段落提示：{section_hint}
{persona_context}{mcp_needed_context}

要求：
1. 生成 3 个版本，各有不同的切入角度和写作思路
2. 每个版本 3-5 句话，说明该段落写什么、怎么写、可用素材
3. 每个版本标注其风格特点（如"技术背景切入"、"行业现状切入"、"用户痛点切入"等）
4. 返回 JSON 格式（不要 markdown 代码块）：
{{
  "versions": [
    {{"style": "技术背景切入", "outline": "写作提纲：该段落应该写...从...角度切入...可用素材..."}},
    {{"style": "行业现状切入", "outline": "..."}},
    {{"style": "用户痛点切入", "outline": "..."}}
  ]
}}

请直接返回 JSON：
"""
        
        import httpx
        async with httpx.AsyncClient(timeout=llm_config.get("timeout", 60)) as client:
            response = await client.post(
                f"{llm_config.get('base_url', 'https://api.deepseek.com/v1')}/chat/completions",
                headers={"Authorization": f"Bearer {llm_config.get('api_key', '')}"},
                json={
                    "model": llm_config.get("model", "deepseek-chat"),
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2048,
                    "temperature": 0.5,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()
        
        content = result["choices"][0]["message"]["content"].strip()
        content = content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        parsed = json_mod.loads(content)
        versions = parsed.get("versions", [])
        
        return _success({
            "section_key": section_key,
            "section_title": section_title,
            "versions": versions,
        })
        
    except Exception as e:
        logger.warning(f"LLM 提纲版本生成失败: {e}")
        return _error(msg=str(e))


@router.post("/api/content/check_direction")
async def check_direction_alignment(request: Dict = Body(...)):
    """
    方向性检测：检测生成内容是否符合提纲要求。
    
    请求体：
    {
        "section_title": "技术架构解析",
        "section_outline": "写作提纲：从整体架构角度拆解...",
        "generated_content": "AI 生成的段落内容"
    }
    """
    section_title = request.get("section_title", "")
    section_outline = request.get("section_outline", "")
    generated_content = request.get("generated_content", "")
    
    if not section_outline or not generated_content:
        return _error(code=400, msg="缺少 section_outline 或 generated_content 参数")
    
    try:
        llm_config = _get_config("llm")
        
        prompt = f"""请检测以下内容是否覆盖了提纲要求的要点：

【提纲要点】
{section_outline}

【生成内容】
{generated_content[:3000]}

请从以下维度检测：
1. 主题是否偏离？（提纲要求X，内容在讲Y）
2. 重点是否偏移？（提纲要求重点讲A，内容在讲B）
3. 素材是否缺失？（提纲要求具体案例，内容全是理论）
4. 语气是否符合身份？（专业、通俗、学术等）

返回 JSON 格式（不要 markdown 代码块）：
{{
  "coverage": {{
    "要点1": true,
    "要点2": false,
    ...
  }},
  "coverage_rate": 0.67,
  "severity": "medium",
  "issues": ["缺少具体案例", "偏理论描述"],
  "suggestion": "建议重写，重点补充..."
}}

其中 severity 分级：
- "none": coverage_rate >= 0.8，方向正确
- "minor": 0.6 <= coverage_rate < 0.8，建议检查
- "medium": 0.4 <= coverage_rate < 0.6，可能需要调整
- "severe": coverage_rate < 0.4，方向偏离

请直接返回 JSON：
"""
        
        import httpx
        async with httpx.AsyncClient(timeout=llm_config.get("timeout", 60)) as client:
            response = await client.post(
                f"{llm_config.get('base_url', 'https://api.deepseek.com/v1')}/chat/completions",
                headers={"Authorization": f"Bearer {llm_config.get('api_key', '')}"},
                json={
                    "model": llm_config.get("model", "deepseek-chat"),
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                    "temperature": 0,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()
        
        content = result["choices"][0]["message"]["content"].strip()
        content = content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        parsed = json_mod.loads(content)
        
        severity_labels = {
            "none": "✅ 方向正确",
            "minor": "⚠️ 建议检查",
            "medium": "⚠️ 可能需要调整",
            "severe": "❌ 方向偏离",
        }
        severity_colors = {
            "none": "green",
            "minor": "orange",
            "medium": "orangered",
            "severe": "red",
        }
        
        return _success({
            "section_title": section_title,
            "coverage": parsed.get("coverage", {}),
            "coverage_rate": parsed.get("coverage_rate", 0),
            "severity": parsed.get("severity", "none"),
            "severity_label": severity_labels.get(parsed.get("severity", "none"), "⚠️ 建议检查"),
            "severity_color": severity_colors.get(parsed.get("severity", "none"), "orange"),
            "issues": parsed.get("issues", []),
            "suggestion": parsed.get("suggestion", ""),
        })
        
    except Exception as e:
        logger.warning(f"方向性检测失败: {e}")
        return _error(msg=str(e))


@router.post("/api/content/ai_generate")
async def ai_generate_section(request: Dict = Body(...)):
    """
    AI 辅助生成单个段落内容。
    
    请求体：
    {
        "direction_name": "技术深度分析",
        "section_title": "技术架构解析",
        "section_hint": "从整体架构角度拆解...",
        "section_outline": "写作提纲：该段落应该写...",
        "analysis_type": "use_original|supplement|add_new",
        "analysis_suggestion": "建议补充具体案例",
        "topic_needed": "MCP分析建议补充的内容",
        "source_text": "MCP 总结全文",
        "existing_sections": {"intro": "...", "section_0": "..."}
    }
    """
    direction_name = request.get("direction_name", "")
    section_title = request.get("section_title", "")
    section_hint = request.get("section_hint", "")
    section_outline = request.get("section_outline", "")  # 新增：段落提纲
    analysis_type = request.get("analysis_type", "add_new")  # 新增：原文充足性
    analysis_suggestion = request.get("analysis_suggestion", "")  # 新增：分析建议
    topic_needed = request.get("topic_needed", "")  # 新增：MCP建议补充
    source_text = request.get("source_text", "")
    existing_sections = request.get("existing_sections", {})
    
    if not direction_name or not section_title:
        return _error(code=400, msg="缺少 direction_name 或 section_title 参数")
    
    try:
        llm_config = _get_config("llm")
        headers = {
            "Authorization": f"Bearer {llm_config.get('api_key', '')}",
            "Content-Type": "application/json",
        }
        
        existing_context = ""
        if existing_sections:
            existing_parts = []
            for key, val in existing_sections.items():
                if val and val.strip():
                    existing_parts.append(f"[{key}]: {val[:500]}")
            if existing_parts:
                existing_context = "\n\n已撰写的其他段落：\n" + "\n\n".join(existing_parts)
        
        source_context = f"\n\n参考资料（MCP 检索总结）：\n{source_text[:5000]}" if source_text else ""
        
        # 知识库自学习：合并已确认的补充内容到上下文
        session_id = request.get("session_id", "")
        if session_id:
            try:
                supp_storage = get_supplement_storage(session_id)
                source_text_for_llm = supp_storage.merge_to_mcp(source_text[:5000])
                source_context = f"\n\n参考资料（MCP 检索总结 + 用户补充）：\n{source_text_for_llm}" if source_text_for_llm else ""
            except Exception as e:
                logger.warning(f"合并补充内容失败: {e}")
        
        # 获取身份定位文件内容（如果存在）
        persona_content = _get_persona_summary()
        persona_context = f"\n\n作者身份定位：\n{persona_content}" if persona_content else ""
        
        # 构建原文充足性指导
        analysis_guidance = ""
        if analysis_type == "use_original":
            analysis_guidance = f"""
【原文充足性指导】
原文内容充足，请优先基于参考资料撰写，适当引用原文信息。
"""
        elif analysis_type == "supplement":
            analysis_guidance = f"""
【原文充足性指导】
原文有部分相关内容，请结合参考资料和逻辑推演撰写。
需要补充：{analysis_suggestion}
"""
        else:  # add_new
            analysis_guidance = f"""
【原文充足性指导】
原文缺少该部分内容，请基于逻辑推演、行业知识或外部知识撰写。
建议方向：{analysis_suggestion}
"""
        
        # 构建MCP建议
        mcp_guidance = ""
        if topic_needed:
            mcp_guidance = f"""
【MCP 分析建议补充】
{topic_needed}
如果本段落需要补充上述内容，请在撰写时体现。
"""
        
        # 构建提纲指导
        outline_guidance = ""
        if section_outline:
            outline_guidance = f"""
【本段写作提纲】
{section_outline}
请严格按照上述提纲撰写，确保内容方向与提纲一致。
"""
        
        # P0 融合方案：缺失感知 + 降级模式 + 置信度标注
        mcp_summary = source_text[:5000] if source_text else ""
        missing_items = request.get("missing_items", [])
        
        # 完整性评估（completeness_checker已移除，使用安全兜底）
        completeness_score = 100 if not missing_items else max(0, 100 - len(missing_items) * 10)
        completeness_mode = "full" if completeness_score >= 80 else ("partial" if completeness_score >= 50 else "fallback")
        completeness_mode_label = "🟢 知识库充足" if completeness_score >= 80 else ("🟡 部分缺失" if completeness_score >= 50 else " 严重缺失")
        mode_instructions = (
            "模式：正常生成，充分利用知识库" if completeness_score >= 80 else
            "模式：部分维度有缺失，请尽量基于已有信息推断，缺失维度可合理补充" if completeness_score >= 50 else
            "模式：知识库严重不足，请输出结构化框架，不要编造案例数据"
        )
        confidence_instructions = (
            "对基于已有信息的段落不额外标注，对推断部分标注 [AI推断]"
        )
        
        prompt = f"""你是一个专业的{direction_name.replace("分析", "分析师")}。请撰写"{section_title}"这一段落的内容。
{outline_guidance}{analysis_guidance}{mcp_guidance}
【基础写作要求】
{section_hint}
{existing_context}{source_context}{persona_context}

【知识库完整性判定】
完整性评分：{completeness_score}%
当前模式：{completeness_mode_label}

【生成模式指令】
{mode_instructions}

【置信度标注要求】
{confidence_instructions}

【补充知识库使用要求】
⚠️ 重要：如果"参考资料"中包含【用户补充的知识库】部分，你必须：
1. 仔细阅读补充的知识内容（案例、数据、画像等）
2. 在撰写正文时，优先引用和融入这些补充内容
3. 补充内容应作为论据支撑你的观点，而非简单罗列
4. 引用补充案例时，保持案例的核心信息（公司名、数据、效果）不变
5. 如果补充知识库为空，则基于 MCP 原始摘要撰写

【内容比例要求】
- 理论内容≤20%，实战内容≥80%
- 理论：概念解释、背景介绍、原理说明（简短精炼）
- 实战：操作步骤、具体案例、避坑指南、收益测算、工具推荐

【素材来源标注要求】（P0 渐进实施阶段）
- 如果内容基于参考资料/MCP 摘要，在段落末尾标注 [来源：xxx]
- 如果内容基于逻辑推演/行业知识，在段落开头标注 ⚠️ [AI 推断]
- 如果内容来自用户手动补充，在段落末尾标注 [来源：用户补充]

【底线原则】
严禁编造案例细节或用户数据。如果信息极度匮乏，输出一个待填充的结构化框架优于输出一篇空洞的文章。

要求：
1. 严格按照【本段写作提纲】撰写（如果有）
2. 根据【原文充足性指导】决定原文使用程度
3. 如果【MCP 分析建议补充】提到需要补充某内容，请在本段体现
4. 内容专业、准确，有逻辑性
5. 适当引用参考资料中的信息（特别是补充知识库中的案例和数据）
6. 使用 Markdown 格式
7. 语言风格要符合作者的身份定位
8. 不要编造参考资料中没有的内容（原文充足时）
9. 如果案例/素材不足，使用【案例占位符】格式标注：[📌 待补充案例：xxx 类型的实际案例]
10. 每个结论标注置信等级（✅/⚠️/❓）
11. 直接输出该段落的内容，不要输出"好的"、"以下是"等多余话语

请撰写该段落内容：
"""
        
        import httpx
        async with httpx.AsyncClient(timeout=llm_config.get("timeout", 60)) as client:
            response = await client.post(
                f"{llm_config.get('base_url', 'https://api.deepseek.com/v1')}/chat/completions",
                headers=headers,
                json={
                    "model": llm_config.get("model", "deepseek-chat"),
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2048,
                    "temperature": 0.3,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()
        
        content = result["choices"][0]["message"]["content"].strip()
        
        # P2: source_tag 处理
        processor = get_source_tag_processor()
        processed = processor.process_content(content, strict_mode=False)  # P2 阶段先用宽松模式
        
        return _success({
            "content": content,
            "rendered_content": processed.rendered_content,
            "source_tag": processed.source_tag,
            "is_valid": processed.is_valid,
            "warning": processed.warning,
            # P0 融合方案：返回完整性信息
            "completeness": {
                "score": completeness.score,
                "mode": completeness.mode,
                "mode_label": completeness.mode_label,
                "missing_dimensions": completeness.missing_dimensions,
                "suggestions": completeness.suggestions,
            },
        })
        
    except Exception as e:
        logger.error(f"AI 段落生成失败: {e}")
        return _error(msg=str(e))


@router.post("/api/content/ai_rewrite")
async def ai_rewrite_section(request: Dict = Body(...)):
    """
    AI 重写单个段落内容（支持用户补充指令）。
    
    请求体：
    {
        "direction_name": "技术深度分析",
        "section_title": "技术架构解析",
        "section_outline": "写作提纲：该段落应该写...",
        "user_feedback": "不要讲太多理论，重点描述数据是怎么在各个模块之间流动的",
        "source_text": "MCP 总结全文",
        "existing_sections": {"intro": "...", "section_0": "..."}
    }
    """
    direction_name = request.get("direction_name", "")
    section_title = request.get("section_title", "")
    section_outline = request.get("section_outline", "")
    user_feedback = request.get("user_feedback", "")
    source_text = request.get("source_text", "")
    existing_sections = request.get("existing_sections", {})
    
    if not direction_name or not section_title:
        return _error(code=400, msg="缺少 direction_name 或 section_title 参数")
    if not section_outline:
        return _error(code=400, msg="缺少 section_outline 参数")
    
    try:
        llm_config = _get_config("llm")
        headers = {
            "Authorization": f"Bearer {llm_config.get('api_key', '')}",
            "Content-Type": "application/json",
        }
        
        existing_context = ""
        if existing_sections:
            existing_parts = []
            for key, val in existing_sections.items():
                if val and val.strip():
                    existing_parts.append(f"[{key}]: {val[:500]}")
            if existing_parts:
                existing_context = "\n\n已撰写的其他段落：\n" + "\n\n".join(existing_parts)
        
        source_context = f"\n\n参考资料（MCP 检索总结）：\n{source_text[:5000]}" if source_text else ""
        
        persona_content = _get_persona_summary()
        persona_context = f"\n\n作者身份定位：\n{persona_content}" if persona_content else ""
        
        user_feedback_context = ""
        if user_feedback:
            user_feedback_context = f"""
【用户补充指令（优先级最高）】
{user_feedback}

注意：用户补充指令的优先级高于原提纲，如果两者有冲突，以用户指令为准。
"""
        
        prompt = f"""你是一个专业的{direction_name.replace("分析", "分析师")}。请重写"{section_title}"这一段落的内容。

【原提纲】
{section_outline}
{user_feedback_context}

【基础写作要求】
{existing_context}{source_context}{persona_context}

要求：
1. 严格按照【原提纲】撰写
2. 如果有【用户补充指令】，优先级最高，按用户指令调整方向
3. 内容专业、准确，有逻辑性
4. 适当引用参考资料中的信息
5. 使用 Markdown 格式
6. 语言风格要符合作者的身份定位
7. 直接输出该段落的内容，不要输出"好的"、"以下是"等多余话语

请重写该段落内容：
"""
        
        import httpx
        async with httpx.AsyncClient(timeout=llm_config.get("timeout", 60)) as client:
            response = await client.post(
                f"{llm_config.get('base_url', 'https://api.deepseek.com/v1')}/chat/completions",
                headers=headers,
                json={
                    "model": llm_config.get("model", "deepseek-chat"),
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2048,
                    "temperature": 0.3,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()
        
        content = result["choices"][0]["message"]["content"].strip()
        
        # P2: source_tag 处理
        processor = get_source_tag_processor()
        processed = processor.process_content(content, strict_mode=False)
        
        return _success({
            "content": content,
            "rendered_content": processed.rendered_content,
            "source_tag": processed.source_tag,
            "is_valid": processed.is_valid,
            "warning": processed.warning,
        })
        
    except Exception as e:
        logger.error(f"AI 重写失败: {e}")
        return _error(msg=str(e))


@router.post("/api/content/ai_generate_full")
async def ai_generate_full_content(request: Dict = Body(...)):
    """
    AI 一键生成全文所有段落。
    
    请求体：
    {
        "direction_name": "技术深度分析",
        "structure": {"intro": {...}, "sections": [...], "conclusion": {...}},
        "source_text": "MCP 总结全文"
    }
    """
    direction_name = request.get("direction_name", "")
    structure = request.get("structure", {})
    source_text = request.get("source_text", "")
    
    if not direction_name or not structure:
        return _error(code=400, msg="缺少 direction_name 或 structure 参数")
    
    try:
        llm_config = _get_config("llm")
        headers = {
            "Authorization": f"Bearer {llm_config.get('api_key', '')}",
            "Content-Type": "application/json",
        }
        
        source_context = f"\n\n参考资料（MCP 检索总结）：\n{source_text[:5000]}" if source_text else ""
        
        # 知识库自学习：合并已确认的补充内容到上下文
        session_id = request.get("session_id", "")
        if session_id:
            try:
                supp_storage = get_supplement_storage(session_id)
                source_text_for_llm = supp_storage.merge_to_mcp(source_text[:5000])
                source_context = f"\n\n参考资料（MCP 检索总结 + 用户补充）：\n{source_text_for_llm}" if source_text_for_llm else ""
            except Exception as e:
                logger.warning(f"合并补充内容失败: {e}")
        
        # 获取身份定位文件内容（如果存在）
        persona_content = _get_persona_summary()
        persona_context = f"\n\n作者身份定位：\n{persona_content}" if persona_content else ""
        
        # 构建全文大纲
        outline = f"方向：{direction_name}\n\n"
        if structure.get("intro"):
            outline += f"## {structure['intro']['title']}\n{structure['intro']['hint']}\n\n"
        for i, sec in enumerate(structure.get("sections", [])):
            outline += f"## {sec['title']}\n{sec['hint']}\n\n"
        if structure.get("conclusion"):
            outline += f"## {structure['conclusion']['title']}\n{structure['conclusion']['hint']}\n\n"
        
        prompt = f"""你是一个专业的分析师。请根据以下大纲和参考资料，撰写一篇完整的{direction_name}文章。

文章大纲：
{outline}
{source_context}
{persona_context}

【内容比例要求】
- 理论内容≤20%，实战内容≥80%
- 理论：概念解释、背景介绍、原理说明（简短精炼）
- 实战：操作步骤、具体案例、避坑指南、收益测算、工具推荐

【素材来源标注要求】（P0 渐进实施阶段）
- 如果内容基于参考资料/MCP 摘要，在段落末尾标注 [来源：xxx]
- 如果内容基于逻辑推演/行业知识，在段落开头标注 ⚠️ [AI 推断]
- 如果案例/素材不足，使用【案例占位符】格式：[📌 待补充案例：xxx 类型的实际案例]

要求：
1. 按照大纲顺序，逐个段落撰写
2. 每个段落以"## 标题"开头
3. 内容专业、准确，有逻辑性
4. 适当引用参考资料中的信息
5. 使用 Markdown 格式
6. 语言风格要符合作者的身份定位
7. 不要编造参考资料中没有的内容
8. 直接输出完整文章，不要输出多余的开场白

请撰写全文：
"""
        
        import httpx
        async with httpx.AsyncClient(timeout=llm_config.get("timeout", 120)) as client:
            response = await client.post(
                f"{llm_config.get('base_url', 'https://api.deepseek.com/v1')}/chat/completions",
                headers=headers,
                json={
                    "model": llm_config.get("model", "deepseek-chat"),
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 8192,
                    "temperature": 0.3,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()
        
        full_content = result["choices"][0]["message"]["content"].strip()
        
        # P2: source_tag 处理（全文按段落分割处理）
        processor = get_source_tag_processor()
        processed = processor.process_full_article(full_content, strict_mode=False)
        
        return _success({
            "content": full_content,
            "rendered_html": processed["rendered_html"],
            "valid_count": processed["valid_count"],
            "filtered_count": processed["filtered_count"],
            "source_tags": processed["source_tags"],
            "blocks": [
                {
                    "source_tag": b.source_tag,
                    "is_valid": b.is_valid,
                    "warning": b.warning,
                    "rendered_content": b.rendered_content,
                }
                for b in processed["blocks"]
            ],
        })
        
    except Exception as e:
        logger.error(f"AI 全文生成失败: {e}")
        return _error(msg=str(e))


@router.post("/api/content/smart_fill")
async def smart_fill_content(request: Dict = Body(...)):
    """
    智能补全：根据分析结果，自动补全全文
    - 原文充足：直接使用原文
    - 原文不足：调用 AI 生成
    
    请求体：
    {
        "direction_name": "技术深度分析",
        "structure": {"intro": {...}, "sections": [...], "conclusion": {...}},
        "source_text": "MCP 总结全文",
        "analysis": {"intro": {"type": "use_original|supplement|add_new"}, ...}
    }
    """
    direction_name = request.get("direction_name", "")
    structure = request.get("structure", {})
    source_text = request.get("source_text", "")
    analysis = request.get("analysis", {})
    
    if not direction_name or not structure:
        return _error(code=400, msg="缺少 direction_name 或 structure 参数")
    
    llm_config = _get_config("llm")
    headers = {
        "Authorization": f"Bearer {llm_config.get('api_key', '')}",
        "Content-Type": "application/json",
    }
    
    source_context = f"\n\n参考资料（MCP 检索总结）：\n{source_text[:5000]}" if source_text else ""
    
    # 获取身份定位文件内容（如果存在）
    persona_content = _get_persona_summary()
    persona_context = f"\n\n作者身份定位：\n{persona_content}" if persona_content else ""
    
    result_sections = {}
    sections_to_fill = []
    
    # 收集所有段落信息
    if structure.get("intro"):
        sections_to_fill.append({"key": "intro", "title": structure["intro"]["title"], "hint": structure["intro"]["hint"]})
    for i, sec in enumerate(structure.get("sections", [])):
        sections_to_fill.append({"key": f"section_{i}", "title": sec["title"], "hint": sec["hint"], "pre_filled_content": sec.get("pre_filled_content", "")})
    if structure.get("conclusion"):
        sections_to_fill.append({"key": "conclusion", "title": structure["conclusion"]["title"], "hint": structure["conclusion"]["hint"]})
    
    # 处理每个段落
    for sec_info in sections_to_fill:
        key = sec_info["key"]
        analysis_info = analysis.get(key, {})
        analysis_type = analysis_info.get("type", "add_new")
        # 获取预填充内容
        if key == "intro":
            pre_filled = structure.get("intro", {}).get("pre_filled_content", "")
        elif key == "conclusion":
            pre_filled = structure.get("conclusion", {}).get("pre_filled_content", "")
        else:
            pre_filled = sec_info.get("pre_filled_content", "")
        
        if analysis_type == "use_original" and pre_filled:
            # 原文充足，直接使用
            result_sections[key] = {
                "content": pre_filled,
                "source": "original"
            }
        else:
            # 需要 AI 生成（supplement 或 add_new）
            existing_context = ""
            existing_parts = []
            for k, v in result_sections.items():
                if v.get("content") and v["content"].strip():
                    existing_parts.append(f"[{k}]: {v['content'][:500]}")
            if existing_parts:
                existing_context = "\n\n已撰写的其他段落：\n" + "\n\n".join(existing_parts)
            
            prompt = f"""你是一个专业的{direction_name.replace('分析', '分析师')}。请根据以下要求，撰写"{sec_info['title']}"这一段落的内容。

写作要求：
{sec_info['hint']}
{existing_context}
{source_context}
{persona_context}

要求：
1. 内容专业、准确，有逻辑性
2. 适当引用参考资料中的信息
3. 使用 Markdown 格式
4. 语言风格要符合作者的身份定位
5. 不要编造参考资料中没有的内容
6. 直接输出该段落的内容，不要输出"好的"、"以下是"等多余话语

请撰写该段落内容：
"""
            
            try:
                import httpx
                async with httpx.AsyncClient(timeout=llm_config.get("timeout", 60)) as client:
                    response = await client.post(
                        f"{llm_config.get('base_url', 'https://api.deepseek.com/v1')}/chat/completions",
                        headers=headers,
                        json={
                            "model": llm_config.get("model", "deepseek-chat"),
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": 2048,
                            "temperature": 0.3,
                            "seed": 42,
                        },
                    )
                    response.raise_for_status()
                    result = response.json()
                
                content = result["choices"][0]["message"]["content"].strip()
                content = content.replace("```markdown", "").replace("```", "").strip()
                # Remove heading if AI outputted it
                import re
                content = re.sub(r'^##\s+.+\n+', '', content, flags=re.MULTILINE)
                
                result_sections[key] = {
                    "content": content,
                    "source": "ai"
                }
            except Exception as e:
                logger.warning(f"AI 生成段落 {key} 失败: {e}")
                # 回退：使用预填充内容
                result_sections[key] = {
                    "content": pre_filled,
                    "source": "fallback"
                }
    
    # 构建返回结果
    final_contents = {}
    for key, sec_result in result_sections.items():
        final_contents[key] = sec_result["content"]
    
    return _success({
        "sections": final_contents,
        "total": len(final_contents),
        "ai_generated": len([v for v in result_sections.values() if v["source"] == "ai"]),
        "original_used": len([v for v in result_sections.values() if v["source"] == "original"]),
    })


# ===== 身份定位管理 =====

_persona_file_path = None

def _get_persona_path():
    """获取身份定位文件路径"""
    global _persona_file_path
    if _persona_file_path:
        return _persona_file_path
    # 默认路径
    default_path = Path(__file__).parent / "data" / "persona.md"
    return str(default_path)

def _get_persona_content():
    """获取身份定位文件原始内容（如果存在）"""
    try:
        file_path = _get_persona_path()
        if Path(file_path).exists():
            return Path(file_path).read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"读取身份定位文件失败: {e}")
    return ""

_persona_parsed_cache = {}

def _get_persona_parsed():
    """获取身份定位文件的解析结果（带缓存）"""
    current_content = ""
    try:
        file_path = _get_persona_path()
        if Path(file_path).exists():
            current_content = Path(file_path).read_text(encoding="utf-8")
    except Exception:
        pass
    
    if _persona_parsed_cache.get("content") == current_content:
        return _persona_parsed_cache.get("parsed")
    return None

def _get_persona_summary():
    """获取身份定位的摘要，用于传给 LLM（优先使用六维模型摘要）"""
    parsed = _get_persona_parsed()
    if parsed:
        # 优先使用六维模型的整体描述
        if parsed.get("summary"):
            return parsed["summary"]
        
        # 兼容旧格式
        if parsed.get("who_am_i"):
            return f"作者身份：{parsed['who_am_i']}，目标读者：{parsed.get('target_audience', '')}，专业领域：{parsed.get('expertise', '')}，写作风格：{parsed.get('style', '')}"
    
    # 回退：使用原始内容的前 500 字
    raw = _get_persona_content()
    return raw[:500] if raw else ""

@router.post("/api/persona/parse")
async def parse_persona(request: Dict = Body(default={})):
    """
    解析身份定位文件，提取六维结构化信息（AI推理）
    使用 LLM 将非结构化身份文件解析为六维动态行为模型
    """
    # 优先使用传入的路径，如果没有则使用配置中的路径
    content = ""
    file_path = request.get("file_path", "")
    if file_path:
        try:
            from pathlib import Path as PathLib
            if PathLib(file_path).exists():
                content = PathLib(file_path).read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"读取身份定位文件失败: {e}")
    
    if not content:
        content = _get_persona_content()
    
    if not content:
        return _error(code=400, msg="未设置身份定位文件")
    
    # 复杂度检测：文件内容是否过于简单
    complexity_warning = ""
    word_count = len(content.strip())
    if word_count < 300:
        complexity_warning = "注意：该文件内容较少，可能缺少完整的身份定位信息。建议补充更多细节（如核心驱动、思维框架、表达规范等）。"
    elif word_count < 600:
        complexity_warning = "提示：该文件内容较简洁，建议适当补充细节以提升AI理解准确度。"
    
    # 加载六维配置模板
    dimensions_template = ""
    try:
        from pathlib import Path as PathLib
        dim_path = PathLib(__file__).parent / "config" / "persona_dimensions.md"
        if dim_path.exists():
            dimensions_template = dim_path.read_text(encoding="utf-8")
    except Exception:
        pass
    
    try:
        llm_config = _get_config("llm")
        base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
        api_key = llm_config.get("api_key", "")
        model = llm_config.get("model", "deepseek-chat")
        timeout = llm_config.get("timeout", 60)
        
        prompt = f"""你是一个专业的角色建模专家。请分析以下身份定位文件，提取作者的六维动态行为模型。

【原始内容】
{content}

【六维框架参考】
{dimensions_template}

请基于原始内容，推理提取以下六维信息。如果没有明确提到，请根据上下文合理推断：

1. 核心驱动 (Why): 作者创作的源动力是什么？想解决什么问题？
2. 认知过滤 (Filter): 作者的思维方式有什么独特之处？习惯用什么结构？
3. 受众画像 (Who): 目标读者是谁？他们有什么痛点？如何与他们共情？
4. 能力边界 (Edge): 作者擅长什么？不擅长什么？回避哪些话题？
5. 表达范式 (Voice): 语言风格、结构偏好、比例要求、禁用词
6. 价值标准 (Value): 什么内容是有价值的？如何取舍？

返回 JSON 格式（不要 markdown 代码块）：
{{
  "why": "核心驱动（一句话，说明源动力）",
  "filter": "认知过滤（思维模式，如'问题→方案→避坑→收益'）",
  "who": {{
    "profile": "受众画像（身份特征）",
    "pain_points": ["痛点1", "痛点2", ...],
    "empathy_phrases": ["共情话术1", "共情话术2", ...]
  }},
  "edge": {{
    "focus": "专注领域（擅长什么）",
    "avoid": "回避话题（不写什么）"
  }},
  "voice": {{
    "tone": "语气风格",
    "structure": "结构偏好",
    "ratio": "内容比例要求",
    "forbidden": "禁用/避免的表达"
  }},
  "value": {{
    "gold_standard": "金标准（一句话）",
    "checklist": ["检查项1", "检查项2", ...]
  }},
  "summary": "身份定位的整体描述（200字内），用于作为文章作者身份背景传给LLM",
  "raw_summary": "原文关键内容摘要（保留原文表述）",
  "complexity_note": "{complexity_warning if complexity_warning else ''}"
}}

注意：
- 所有维度都要基于原文推理，不要编造
- 如果原文信息不足，可以从上下文合理推断，但要标注推断内容
- "summary" 是最重要的字段，将直接传给内容生成LLM
- 每个维度用简洁语言描述，避免冗长

请直接返回 JSON：
"""
        
        import httpx
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2048,
                    "temperature": 0,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()
        
        parsed_content = result["choices"][0]["message"]["content"].strip()
        parsed_content = parsed_content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        parsed = json_mod.loads(parsed_content)
        
        # 缓存解析结果
        _persona_parsed_cache["content"] = content
        _persona_parsed_cache["parsed"] = parsed
        
        return _success({
            "raw": content,
            "parsed": parsed,
            "complexity_warning": complexity_warning,
        })
        
    except Exception as e:
        logger.warning(f"LLM 身份解析失败: {e}")
        return _error(msg=str(e))


async def _parse_persona_sync(content: str):
    """同步解析身份定位内容，返回六维结构化信息"""
    try:
        llm_config = _get_config("llm")
        base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
        api_key = llm_config.get("api_key", "")
        model = llm_config.get("model", "deepseek-chat")
        timeout = llm_config.get("timeout", 60)
        
        # 加载六维配置模板
        dimensions_template = ""
        try:
            from pathlib import Path as PathLib
            dim_path = PathLib(__file__).parent / "config" / "persona_dimensions.md"
            if dim_path.exists():
                dimensions_template = dim_path.read_text(encoding="utf-8")
        except Exception:
            pass
        
        # 复杂度检测
        complexity_note = ""
        word_count = len(content.strip())
        if word_count < 300:
            complexity_note = "注意：该文件内容较少，可能缺少完整的身份定位信息。建议补充更多细节。"
        elif word_count < 600:
            complexity_note = "提示：该文件内容较简洁，建议适当补充细节以提升AI理解准确度。"
        
        prompt = f"""你是一个专业的角色建模专家。请分析以下身份定位文件，提取作者的六维动态行为模型。

【原始内容】
{content}

【六维框架参考】
{dimensions_template}

请基于原始内容，推理提取以下六维信息。如果没有明确提到，请根据上下文合理推断：

1. 核心驱动 (Why): 作者创作的源动力是什么？想解决什么问题？
2. 认知过滤 (Filter): 作者的思维方式有什么独特之处？习惯用什么结构？
3. 受众画像 (Who): 目标读者是谁？他们有什么痛点？如何与他们共情？
4. 能力边界 (Edge): 作者擅长什么？不擅长什么？回避哪些话题？
5. 表达范式 (Voice): 语言风格、结构偏好、比例要求、禁用词
6. 价值标准 (Value): 什么内容是有价值的？如何取舍？

返回 JSON 格式（不要 markdown 代码块）：
{{
  "why": "核心驱动（一句话，说明源动力）",
  "filter": "认知过滤（思维模式，如'问题→方案→避坑→收益'）",
  "who": {{
    "profile": "受众画像（身份特征）",
    "pain_points": ["痛点1", "痛点2"],
    "empathy_phrases": ["共情话术1", "共情话术2"]
  }},
  "edge": {{
    "focus": "专注领域（擅长什么）",
    "avoid": "回避话题（不写什么）"
  }},
  "voice": {{
    "tone": "语气风格",
    "structure": "结构偏好",
    "ratio": "内容比例要求",
    "forbidden": "禁用/避免的表达"
  }},
  "value": {{
    "gold_standard": "金标准（一句话）",
    "checklist": ["检查项1", "检查项2"]
  }},
  "summary": "身份定位的整体描述（200字内），用于作为文章作者身份背景传给LLM",
  "raw_summary": "原文关键内容摘要（保留原文表述）",
  "complexity_note": "{complexity_note}"
}}

注意：
- 所有维度都要基于原文推理，不要编造
- 如果原文信息不足，可以从上下文合理推断
- "summary" 是最重要的字段，将直接传给内容生成LLM
- 每个维度用简洁语言描述，避免冗长

请直接返回 JSON：
"""
        
        import httpx
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2048,
                    "temperature": 0,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()
        
        parsed_content = result["choices"][0]["message"]["content"].strip()
        parsed_content = parsed_content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        parsed = json_mod.loads(parsed_content)
        
        _persona_parsed_cache["content"] = content
        _persona_parsed_cache["parsed"] = parsed
        return parsed
    except Exception as e:
        logger.error(f"身份定位解析失败: {e}")
        return None


@router.get("/api/persona/info")
async def get_persona_info():
    """获取身份定位信息：文件路径 + 内容 + 解析后的结构化信息（六维模型）"""
    file_path = _get_persona_path()
    content = ""
    exists = False
    parsed = None
    try:
        if Path(file_path).exists():
            content = Path(file_path).read_text(encoding="utf-8")
            exists = True
            # 优先使用缓存的六维解析结果
            parsed = _get_persona_parsed()
            if not parsed and content:
                # 如果没有缓存，使用 LLM 解析六维模型
                parsed = await _parse_persona_sync(content)
    except Exception as e:
        logger.warning(f"读取身份定位文件失败: {e}")
    
    return _success({
        "file_path": file_path,
        "content": content,
        "exists": exists,
        "parsed": parsed,
    })

@router.post("/api/persona/set_path")
async def set_persona_path(request: Dict = Body(...)):
    """设置身份定位文件路径"""
    global _persona_file_path
    file_path = request.get("file_path", "")
    if not file_path:
        return _error(code=400, msg="缺少 file_path 参数")
    
    if not Path(file_path).exists():
        return _error(code=400, msg="文件不存在")
    
    _persona_file_path = file_path
    return _success({"file_path": file_path})

@router.post("/api/persona/save")
async def save_persona(request: Dict = Body(...)):
    """保存身份定位内容到文件"""
    content = request.get("content", "")
    file_path = _get_persona_path()
    
    try:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        Path(file_path).write_text(content, encoding="utf-8")
        return _success({"file_path": file_path})
    except Exception as e:
        return _error(msg=f"保存失败: {e}")


# ===== MCP 检索接口 =====

@router.post("/api/mcp/search")
async def mcp_search(request: Dict = Body(...)):
    """
    MCP 检索：扫描 → 过滤 → 读取 → LLM 总结
    请求体：
    {
        "topic": "Agent",
        "folders": ["/home/admin/Desktop"]
    }
    """
    topic = request.get("topic", "")
    folders = request.get("folders", [])
    
    if not topic:
        return _error(code=400, msg="缺少 topic 参数")
    if not folders:
        return _error(code=400, msg="缺少 folders 参数")
        
    try:
        # Step 1: 扫描所有绑定的文件夹，检索匹配文件
        all_matched_files = []
        for folder_path in folders:
            try:
                reader = LocalFolderReader(folder_path)
                files = reader.list_files(keyword=topic, limit=10)
                for f in files:
                    f["folder_path"] = folder_path
                all_matched_files.extend(files)
            except Exception as e:
                logger.warning(f"扫描文件夹失败 {folder_path}: {e}")
                
        if not all_matched_files:
            return _success({
                "summary": f"未找到与「{topic}」相关的内容。请尝试其他关键词或添加更多文件夹。",
                "source_files": [],
                "file_count": 0,
                "summary_type": "no_result",
            })
            
        # 去重（按文件名）
        seen_names = set()
        unique_files = []
        for f in all_matched_files:
            if f["name"] not in seen_names:
                seen_names.add(f["name"])
                unique_files.append(f)
                
        source_files = [f["name"] for f in unique_files]
        logger.info(f"MCP 检索到 {len(unique_files)} 个文件: {source_files}")
        
        # Step 2: 读取全文（最多 5 个文件，控制 token 使用）
        max_files = 5
        target_files = unique_files[:max_files]
        target_paths = [f["path"] for f in target_files]
        
        reader = LocalFolderReader(target_files[0]["folder_path"])
        contents = reader.read_files(target_paths)
        
        # Step 3: 拼接上下文
        context_parts = []
        for c in contents:
            context_parts.append(f"## {c['name']}\n\n{c['content']}")
        context = "\n\n---\n\n".join(context_parts)
        
        # Step 4: 调用 LLM 总结
        llm_config = _get_config("llm")
        base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
        api_key = llm_config.get("api_key", "")
        model = llm_config.get("model", "deepseek-chat")
        timeout = llm_config.get("timeout", 30)
        
        import httpx
        
        prompt = f"""基于以下资料，整理一份关于「{topic}」的综合摘要：
{context}
要求：
1. 结构化输出（分点/分层级）
2. 引用原文时标注文件名
3. 不要编造资料中没有的内容
4. 使用 Markdown 格式
5. 语言简洁专业

同时，请分析如果要围绕「{topic}」写一篇文章，还需要补充什么内容（例如：具体案例、最新数据、专家观点等）。

返回 JSON 格式（不要 markdown 代码块）：
{{
    "summary": "综合摘要内容（Markdown 格式）",
    "topic_needed": "需要补充的内容（50字内，说明缺什么）"
}}

请直接返回 JSON：
"""
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4096,
                    "temperature": 0,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()
            
        content = result["choices"][0]["message"]["content"].strip()
        content = content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        parsed = json_mod.loads(content)
        
        summary = parsed.get("summary", content)  # 回退：如果解析失败，使用原始内容
        topic_needed = parsed.get("topic_needed", "建议补充更多具体案例和数据支撑")
        
        return _success({
            "summary": summary,
            "topic_needed": topic_needed,
            "source_files": source_files,
            "file_count": len(unique_files),
            "summary_type": "ok",
        })
        
    except Exception as e:
        logger.error(f"MCP 检索失败: {e}", exc_info=True)
        return _error(msg=str(e))


# ===== MCP 题材推荐接口 =====

def _classify_file(file_info: Dict) -> List[str]:
    """
    两层分类：基础分类 + LLM 语义分类
    
    第一层：读取 Front Matter 中的 category 字段（用户已标注）
    第二层：LLM 语义分类（对未标注文件进行推断）
    
    Returns:
        分类 key 列表，如 ["business", "product"]
    """
    categories = []
    
    # 第一层：基础分类（用户已标注）
    base_category = file_info.get("category", "")
    if base_category and base_category.lower() in _get_all_category_keys():
        categories.append(base_category.lower())
    
    # 第二层：LLM 语义分类（仅对未标注文件）
    if not categories:
        content = file_info.get("_full_content", file_info.get("preview", ""))[:1500]
        if content:
            llm_cats = _llm_classify_text(content)
            categories.extend(llm_cats)
    
    return categories


def _get_all_category_keys() -> List[str]:
    """获取所有分类 key"""
    try:
        from src.classifier import ContentClassifier
        cats = ContentClassifier({}).get_categories()
        return list(cats.keys())
    except Exception:
        return ["ai-models", "ai-products", "industry", "paper", "tip"]


_LLM_CLASSIFY_CACHE: Dict[str, List[str]] = {}

def _llm_classify_text(text: str) -> List[str]:
    """
    LLM 语义分类（带缓存）
    对文本进行语义理解，判断属于哪些业务领域
    """
    # 取前 1000 字作为分类依据
    content = text[:1000].strip()
    if not content:
        return []
    
    # 使用内容哈希作为缓存 key
    cache_key = hash(content)
    if cache_key in _LLM_CLASSIFY_CACHE:
        return _LLM_CLASSIFY_CACHE[cache_key]
    
    from src.classifier import ContentClassifier
    classifier = ContentClassifier(_get_config("llm"))
    result = classifier._classify_by_rules(content)
    
    primary = result.get("primary", "")
    alternatives = result.get("alternatives", [])
    
    cats = [primary] if primary else []
    cats.extend(alternatives[:2])
    
    # 缓存结果
    _LLM_CLASSIFY_CACHE[cache_key] = cats
    
    return cats


@router.post("/api/mcp/suggest")
async def mcp_topic_suggestion(request: Dict = Body(...)):
    """
    MCP 题材推荐：分析这批资料适合写什么题材
    请求体：
    {
        "topic": "Agent",           // 可选，空则自动推荐
        "folders": ["/home/..."],    // 必填
        "categories": ["business"],  // 可选，多选
        "time_range": "week",        // 可选：today, week, month, all
        "start_date": "2025-01-01",  // 可选，自定义日期
        "end_date": "2025-06-02"     // 可选
    }
    """
    topic = request.get("topic", "").strip()
    folders = request.get("folders", [])
    categories = request.get("categories", [])
    time_range = request.get("time_range", "all")
    start_date = request.get("start_date", "")
    end_date = request.get("end_date", "")
    
    if not folders:
        return _error(code=400, msg="缺少 folders 参数")
    
    try:
        from datetime import datetime, timedelta
        import time as _time
        
        # 计算时间范围
        if time_range == "today":
            start_ts = _time.mktime(datetime.now().replace(hour=0, minute=0, second=0).timetuple())
        elif time_range == "week":
            start_ts = _time.mktime((datetime.now() - timedelta(days=7)).timetuple())
        elif time_range == "month":
            start_ts = _time.mktime((datetime.now() - timedelta(days=30)).timetuple())
        elif start_date and end_date:
            start_ts = _time.mktime(datetime.strptime(start_date, "%Y-%m-%d").timetuple())
        else:
            start_ts = 0
        
        # 判断是否全空（无关键词、无分类、无时间筛选）
        is_empty_search = not topic and not categories and time_range == "all" and not start_date
        
        # 全空时：自动推荐（使用快速全量扫描）
        if is_empty_search:
            return await _auto_recommend_topics(folders)
        
        # 有筛选条件时：使用 list_files 扫描
        all_matched_files = []
        for folder_path in folders:
            try:
                reader = LocalFolderReader(folder_path)
                if topic:
                    files = reader.list_files(keyword=topic, limit=50)
                else:
                    files = reader.list_files(limit=50)
                
                # 按时间过滤
                if start_ts > 0:
                    files = [f for f in files if f.get("mtime", 0) >= start_ts]
                
                # 按分类过滤
                if categories:
                    filtered = []
                    for f in files:
                        file_cats = _classify_file(f)
                        if any(c in categories for c in file_cats):
                            filtered.append(f)
                    files = filtered
                
                for f in files:
                    f["folder_path"] = folder_path
                all_matched_files.extend(files)
            except Exception as e:
                logger.warning(f"扫描文件夹失败 {folder_path}: {e}")
        
        if not all_matched_files:
            return _success({
                "topics": [],
                "summary": f"未找到符合条件的内容。请调整筛选条件或输入关键词搜索。",
                "source_files": [],
                "file_count": 0,
            })
        
        # 去重（按相对路径，不同子目录下的同名文件不冲突）
        seen_paths = set()
        unique_files = []
        for f in all_matched_files:
            rel = f.get("relative_path", f["path"])
            if rel not in seen_paths:
                seen_paths.add(rel)
                unique_files.append(f)
        
        source_files = [f["name"] for f in unique_files]
        logger.info(f"MCP 题材分析扫描到 {len(unique_files)} 个文件")
        
        # 读取全文
        max_files = 5
        target_files = unique_files[:max_files]
        target_paths = [f["path"] for f in target_files]
        
        reader = LocalFolderReader(target_files[0]["folder_path"])
        contents = reader.read_files(target_paths)
        
        context_parts = []
        for c in contents:
            context_parts.append(f"## {c['name']}\n\n{c['content'][:1500]}")
        context = "\n\n---\n\n".join(context_parts)
        
        # 调用 LLM 分析题材
        llm_config = _get_config("llm")
        base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
        api_key = llm_config.get("api_key", "")
        model = llm_config.get("model", "deepseek-chat")
        timeout = llm_config.get("timeout", 60)
        
        persona_content = _get_persona_summary()
        persona_context = f"\n\n作者身份定位：\n{persona_content}" if persona_content else ""
        
        prompt = f"""你是一个专业的选题策划师。请分析以下资料，推荐 3-5 个值得写的文章题材。

资料列表：
{', '.join(source_files)}

资料内容摘要：
{context[:4000]}
{persona_context}

要求：
1. 分析这批资料涵盖的主题
2. 推荐 3-5 个写作方向，每个方向包含：
   - name: 方向名称（如"技术深度分析"）
   - description: 一句话描述写什么
   - coverage: 资料覆盖度 0-1（浮点数）
   - reason: 为什么值得写（50 字内）
   - needed: 需要补充什么
3. 返回 JSON 格式（不要 markdown 代码块）：
{{
    "topics": [
        {{"name": "...", "description": "...", "coverage": 0.8, "reason": "...", "needed": "..."}}
    ],
    "summary": "这批资料的整体情况（100字内）"
}}

请直接返回 JSON：
"""
        
        import httpx
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4096,
                    "temperature": 0,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()
        
        content = result["choices"][0]["message"]["content"].strip()
        content = content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        parsed = json_mod.loads(content)
        
        topics = parsed.get("topics", [])
        summary = parsed.get("summary", "")
        
        return _success({
            "topics": topics,
            "summary": summary,
            "source_files": source_files,
            "file_count": len(unique_files),
        })
        
    except Exception as e:
        logger.error(f"MCP 题材分析失败: {e}", exc_info=True)
        return _error(msg=str(e))


async def _auto_recommend_topics(folders: List[str]):
    """自动推荐值得写的话题：按分类统计后推荐（支持大规模知识库）"""
    try:
        from datetime import datetime, timedelta
        import time as _time
        import random
        
        now = datetime.now()
        
        # Step 1: 快速全量扫描（只取文件名 + mtime，不读内容）
        all_files_flat = []  # 不去重，记录全部文件
        for folder_path in folders:
            try:
                reader = LocalFolderReader(folder_path)
                files = reader.list_files_fast()  # 快速扫描，无 limit
                for f in files:
                    all_files_flat.append({
                        **f,
                        "folder": folder_path,
                    })
                logger.info(f"扫描 {folder_path}: 找到 {len(files)} 个 .md 文件")
            except Exception as e:
                logger.warning(f"扫描文件夹失败 {folder_path}: {e}")
        
        logger.info(f"共扫描到 {len(all_files_flat)} 个文件（未去重）")
        
        # 按路径去重（同一路径的文件只保留一个）
        seen_paths = set()
        all_file_basenames = {}
        for f in all_files_flat:
            if f["path"] not in seen_paths:
                seen_paths.add(f["path"])
                # 用相对路径作为唯一标识
                key = f["relative_path"]
                if key not in all_file_basenames:
                    all_file_basenames[key] = f
        
        if not all_file_basenames:
            return _success({
                "topics": [
                    {"name": "AI 行业趋势", "description": "分析当前 AI 行业热点和发展趋势", "coverage": 0.5, "reason": "通用题材", "needed": "最新行业动态"},
                ],
                "summary": "知识库为空，请先添加文件。",
                "source_files": [],
                "file_count": 0,
            })
        
        total_count = len(all_file_basenames)
        logger.info(f"知识库共 {total_count} 个文件，开始全量分类...")
        
        # Step 2: 全量读取 Front Matter + 内容，进行分类
        unique_files = []
        for name, info in all_file_basenames.items():
            try:
                reader = LocalFolderReader(info["folder"])
                content = reader.read_files([info["path"]])
                if content:
                    unique_files.append({
                        "name": name,
                        "path": info["path"],
                        "mtime": info["mtime"],
                        "folder": info["folder"],
                        "_full_content": content[0].get("content", ""),
                        "category": content[0].get("category", ""),
                    })
            except Exception as e:
                logger.warning(f"读取文件失败 {name}: {e}")
        
        # 分类统计
        category_counts = {}  # {category_key: [files]}
        uncategorized = []
        
        for f in unique_files:
            cats = _classify_file(f)
            if cats:
                for c in cats:
                    if c not in category_counts:
                        category_counts[c] = []
                    category_counts[c].append(f)
            else:
                uncategorized.append(f)
        
        logger.info(f"分类完成：{len(category_counts)} 个类别，{len(uncategorized)} 个未分类")
        
        # Step 3: 构建分类统计描述
        from src.classifier import ContentClassifier
        cat_names = ContentClassifier({}).get_categories()
        
        cat_desc_parts = []
        for cat_key, cat_files in sorted(category_counts.items(), key=lambda x: len(x[1]), reverse=True):
            cat_info = cat_names.get(cat_key, {})
            cat_count = len(cat_files)
            recent_names = [f["name"] for f in sorted(cat_files, key=lambda x: x["mtime"], reverse=True)[:2]]
            cat_desc_parts.append(f"- {cat_info.get('name', cat_key)}: {cat_count} 篇（最近：{', '.join(recent_names)}）")
        
        cat_desc = "\n".join(cat_desc_parts)
        if uncategorized:
            cat_desc += f"\n- 未分类/其他: {len(uncategorized)} 篇"
        
        # Step 4: 每个分类取最近 2 个作为代表传给 LLM
        llm_targets = []
        for cat_key, cat_files in category_counts.items():
            sorted_cats = sorted(cat_files, key=lambda x: x["mtime"], reverse=True)
            llm_targets.extend(sorted_cats[:2])
        if uncategorized:
            sorted_uncat = sorted(uncategorized, key=lambda x: x["mtime"], reverse=True)
            llm_targets.extend(sorted_uncat[:2])
        
        # 限制最多 10 个文件传给 LLM
        llm_targets = llm_targets[:10]
        
        llm_contents = []
        for f in llm_targets:
            content = f.get("_full_content", "")[:1500]
            if content:
                llm_contents.append(f"## {f['name']}\n\n{content}")
        
        context = "\n\n---\n\n".join(llm_contents)
        
        persona_content = _get_persona_summary()
        persona_context = f"\n\n作者身份定位：\n{persona_content}" if persona_content else ""
        
        llm_config = _get_config("llm")
        base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
        api_key = llm_config.get("api_key", "")
        model = llm_config.get("model", "deepseek-chat")
        timeout = llm_config.get("timeout", 60)
        
        prompt = f"""你是一个专业的选题策划师。请分析知识库内容分布，结合写作者的身份定位，推荐 3-5 个值得写的文章题材。

知识库总文件数：{total_count} 篇

分类分布：
{cat_desc}

代表文件内容摘要：
{context[:4000]}
{persona_context}

要求：
1. 推荐 3-5 个写作方向
2. 每个方向包含：name, description, coverage(0-1), reason, needed
3. **如果提供了作者身份定位，推荐的题材要符合该身份，体现其专业领域和视角**
4. 理由要具体，说明这批资料能写什么
5. 返回 JSON 格式（不要 markdown 代码块）：
{{
    "topics": [
        {{"name": "...", "description": "...", "coverage": 0.8, "reason": "...", "needed": "..."}}
    ],
    "summary": "知识库内容概况（100字内），说明各类别分布和文件总数"
}}

请直接返回 JSON：
"""
        
        import httpx
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4096,
                    "temperature": 0,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()
        
        content = result["choices"][0]["message"]["content"].strip()
        content = content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        parsed = json_mod.loads(content)
        
        topics = parsed.get("topics", [])
        summary = parsed.get("summary", "")
        
        return _success({
            "topics": topics,
            "summary": summary,
            "source_files": list(all_file_basenames.keys()),
            "file_count": total_count,
        })
        
    except Exception as e:
        logger.error(f"自动推荐失败: {e}", exc_info=True)
        return _success({
            "topics": [
                {"name": "综合分析报告", "description": "从多个维度全面分析", "coverage": 0.5, "reason": "通用题材", "needed": "具体数据"},
            ],
            "summary": "分析失败，请重试或输入关键词搜索。",
            "source_files": [],
            "file_count": 0,
        })


async def _process_async(task_id: str, framework_key: str, text: str, style: str, size: str):
    """异步处理逻辑"""
    try:
        async_tasks[task_id]["status"] = "processing"
        async_tasks[task_id]["progress"] = 10

        extractor = StructureExtractor(_get_config("llm"))
        data = extractor.extract(text, framework_key)
        async_tasks[task_id]["progress"] = 40

        generator = HTMLGenerator(_get_config("storage"))
        html = generator.render(data, framework_key, style, size)
        async_tasks[task_id]["progress"] = 70

        output_dir = Path(_get_config("storage").get("output_dir", "output"))
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{task_id}.png"

        screenshot = ScreenshotService()
        await screenshot.capture(html, str(output_path), size)
        async_tasks[task_id]["progress"] = 100
        async_tasks[task_id]["status"] = "completed"
        async_tasks[task_id]["output_path"] = str(output_path)

    except Exception as e:
        async_tasks[task_id]["status"] = "failed"
        async_tasks[task_id]["error"] = str(e)
        logger.error(f"异步任务失败: {str(e)}", exc_info=True)


# ===== 多段式工作流接口 =====

_sessions: Dict[str, Dict] = {}

def _get_session(session_id: str) -> Dict:
    """获取或创建会话状态"""
    if session_id not in _sessions:
        _sessions[session_id] = {
            "mcp_summary": "",
            "mcp_files": [],
            "completeness": 0,
            "supplement_count": 0,
            "step1": {},
            "step2": {},
            "step3": {},
            "outline": [],
        }
    return _sessions[session_id]


@router.post("/api/workflow/session/create")
async def create_session(request: Dict = Body(default={})):
    """创建新会话"""
    session_id = str(uuid.uuid4())[:8]
    _sessions[session_id] = {
        "mcp_summary": "",
        "mcp_files": [],
        "completeness": 0,
        "supplement_count": 0,
        "step1": {},
        "step2": {},
        "step3": {},
        "outline": [],
    }
    return _success({"session_id": session_id})


@router.post("/api/workflow/session/status")
async def get_session_status(request: Dict = Body(...)):
    """获取会话状态"""
    session_id = request.get("session_id", "")
    if not session_id or session_id not in _sessions:
        return _error(code=400, msg="会话不存在")
    return _success(_sessions[session_id])


@router.post("/api/workflow/completeness/evaluate")
async def evaluate_completeness(request: Dict = Body(...)):
    """评估信息完整度"""
    session_id = request.get("session_id", "")
    mcp_summary = request.get("mcp_summary", "")
    
    session = _get_session(session_id)
    session["mcp_summary"] = mcp_summary
    
    llm_config = _get_config("llm")
    base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = llm_config.get("api_key", "")
    model = llm_config.get("model", "deepseek-chat")
    timeout = llm_config.get("timeout", 60)
    
    # 获取身份定位信息
    persona_summary = ""
    try:
        persona_parsed = _get_persona_parsed()
        if persona_parsed:
            persona_summary = persona_parsed.get("summary", "")
    except:
        pass
    
    prompt = f"""你是一个内容策划专家。请评估以下素材的信息完整度，用于生成文章。

【MCP 素材摘要】
{mcp_summary}

【作者身份定位】
{persona_summary}

请从以下维度评估信息完整度（0-100分）：
1. 核心概念清晰度（30%）：主题/概念是否清晰
2. 应用场景具体性（25%）：是否有具体应用场景
3. 案例/数据丰富度（25%）：是否有真实案例或数据
4. 目标读者明确性（20%）：目标读者是否明确

返回 JSON 格式（不要 markdown 代码块）：
{{
  "completeness": 0-100的数字,
  "dimensions": {{
    "concept_clarity": 0-100,
    "scenario_specificity": 0-100,
    "case_richness": 0-100,
    "audience_clarity": 0-100
  }},
  "supplement_count": 建议补充次数（0-3的数字），
  "supplement_strategy": "补充策略描述（说明为什么需要这些补充）",
  "missing_critical": ["关键缺失项1", "关键缺失项2"],
  "missing_optional": ["可选缺失项1", "可选缺失项2"]
}}

规则：
- completeness >= 80: supplement_count = 0（信息充足，可直接生成）
- completeness 60-79: supplement_count = 1-2
- completeness < 60: supplement_count = 3

请直接返回 JSON：
"""
    
    try:
        import httpx
        logger.info(f"开始评估完整度, session: {session_id}")
        async with httpx.AsyncClient(timeout=httpx.Timeout(30, connect=10)) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                    "temperature": 0,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()
        
        parsed_content = result["choices"][0]["message"]["content"].strip()
        parsed_content = parsed_content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        evaluation = json_mod.loads(parsed_content)
        
        session["completeness"] = evaluation.get("completeness", 0)
        session["supplement_count"] = evaluation.get("supplement_count", 3)
        
        logger.info(f"评估完成: completeness={session['completeness']}")
        return _success(evaluation)
    except Exception as e:
        logger.error(f"完整度评估失败: {e}")
        # 默认返回保守评估
        return _success({
            "completeness": 50,
            "supplement_count": 3,
            "supplement_strategy": "信息不足，建议补充3次",
            "missing_critical": ["案例/数据", "应用场景"],
            "missing_optional": ["ROI数据", "避坑指南"]
        })


@router.post("/api/workflow/directions/analyze")
async def analyze_directions_v2(request: Dict = Body(...)):
    """推荐写作方向（带缺失项展示）"""
    session_id = request.get("session_id", "")
    mcp_summary = request.get("mcp_summary", "")
    
    session = _get_session(session_id)
    
    llm_config = _get_config("llm")
    base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = llm_config.get("api_key", "")
    model = llm_config.get("model", "deepseek-chat")
    timeout = llm_config.get("timeout", 60)
    
    persona_summary = ""
    try:
        persona_parsed = _get_persona_parsed()
        if persona_parsed:
            persona_summary = persona_parsed.get("summary", "")
    except:
        pass
    
    prompt = f"""你是一个内容策划专家。请基于以下素材，推荐2-3个写作方向。

【MCP 素材摘要】
{mcp_summary}

【作者身份定位】
{persona_summary}

═══════════ 透明推理原则（必须严格执行）═══════════
1. 每个方向必须有推荐理由（基于素材中的哪一点）
2. 标注推荐来源：
   - user_content: 直接从素材推导
   - user_implied: 素材隐含但未明说
   - general_knowledge: 基于通用领域知识
3. 提供2-3个选项，不替用户做决定
4. 标注置信度：high/medium/low（由你判断，基于素材充分度）

═══════════ 生成原则 ═══════════
- 如果素材不足，标注 confidence=low，不要编造
- 如果推荐基于通用知识，标注 source=general_knowledge
- 每个方向必须具体可操作，不要泛泛而谈
- evidence_quote 可选：如果能准确引用素材原文就加上，不能则留空字符串

请推荐2-3个写作方向，返回 JSON 格式（不要 markdown 代码块）：
[
  {{
    "name": "主张型：论证 Vibe Coding 的优越性",
    "description": "方向描述（1-2句话）",
    "coverage": 0.85,
    "reason": "基于你提到的'比传统编程快很多'这一主张性表述",
    "evidence_quote": "它比传统编程快很多，特别适合快速原型开发",
    "source": "user_content",
    "confidence": "high",
    "scenario": "适合说服持怀疑态度的开发者读者",
    "risk": "需要提供具体数据支撑'快很多'的说法",
    "missing_critical": ["关键缺失项1", "关键缺失项2"],
    "missing_optional": ["可选缺失项1"],
    "frameworks": ["推荐框架1", "推荐框架2"]
  }}
]

最后增加一个推荐字段：
{{
  "directions": [...],
  "recommendation": "主张型",
  "recommendation_reason": "你的素材有明确主张语气，且有反面质疑（适合做驳论）"
}}

请直接返回 JSON：
"""
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2048,
                    "temperature": 0,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()
        
        parsed_content = result["choices"][0]["message"]["content"].strip()
        parsed_content = parsed_content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        result_data = json_mod.loads(parsed_content)
        
        # 确保返回格式包含透明推理字段（Phase 4 P0 兜底逻辑）
        valid_sources = ["user_content", "user_implied", "general_knowledge"]
        valid_confidence = ["high", "medium", "low"]
        
        if isinstance(result_data, dict) and "directions" in result_data:
            # 新格式：{"directions": [...], "recommendation": ...}
            for d in result_data["directions"]:
                if not isinstance(d, dict):
                    continue
                d.setdefault("source", "user_implied")
                d.setdefault("confidence", "medium")
                d.setdefault("reason", "")
                d.setdefault("evidence_quote", "")
                d.setdefault("scenario", "")
                d.setdefault("risk", "")
                d.setdefault("missing_critical", [])
                d.setdefault("missing_optional", [])
                d.setdefault("frameworks", [])
                
                # 校验字段值
                if d.get("source") not in valid_sources:
                    d["source"] = "user_implied"
                if d.get("confidence") not in valid_confidence:
                    d["confidence"] = "medium"
            
            result_data.setdefault("recommendation", "")
            result_data.setdefault("recommendation_reason", "")
        elif isinstance(result_data, list):
            # 兼容旧格式：直接返回数组
            for d in result_data:
                if not isinstance(d, dict):
                    continue
                d.setdefault("source", "user_implied")
                d.setdefault("confidence", "medium")
                d.setdefault("reason", "")
                d.setdefault("evidence_quote", "")
                d.setdefault("scenario", "")
                d.setdefault("risk", "")
                d.setdefault("missing_critical", [])
                d.setdefault("missing_optional", [])
                d.setdefault("frameworks", [])
                
                if d.get("source") not in valid_sources:
                    d["source"] = "user_implied"
                if d.get("confidence") not in valid_confidence:
                    d["confidence"] = "medium"
            
            result_data = {
                "directions": result_data,
                "recommendation": "",
                "recommendation_reason": "",
            }
        
        return _success(result_data)
    except Exception as e:
        logger.error(f"方向推荐失败: {e}")
        return _error(msg=str(e))


@router.post("/api/workflow/supplement/1")
async def supplement_1(request: Dict = Body(...)):
    """第1次补充：方向相关信息（粗粒度）"""
    session_id = request.get("session_id", "")
    direction = request.get("direction", "")
    supplement_info = request.get("supplement_info", {})
    
    session = _get_session(session_id)
    session["step1"] = {
        "selected_direction": direction,
        "supplement_1": supplement_info,
    }
    
    return _success({"status": "ok", "message": "第1次补充已保存"})


@router.post("/api/workflow/frameworks/match")
async def match_frameworks_v2(request: Dict = Body(...)):
    """推荐分析框架(v2: 双评分+降级兜底+业务化warning)"""
    session_id = request.get("session_id", "")
    direction = request.get("direction", "")
    supplement_1 = request.get("supplement_1", {})
    mcp_summary = request.get("mcp_summary", "")
    
    if not direction or len(direction.strip()) < 8:
        return _error(
            code=400,
            msg="方向描述过于模糊,请补充至少一个具体场景或受众(如'AI在中小企业财务自动化中的应用')",
        )
    
    session = _get_session(session_id)
    
    llm_config = _get_config("llm")
    base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = llm_config.get("api_key", "")
    model = llm_config.get("model", "deepseek-chat")
    timeout = llm_config.get("timeout", 60)
    
    fw_config = _get_config("framework_recommendation") or {}
    PREMIUM_THRESHOLD = float(fw_config.get("alignment_threshold_premium", 0.7))
    FALLBACK_THRESHOLD = float(fw_config.get("alignment_threshold_fallback", 0.6))
    
    persona_summary = ""
    persona_filter = ""
    try:
        persona_parsed = _get_persona_parsed()
        if persona_parsed:
            persona_summary = persona_parsed.get("summary", "")
            persona_filter = persona_parsed.get("filter", "")
    except:
        pass
    
    prompt = f"""你是一个内容策划专家。请基于以下信息，**严格围绕"选定方向"**推荐3个分析框架。

【MCP 素材摘要】
{mcp_summary}

【选定方向】（这是用户已经确定的写作方向，框架必须服务于这个方向）
{direction}

【第1次补充信息】
{json.dumps(supplement_1, ensure_ascii=False, indent=2)}

【作者认知过滤】
{persona_filter}

═══════════ 透明推理原则（必须严格执行）═══════════
1. 每个框架必须有推荐理由（为什么匹配用户方向）
2. 标注推荐来源：
   - user_content: 直接从方向描述推导
   - user_implied: 方向隐含但未明说
   - general_knowledge: 基于通用领域知识
3. 标注方向对齐度（direction_alignment_score，0-1）
4. 如果对齐度<0.6，请勿推荐

═══════════ 强制规则（必须严格执行）═══════════
1. 每个推荐框架必须能直接服务于「{direction}」这个具体方向
2. 严禁推荐与方向核心场景脱节的通用框架
   - 反面示例：方向是"个人IP构建"，却推荐"领导力框架"（适用于组织管理，不适合个人IP）
   - 反面示例：方向是"AI降本增效"，却推荐"组织变革框架"（脱离技术落地场景）
3. 必须在 reason 中明确写出"框架的每个维度如何对应方向的关键问题"
4. 方向对齐度评分标准:
   - ≥0.8: 优秀(框架核心维度与方向高度契合)
   - 0.7-0.8: 良好(大部分维度贴合,可推荐)
   - 0.6-0.7: 勉强(需要转化使用,要在 warning 中说明)
   - <0.6: 不适用(请勿推荐,换更契合的框架)
5. 如果实在找不到3个对齐度≥0.6的框架，宁可只返回1-2个，也不要凑数
6. warning 字段必须用"业务视角"(站在决策者角度),不要用技术视角
   - ✅ 正确: "⚠️ 风险提示:该框架偏向组织管理,若用于个人IP构建需自行转化语境,建议优先参考前两项"
   -  错误: "该框架原用于管理者对下属的辅导..."(技术视角)
7. evidence_quote 可选：如果能准确引用方向描述就加上，不能则留空字符串

返回 JSON 格式（不要 markdown 代码块），按 direction_alignment_score 降序排列：
[
  {{
    "name": "框架名称",
    "description": "框架描述（1-2句话）",
    "direction_alignment_score": 0.95,
    "direction_alignment_reason": "该框架的XX维度对应方向的YY关键问题，ZZ维度对应...",
    "reason": "为什么适合（具体到方向场景）",
    "evidence_quote": "你的方向描述中...（可选）",
    "source": "user_content",
    "framework_origin": "管理学/营销学/心理学/经济学/技术架构/内容创作 等学科归属",
    "usage_hint": "这个框架适合用来做什么",
    "warning": "如果对齐度<0.8，写明业务视角的潜在风险；否则留空字符串",
    "needs_supplement": ["需要补充的信息1", "需要补充的信息2"]
  }}
]

请直接返回 JSON 数组：
"""
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2048,
                    "temperature": 0,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()
        
        parsed_content = result["choices"][0]["message"]["content"].strip()
        parsed_content = parsed_content.replace("```json", "").replace("```", "").strip()
        frameworks = json.loads(parsed_content)
        
        if not isinstance(frameworks, list):
            frameworks = [frameworks]
        
        for fw in frameworks:
            fw.setdefault("name", "未知框架")
            fw.setdefault("description", "")
            fw.setdefault("direction_alignment_score", fw.get("match_score", 0.5))
            fw.setdefault("direction_alignment_reason", "")
            fw.setdefault("reason", "")
            fw.setdefault("evidence_quote", "")
            fw.setdefault("source", "user_implied")
            fw.setdefault("framework_origin", "")
            fw.setdefault("usage_hint", "")
            fw.setdefault("warning", "")
            fw.setdefault("needs_supplement", [])
            
            # 校验 source 取值
            valid_sources = ["user_content", "user_implied", "general_knowledge"]
            if fw.get("source") not in valid_sources:
                fw["source"] = "user_implied"
            try:
                align = float(fw.get("direction_alignment_score") or 0)
            except (TypeError, ValueError):
                align = 0.0
                fw["direction_alignment_score"] = 0.0
            if align < PREMIUM_THRESHOLD and not fw.get("warning"):
                fw["warning"] = (
                    f"⚠️ 风险提示：该框架方向对齐度仅 {align*100:.0f}%，"
                    f"用于「{direction}」需要自行转化语境，建议优先参考排名靠前的框架"
                )
        
        frameworks = [f for f in frameworks if float(f.get("direction_alignment_score") or 0) >= FALLBACK_THRESHOLD]
        frameworks.sort(key=lambda f: float(f.get("direction_alignment_score") or 0), reverse=True)
        
        if not frameworks:
            logger.warning(f"框架推荐: 所有候选对齐度均<{FALLBACK_THRESHOLD},方向='{direction}'")
            return _success({
                "frameworks": [],
                "mode": "rejected",
                "banner": (
                    f"❌ 无法为「{direction}」推荐合适的框架。"
                    f"可能原因:方向描述过于宽泛或专业领域稀少。"
                    f"建议:补充1-2个具体场景或受众,如'AI在XX行业的YY应用',再重新推荐。"
                ),
            })
        
        max_align = max(float(f.get("direction_alignment_score") or 0) for f in frameworks)
        if max_align < PREMIUM_THRESHOLD:
            logger.warning(f"框架推荐降级模式: 最高对齐度{max_align:.2f}<{PREMIUM_THRESHOLD}, 方向='{direction}'")
            return _success({
                "frameworks": frameworks,
                "mode": "fallback",
                "banner": (
                    f"⚠️ 当前方向「{direction}」较为冷门,以下框架对齐度有限"
                    f"(最高{max_align*100:.0f}%),建议人工评估或补充更具体的场景描述。"
                ),
            })
        
        return _success({
            "frameworks": frameworks,
            "mode": "premium",
            "banner": "",
        })
    except json.JSONDecodeError as e:
        logger.error(f"框架推荐 JSON 解析失败: {e}")
        default_frameworks = [
            {
                "name": "SWOT 分析",
                "description": "从优势、劣势、机会、威胁四个维度进行分析",
                "match_score": 0.7,
                "direction_alignment_score": 0.65,
                "direction_alignment_reason": "通用分析框架,可灵活应用于多种方向,但需要根据方向自行映射四个维度",
                "reason": "通用分析框架，适合大多数场景",
                "warning": "⚠️ 风险提示:这是兜底返回的通用框架,可能未充分契合您的具体方向,建议重新生成或人工评估",
                "framework_origin": "战略管理学",
                "needs_supplement": ["具体案例数据"]
            },
        ]
        return _success({
            "frameworks": default_frameworks,
            "mode": "fallback",
            "banner": "⚠️ AI推荐解析异常,以下为通用兜底框架,建议点击'重新推荐'获取定制方案",
        })
    except Exception as e:
        logger.error(f"框架推荐失败: {e}")
        return _error(msg=str(e))


@router.post("/api/workflow/supplement/2")
async def supplement_2(request: Dict = Body(...)):
    """第2次补充：完善分析内容（中粒度）"""
    session_id = request.get("session_id", "")
    framework = request.get("framework", "")
    supplement_info = request.get("supplement_info", {})
    
    session = _get_session(session_id)
    session["step2"] = {
        "selected_framework": framework,
        "supplement_2": supplement_info,
    }
    
    return _success({"status": "ok", "message": "第2次补充已保存"})


@router.post("/api/workflow/direction/check")
async def check_direction(request: Dict = Body(...)):
    """方向检测：检测分析内容的问题（含前置拦截）"""
    session_id = request.get("session_id", "")
    direction = request.get("direction", "")
    framework = request.get("framework", "")
    supplement_1 = request.get("supplement_1", {})
    supplement_2 = request.get("supplement_2", {})
    mcp_summary = request.get("mcp_summary", "")
    
    # ═══════════════════════════════════════════════════════
    # 前置拦截：内容为空/无意义时直接返回pending，不调用LLM
    # 避免"推荐时匹配度高，检测时全红报错"的认知矛盾
    # ═══════════════════════════════════════════════════════
    supplement_text = (supplement_2.get("text") or "").strip()
    supplement_cases = supplement_2.get("cases") or supplement_2.get("data_points") or []
    supplement_structure = supplement_2.get("structure") or supplement_2.get("framework_content") or ""
    
    has_meaningful_content = (
        supplement_text or supplement_cases or supplement_structure
    ) and len(supplement_text) > 20
    
    if not has_meaningful_content:
        pending_issues = [
            {"dimension": "方向偏离", "status": "pending"},
            {"dimension": "案例不足", "status": "pending"},
            {"dimension": "数据缺失", "status": "pending"},
            {"dimension": "结构混乱", "status": "pending"},
            {"dimension": "价值标准", "status": "pending"},
        ]
        return _success({
            "status": "pending",
            "content_completeness_score": 0,
            "overall_score": 0,
            "ready_for_next": False,
            "issues": [
                {
                    "type": "info",
                    "category": "pending",
                    "title": "待补充分析素材",
                    "description": (
                        f"请补充与「{direction}」相关的落地素材（如目标受众画像、赛道数据、实操案例等），"
                        f"至少包含一句完整分析（20字以上）。完成后系统将自动评估以下5个维度。"
                    ),
                    "suggestion": "建议至少补充1-2个实操案例或关键数据",
                    "can_auto_fix": False
                }
            ],
            "pending_dimensions": pending_issues,
        })
    
    # ═══════════════════════════════════════════════════════
    # 内容已有意义，正常调用LLM检测
    # ═══════════════════════════════════════════════════════
    
    llm_config = _get_config("llm")
    base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = llm_config.get("api_key", "")
    model = llm_config.get("model", "deepseek-chat")
    timeout = llm_config.get("timeout", 60)
    
    persona_summary = ""
    persona_voice = {}
    persona_value = {}
    try:
        persona_parsed = _get_persona_parsed()
        if persona_parsed:
            persona_summary = persona_parsed.get("summary", "")
            persona_voice = persona_parsed.get("voice", {})
            persona_value = persona_parsed.get("value", {})
    except:
        pass
    
    # 合并结构化字段和自由文本，让 LLM 能正确评估
    supplement_2_display = json.dumps(supplement_2, ensure_ascii=False, indent=2)
    if supplement_2.get("text"):
        supplement_2_display += f"\n\n【补充文本（自由输入内容）】\n{supplement_2['text']}"
    
    prompt = f"""你是一个内容质量检查专家。请检测以下分析内容是否存在问题。

【MCP 素材摘要】
{mcp_summary}

【选定方向】{direction}
【选定框架】{framework}

【第1次补充信息】
{json.dumps(supplement_1, ensure_ascii=False, indent=2)}

【第2次补充信息】
{supplement_2_display}

【作者表达范式】
{json.dumps(persona_voice, ensure_ascii=False)}

【作者价值标准】
{json.dumps(persona_value, ensure_ascii=False)}

请检测以下维度的问题：
1. 方向偏离：内容是否偏离了选定方向？
2. 案例不足：案例数量是否足够？（至少2-3个）
3. 数据缺失：是否缺少关键数据支撑？
4. 结构混乱：分析结构是否清晰？
5. 价值标准：是否符合"可落地实操"的要求？

注意：第2次补充信息中的"补充文本（自由输入内容）"也是有效的分析内容，请将其视为已补充的内容进行评估。如果用户已提供了补充文本，不应再将其列为缺失项。

返回 JSON 格式（不要 markdown 代码块）：
{{
  "issues": [
    {{
      "type": "error | warning | pass",
      "category": "direction | cases | data | structure | value",
      "title": "问题标题",
      "description": "问题描述",
      "suggestion": "修改建议",
      "can_auto_fix": true 或 false
    }}
  ],
  "overall_score": 0-100,
  "ready_for_next": true 或 false
}}

注意：
- type="error" 表示必须修正的问题
- type="warning" 表示建议优化的问题
- type="pass" 表示通过检查
- can_auto_fix=true 表示AI可以自动修改修正

请直接返回 JSON：
"""
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2048,
                    "temperature": 0,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()
        
        parsed_content = result["choices"][0]["message"]["content"].strip()
        parsed_content = parsed_content.replace("```json", "").replace("```", "").strip()
        check_result = json.loads(parsed_content)
        
        # 验证返回格式
        check_result.setdefault("issues", [])
        check_result.setdefault("overall_score", 50)
        check_result.setdefault("ready_for_next", True)
        check_result.setdefault("content_completeness_score", check_result.get("overall_score", 0))
        check_result.setdefault("status", "checked")
        
        return _success(check_result)
    except json.JSONDecodeError as e:
        logger.error(f"方向检测 JSON 解析失败: {e}")
        # 返回默认检测结果
        default_result = {
            "status": "checked",
            "content_completeness_score": 50,
            "issues": [
                {
                    "type": "warning",
                    "category": "cases",
                    "title": "案例数量不足",
                    "description": "建议至少2-3个具体案例",
                    "suggestion": "补充更多实战案例",
                    "can_auto_fix": False
                }
            ],
            "overall_score": 60,
            "ready_for_next": True
        }
        return _success(default_result)
    except Exception as e:
        logger.error(f"方向检测失败: {e}")
        return _error(msg=str(e))


@router.post("/api/workflow/direction/fix")
async def fix_direction_issue(request: Dict = Body(...)):
    """AI 修改：根据检测结果自动修正问题"""
    session_id = request.get("session_id", "")
    issue = request.get("issue", {})
    supplement_1 = request.get("supplement_1", {})
    supplement_2 = request.get("supplement_2", {})
    mcp_summary = request.get("mcp_summary", "")
    direction = request.get("direction", "")
    framework = request.get("framework", "")
    
    llm_config = _get_config("llm")
    base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = llm_config.get("api_key", "")
    model = llm_config.get("model", "deepseek-chat")
    timeout = llm_config.get("timeout", 60)
    
    persona_summary = ""
    try:
        persona_parsed = _get_persona_parsed()
        if persona_parsed:
            persona_summary = persona_parsed.get("summary", "")
    except:
        pass
    
    issue_category = issue.get("category", "")
    issue_description = issue.get("description", "")
    issue_suggestion = issue.get("suggestion", "")
    
    prompt = f"""你是一个内容修改专家。请根据以下问题和建议，修改补充内容。

【问题信息】
类别：{issue_category}
问题描述：{issue_description}
修改建议：{issue_suggestion}

【当前补充内容】
第1次补充：{json.dumps(supplement_1, ensure_ascii=False)}
第2次补充：{json.dumps(supplement_2, ensure_ascii=False)}

【写作方向】{direction}
【分析框架】{framework}

【作者身份定位】
{persona_summary}

请修改补充内容，解决上述问题。返回 JSON 格式（不要 markdown 代码块）：
{{
  "fixed_supplement_1": {{修改后的第1次补充}},
  "fixed_supplement_2": {{修改后的第2次补充}},
  "fix_description": "修改说明（告诉用户做了什么修改）"
}}

注意：
- 只修改与问题相关的内容，保留其他内容
- 修改要符合身份定位的风格
- 如果不能自动修正，返回原始内容并说明原因

请直接返回 JSON：
"""
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2048,
                    "temperature": 0,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()
        
        parsed_content = result["choices"][0]["message"]["content"].strip()
        parsed_content = parsed_content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        fix_result = json_mod.loads(parsed_content)
        
        # 更新会话状态
        session = _get_session(session_id)
        if fix_result.get("fixed_supplement_1"):
            session["step1"]["supplement_1"] = fix_result["fixed_supplement_1"]
        if fix_result.get("fixed_supplement_2"):
            session["step2"]["supplement_2"] = fix_result["fixed_supplement_2"]
        
        return _success(fix_result)
    except Exception as e:
        logger.error(f"AI 修改失败: {e}")
        return _error(msg=str(e))


@router.post("/api/workflow/structures/recommend")
async def recommend_structures(request: Dict = Body(...)):
    """推荐内容结构"""
    session_id = request.get("session_id", "")
    direction = request.get("direction", "")
    framework = request.get("framework", "")
    supplement_1 = request.get("supplement_1", {})
    supplement_2 = request.get("supplement_2", {})
    mcp_summary = request.get("mcp_summary", "")
    
    llm_config = _get_config("llm")
    base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = llm_config.get("api_key", "")
    model = llm_config.get("model", "deepseek-chat")
    timeout = llm_config.get("timeout", 60)
    
    persona_summary = ""
    persona_voice = {}
    try:
        persona_parsed = _get_persona_parsed()
        if persona_parsed:
            persona_summary = persona_parsed.get("summary", "")
            persona_voice = persona_parsed.get("voice", {})
    except:
        pass
    
    prompt = f"""你是一个内容结构专家。请基于以下信息，推荐2-3个文章叙事结构方案。

注意：你推荐的是「文章叙事结构」（文章段落如何组织），不是「分析框架」。分析框架已由用户选定（见下方），请基于该框架，推荐适合的叙事结构。

【MCP 素材摘要】
{mcp_summary}

【写作方向】{direction}
【分析框架】{framework}

【第1次补充】{json.dumps(supplement_1, ensure_ascii=False)}
【第2次补充】{json.dumps(supplement_2, ensure_ascii=False)}

【作者身份定位】{persona_summary}
【作者表达范式】{json.dumps(persona_voice, ensure_ascii=False)}

叙事结构示例（不是分析框架，而是文章组织方式）：
- 问题→拆解→方案（递进式）
- 现象→本质→启示（剖析式）
- 故事→洞察→行动（场景化）
- 对比→分析→结论（对比式）
- 时间线→里程碑→展望（演进式）
- 总→分→总（总分式）

═══════════ 透明推理原则（必须严格执行）═══════════
1. 每个结构必须有推荐理由（为什么这个结构适合用户方向+框架）
2. 标注推荐来源：
   - user_content: 直接从方向/框架描述推导
   - user_implied: 方向/框架隐含但未明说
   - general_knowledge: 基于通用写作知识
3. 提供2-3个选项，不替用户做决定
4. 标注置信度：high/medium/low（由你判断）

═══════════ 生成原则 ═══════════
- 结构建议要具体到"每段填什么"，不要只给抽象框架
- 明确标注用户已有什么、还缺什么
- 如果用户内容不足，标注 confidence=low
- evidence_quote 可选：如果能准确引用方向/框架描述就加上，不能则留空字符串

请推荐2-3个叙事结构方案，返回 JSON 格式（不要 markdown 代码块）：
[
  {{
    "name": "递进式",
    "description": "结构描述（文章如何分段组织）",
    "match_score": 0.9,
    "reason": "为什么这个结构适合你的方向+框架",
    "evidence_quote": "你的方向中提到...（可选）",
    "source": "user_content",
    "confidence": "high",
    "sections": [
      {{"name": "开场", "hint": "用一句话吸引注意力"}},
      {{"name": "分析", "hint": "基于你提到的XX展开"}},
      {{"name": "总结", "hint": "重申核心观点"}}
    ],
    "missing_content": ["还需要补充的案例或数据"]
  }}
]

最后增加一个推荐字段：
{{
  "structures": [...],
  "recommendation": "递进式",
  "recommendation_reason": "你的方向是主张型，递进式结构适合层层深入论证"
}}

请直接返回 JSON：
"""
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2048,
                    "temperature": 0,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()
        
        parsed_content = result["choices"][0]["message"]["content"].strip()
        parsed_content = parsed_content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        result_data = json_mod.loads(parsed_content)
        
        # 后端兜底逻辑（Phase 4 P1）
        valid_sources = ["user_content", "user_implied", "general_knowledge"]
        valid_confidence = ["high", "medium", "low"]
        
        if isinstance(result_data, dict) and "structures" in result_data:
            for s in result_data["structures"]:
                if not isinstance(s, dict):
                    continue
                s.setdefault("source", "user_implied")
                s.setdefault("confidence", "medium")
                s.setdefault("reason", "")
                s.setdefault("evidence_quote", "")
                s.setdefault("sections", [])
                s.setdefault("missing_content", [])
                
                if s.get("source") not in valid_sources:
                    s["source"] = "user_implied"
                if s.get("confidence") not in valid_confidence:
                    s["confidence"] = "medium"
            
            result_data.setdefault("recommendation", "")
            result_data.setdefault("recommendation_reason", "")
        elif isinstance(result_data, list):
            for s in result_data:
                if not isinstance(s, dict):
                    continue
                s.setdefault("source", "user_implied")
                s.setdefault("confidence", "medium")
                s.setdefault("reason", "")
                s.setdefault("evidence_quote", "")
                s.setdefault("sections", [])
                s.setdefault("missing_content", [])
                
                if s.get("source") not in valid_sources:
                    s["source"] = "user_implied"
                if s.get("confidence") not in valid_confidence:
                    s["confidence"] = "medium"
            
            result_data = {
                "structures": result_data,
                "recommendation": "",
                "recommendation_reason": "",
            }
        
        return _success(result_data)
    except Exception as e:
        logger.error(f"结构推荐失败: {e}")
        return _error(msg=str(e))


@router.post("/api/workflow/supplement/3")
async def supplement_3(request: Dict = Body(...)):
    """第3次补充：案例/数据（细粒度）"""
    session_id = request.get("session_id", "")
    structure = request.get("structure", "")
    supplement_info = request.get("supplement_info", {})
    
    session = _get_session(session_id)
    session["step3"] = {
        "selected_structure": structure,
        "supplement_3": supplement_info,
    }
    
    return _success({"status": "ok", "message": "第3次补充已保存"})


@router.post("/api/workflow/outline/generate")
async def generate_outline_v2(request: Dict = Body(...)):
    """生成写作提纲（基于所有补充信息）"""
    session_id = request.get("session_id", "")
    session = _get_session(session_id)
    
    direction = session.get("step1", {}).get("selected_direction", "")
    framework = session.get("step2", {}).get("selected_framework", "")
    structure = session.get("step3", {}).get("selected_structure", "")
    supplement_1 = session.get("step1", {}).get("supplement_1", {})
    supplement_2 = session.get("step2", {}).get("supplement_2", {})
    supplement_3 = session.get("step3", {}).get("supplement_3", {})
    mcp_summary = session.get("mcp_summary", "")
    
    llm_config = _get_config("llm")
    base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = llm_config.get("api_key", "")
    model = llm_config.get("model", "deepseek-chat")
    timeout = llm_config.get("timeout", 60)
    
    persona_summary = ""
    persona_voice = {}
    persona_filter = ""
    try:
        persona_parsed = _get_persona_parsed()
        if persona_parsed:
            persona_summary = persona_parsed.get("summary", "")
            persona_voice = persona_parsed.get("voice", {})
            persona_filter = persona_parsed.get("filter", "")
    except:
        pass
    
    # 具名骨架定义（固定 5 段式：痛点→拆解→方案）
    SKELETON_TEMPLATE = {
        "hook": {
            "label": "引言（痛点切入）",
            "description": "用可量化的痛点/场景引入，避免泛化描述",
        },
        "problem": {
            "label": "核心问题",
            "description": "拆解痛点的核心成因（2-3个）",
        },
        "breakdown": {
            "label": "维度拆解",
            "description": "按可落地的维度拆解解决路径（3-5个）",
        },
        "solution": {
            "label": "落地方案",
            "description": "对应每个维度的具体操作步骤/工具/配置",
        },
        "action": {
            "label": "行动建议",
            "description": "可立即执行的下一步动作（可量化）",
        },
    }

    prompt = f"""你是一个写作提纲生成专家。请基于以下所有信息，按「痛点→拆解→方案」骨架生成详细的写作提纲。

【骨架定义】（5 个固定 section，不能增减或改名）
1. hook（引言）：用可量化的痛点/场景切入，禁止泛化描述
2. problem（核心问题）：拆解痛点的 2-3 个核心成因
3. breakdown（维度拆解）：按可落地的维度拆解解决路径（3-5个）
4. solution（落地方案）：对应每个维度的具体操作步骤/工具/配置
5. action（行动建议）：可立即执行的下一步动作（可量化）

【MCP 素材摘要】
{mcp_summary}

【写作方向】{direction}
【分析框架】{framework}
【内容结构】{structure}

【第1次补充（方向信息）】
{json.dumps(supplement_1, ensure_ascii=False, indent=2)}

【第2次补充（分析内容）】
{json.dumps(supplement_2, ensure_ascii=False, indent=2)}

【第3次补充（案例数据）】
{json.dumps(supplement_3, ensure_ascii=False, indent=2)}

【作者身份定位】
{persona_summary}

【作者认知过滤】
{persona_filter}

【作者表达范式】
{json.dumps(persona_voice, ensure_ascii=False)}

请生成详细的写作提纲，返回 JSON 格式（不要 markdown 代码块）：
{{
  "title": "文章标题建议",
  "direction_alignment_score": 0.95,
  "direction_alignment_reason": "全文如何紧扣方向「{direction}」,关键章节如何对应方向核心问题",
  "sections": {{
    "hook": {{
      "title": "段落标题",
      "content": "该段落的核心内容概要（2-3句话）",
      "source_tag": "anchored 或 derived 或 missing",
      "key_points": ["要点1", "要点2"],
      "word_count_estimate": 300
    }},
    "problem": {{ ... 同上结构 ... }},
    "breakdown": {{ ... 同上结构 ... }},
    "solution": {{ ... 同上结构 ... }},
    "action": {{ ... 同上结构 ... }}
  }},
  "missing_items": [
    {{
      "field": "缺失的素材/数据/案例名称",
      "fill_guidance": "给用户的补充建议（具体可操作，不要泛泛而谈）"
    }}
  ],
  "estimated_total_words": 总字数估算
}}

═══════════ 强制规则（必须严格执行）═══════════
1. 每个 section 必须紧扣方向「{direction}」,严禁跑题
   - 反面示例：方向是"AI降本增效"，提纲却写"AI技术发展史"（脱离落地场景）
   - 反面示例：方向是"个人IP构建"，提纲却写"团队管理方法"（脱离个人场景）
2. direction_alignment_score 评分标准:
   - ≥0.8: 优秀(全部 section 紧扣方向)
   - 0.7-0.8: 良好(大部分 section 紧扣方向)
   - <0.7: 跑题风险(必须重写)
3. direction_alignment_reason 必须具体到"哪个 section 对应方向的哪个核心问题"

溯源规则（必须严格执行）：
- source_tag = "anchored"：MCP 摘要或用户补充中明确提及的信息，可直接使用
- source_tag = "derived"：从已有信息逻辑推导得出的结论，需合理推断
- source_tag = "missing"：MCP 摘要和补充中完全未提及，必须在 missing_items 中列出并生成 fill_guidance

禁止项：
- 严禁编造案例、数据、用户画像
- 严禁使用泛化表述（如"很多企业""通常来说"）
- 5 个 section 必须全部输出，不能增减
- missing 项的 fill_guidance 要具体可操作，给出补充方向

内容要求：
- 理论≤20%，实战≥80%
- 每个核心段落都应有案例或数据支撑（anchored 优先）
- 引言和结论要简洁有力

请直接返回 JSON：
"""
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4096,
                    "temperature": 0,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            result = response.json()
        
        parsed_content = result["choices"][0]["message"]["content"].strip()
        parsed_content = parsed_content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        import re as _re
        try:
            outline = json_mod.loads(parsed_content)
        except json_mod.JSONDecodeError as je:
            logger.warning(f"提纲JSON解析失败,尝试修复: {je}")
            fixed = _re.sub(r",\s*([}\]])", r"\1", parsed_content)
            fixed = _re.sub(r"}\s*\n\s*\"", '},\n  "', fixed)
            try:
                outline = json_mod.loads(fixed)
            except Exception:
                m = _re.search(r"\{[\s\S]*\}", parsed_content)
                if m:
                    try:
                        outline = json_mod.loads(m.group(0))
                    except Exception as ee:
                        logger.error(f"提纲JSON二次修复仍失败: {ee}")
                        return _error(msg=f"LLM返回非法JSON: {str(je)[:200]}")
                else:
                    return _error(msg=f"LLM返回非法JSON: {str(je)[:200]}")
        
        if not isinstance(outline, dict) or "sections" not in outline:
            return _error(msg="提纲格式不符合v2规范(缺少sections字段)")
        if isinstance(outline.get("sections"), list):
            old_sections = outline["sections"]
            named_keys = ["hook", "problem", "breakdown", "solution", "action"]
            new_sections = {}
            for i, sec in enumerate(old_sections[:5]):
                key = named_keys[i] if i < len(named_keys) else f"section_{i}"
                if isinstance(sec, dict):
                    sec.setdefault("source_tag", "derived")
                    new_sections[key] = sec
            outline["sections"] = new_sections
        outline.setdefault("missing_items", [])
        outline.setdefault("direction_alignment_score", 0.7)
        outline.setdefault("direction_alignment_reason", "")
        try:
            outline_align = float(outline.get("direction_alignment_score") or 0)
        except (TypeError, ValueError):
            outline_align = 0.7
            outline["direction_alignment_score"] = 0.7
        if outline_align < 0.7:
            outline["alignment_warning"] = (
                f"⚠️ 提纲方向对齐度仅 {outline_align*100:.0f}%，"
                f"可能存在跑题风险，建议点击'重新生成'或人工校对每个 section 是否紧扣「{direction}」"
            )
            logger.warning(f"提纲跑题风险: 对齐度{outline_align:.2f}<0.7, 方向='{direction}'")
        else:
            outline.setdefault("alignment_warning", "")
        
        session["outline"] = outline
        
        return _success(outline)
    except Exception as e:
        logger.error(f"提纲生成失败: {e}")
        return _error(msg=str(e))


@router.post("/api/workflow/article/generate")
async def generate_full_article(request: Dict = Body(...)):
    """
    基于提纲生成完整文章
    """
    session_id = request.get("session_id", "")
    outline_sections = request.get("outline_sections", [])
    target_word_count = request.get("target_word_count", 2000)

    if not session_id:
        return _error(code=400, msg="缺少 session_id")
    if not outline_sections:
        return _error(code=400, msg="缺少提纲内容")

    session = _get_session(session_id)
    if not session:
        return _error(code=404, msg="会话不存在")

    llm_config = _get_config("llm")
    base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = llm_config.get("api_key", "")
    model = llm_config.get("model", "deepseek-chat")
    timeout = llm_config.get("timeout", 120)

    mcp_summary = session.get("mcp_summary", "")
    persona_summary = session.get("persona_summary", "")
    persona_voice = session.get("persona_voice", {})
    direction = session.get("direction", "")
    framework = session.get("framework", "")

    # 处理 sections：可能是 dict 或 list
    if isinstance(outline_sections, dict):
        sections_list = list(outline_sections.values())
    elif isinstance(outline_sections, list):
        sections_list = outline_sections
    else:
        return _error(code=400, msg="提纲格式不正确")

    logger.info(f"文章生成 - sections类型: {type(outline_sections).__name__}, 数量: {len(sections_list)}")
    logger.info(f"文章生成 - session数据: direction={direction}, framework={framework}")

    sections_text = "\n".join([
        f"- {s.get('title', s.get('label', ''))}: {s.get('key_points', [])} (素材: {s.get('materials', {})})"
        for s in sections_list
    ])
    
    logger.info(f"文章生成 - 提纲内容: {sections_text[:200]}...")

    prompt = f"""你是一个专业内容写手。请基于以下提纲，撰写一篇完整的文章。

【写作方向】{direction}
【分析框架】{framework}
【目标字数】{target_word_count}字

【MCP 素材摘要】
{mcp_summary}

【作者身份定位】{persona_summary}
【作者表达范式】{json.dumps(persona_voice, ensure_ascii=False)}

【文章提纲】
{sections_text}

要求：
1. 语言风格：专业、实战导向、有洞察力
2. 内容结构：按照提纲的段落顺序撰写
3. 总字数控制在 {target_word_count} 字左右（±10%）
4. 每个段落：合理分配字数，包含具体案例和数据
5. 理论≤20%，实战≥80%
6. 段落之间自然衔接

返回 JSON 格式（不要 markdown 代码块）：
{{
  "title": "文章标题",
  "paragraphs": [
    {{
      "title": "段落标题",
      "content": "段落正文内容（包含具体案例、数据、分析）",
      "word_count": 字数
    }}
  ]
}}

请直接返回 JSON：
"""
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 8192,
                    "temperature": 0.3,
                    "seed": 42,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            content = content.strip()
            if content.startswith("```"):
                content = re.sub(r'^```(?:json)?\s*|\s*```$', '', content, flags=re.MULTILINE).strip()
            
            article = json.loads(content)
            
            return _success(article)
    except json.JSONDecodeError as e:
        logger.error(f"文章生成 JSON 解析失败: {e}")
        return _error(msg=f"文章生成失败，格式错误: {str(e)}")
    except Exception as e:
        logger.error(f"文章生成失败: {e}")
        return _error(msg=str(e))


# ===== P2: source_tag 硬约束 & 4 阶段 LLM Pipeline =====


@router.post("/api/content/validate_source_tags")
async def validate_content_source_tags(request: Dict = Body(...)):
    """
    P2: 验证内容的 source_tag 合规性
    
    请求体：
    {
        "content": "文章内容",
        "strict_mode": true  // 是否启用硬约束（无标签不渲染）
    }
    """
    content = request.get("content", "")
    strict_mode = request.get("strict_mode", True)
    
    if not content:
        return _error(code=400, msg="缺少 content 参数")
    
    try:
        processor = get_source_tag_processor()
        result = processor.process_full_article(content, strict_mode=strict_mode)
        
        return _success({
            "valid_count": result["valid_count"],
            "filtered_count": result["filtered_count"],
            "total_count": len(result["blocks"]),
            "rendered_html": result["rendered_html"],
            "source_tags": result["source_tags"],
            "blocks": [
                {
                    "source_tag": b.source_tag,
                    "is_valid": b.is_valid,
                    "warning": b.warning,
                    "rendered_content": b.rendered_content,
                    "raw_preview": b.raw_content[:100] + "..." if len(b.raw_content) > 100 else b.raw_content,
                }
                for b in result["blocks"]
            ],
        })
    except Exception as e:
        logger.error(f"source_tag 验证失败: {e}")
        return _error(msg=str(e))


@router.post("/api/content/pipeline/generate")
async def pipeline_generate_content(request: Dict = Body(...)):
    """
    P2: 4 阶段 LLM Pipeline 内容生成
    
    请求体：
    {
        "stage": "router|logic_editor|extractor|generator",
        "article_text": "待分析文本",
        "direction_list": [...],
        "edge_focus": "专注领域",
        "edge_avoid": "回避领域",
        "drive": "核心驱动",
        "filter_rule": "认知过滤",
        "value_standard": "价值标准",
        "audience_identity": "受众身份",
        "audience_pain_points": "受众痛点",
        "audience_empathy": "共情话术",
        "voice_style": "表达风格",
        "voice_format": "表达格式",
        "voice_ratio": "内容比例",
        "outline": "提纲",
        "structured_json": "结构化内容"
    }
    """
    from src.llm_pipeline import get_llm_pipeline
    
    stage = request.get("stage", "")
    if not stage:
        return _error(code=400, msg="缺少 stage 参数")
    
    try:
        llm_config = _get_config("llm")
        pipeline = get_llm_pipeline(llm_config)
        
        if stage == "router":
            result = await pipeline.call_router(
                article_text=request.get("article_text", ""),
                direction_list=request.get("direction_list", []),
                edge_focus=request.get("edge_focus", ""),
                edge_avoid=request.get("edge_avoid", ""),
            )
        elif stage == "logic_editor":
            result = await pipeline.call_logic_editor(
                outline=request.get("outline", ""),
                drive=request.get("drive", ""),
                filter_rule=request.get("filter_rule", ""),
                value_standard=request.get("value_standard", ""),
            )
        elif stage == "extractor":
            result = await pipeline.call_extractor(
                revised_outline=request.get("outline", ""),
                audience_identity=request.get("audience_identity", ""),
                audience_pain_points=request.get("audience_pain_points", ""),
                audience_empathy=request.get("audience_empathy", ""),
                value_standard=request.get("value_standard", ""),
            )
        elif stage == "generator":
            result = await pipeline.call_generator(
                structured_json=request.get("structured_json", ""),
                voice_style=request.get("voice_style", ""),
                voice_format=request.get("voice_format", ""),
                voice_ratio=request.get("voice_ratio", ""),
                audience_identity=request.get("audience_identity", ""),
                audience_pain_points=request.get("audience_pain_points", ""),
            )
        else:
            return _error(code=400, msg=f"未知的 stage: {stage}")
        
        return _success(result)
    except Exception as e:
        logger.error(f"Pipeline 调用失败: {e}")
        return _error(msg=str(e))


@router.post("/api/content/pipeline/full_workflow")
async def pipeline_full_workflow(request: Dict = Body(...)):
    """
    P2: 完整的 4 阶段 LLM Pipeline 工作流
    
    按顺序调用：Router → Logic Editor → Extractor → Generator
    
    请求体：
    {
        "article_text": "待分析文本",
        "direction_list": [...],
        "persona": {六维人设配置},
        "enable_source_validation": true
    }
    """
    from src.llm_pipeline import get_llm_pipeline
    
    try:
        llm_config = _get_config("llm")
        pipeline = get_llm_pipeline(llm_config)
        persona = request.get("persona", {})
        
        # 提取六维配置
        edge_focus = persona.get("edge", {}).get("focus", "AI 效率工具")
        edge_avoid = persona.get("edge", {}).get("avoid", "算法原理、技术史")
        drive = persona.get("why", "帮高净值人群节省时间")
        filter_rule = persona.get("filter", "问题→方案→避坑→收益")
        value_standard = persona.get("value", "读者看完能直接上手操作")
        audience_identity = persona.get("who", {}).get("identity", "企业主/高管")
        audience_pain_points = persona.get("who", {}).get("pain_points", "时间稀缺")
        audience_empathy = persona.get("who", {}).get("empathy", "我知道你每天要处理X件事")
        voice_style = persona.get("voice", {}).get("style", "理性务实")
        voice_format = persona.get("voice", {}).get("format", "短句")
        voice_ratio = persona.get("voice", {}).get("ratio", "理论≤20%，实战≥80%")
        
        workflow_result = {
            "stages": {},
            "total_llm_calls": 0,
        }
        
        # Stage 1: Router
        logger.info("[Pipeline] Stage 1: Router - 方向推荐")
        router_result = await pipeline.call_router(
            article_text=request.get("article_text", ""),
            direction_list=request.get("direction_list", []),
            edge_focus=edge_focus,
            edge_avoid=edge_avoid,
        )
        workflow_result["stages"]["router"] = router_result
        workflow_result["total_llm_calls"] += 1
        
        # Stage 2: Logic Editor
        logger.info("[Pipeline] Stage 2: Logic Editor - 框架推荐")
        logic_result = await pipeline.call_logic_editor(
            outline=router_result.get("content", ""),
            drive=drive,
            filter_rule=filter_rule,
            value_standard=value_standard,
        )
        workflow_result["stages"]["logic_editor"] = logic_result
        workflow_result["total_llm_calls"] += 1
        
        # Stage 3: Extractor
        logger.info("[Pipeline] Stage 3: Extractor - 内容萃取")
        extract_result = await pipeline.call_extractor(
            revised_outline=logic_result.get("content", ""),
            audience_identity=audience_identity,
            audience_pain_points=audience_pain_points,
            audience_empathy=audience_empathy,
            value_standard=value_standard,
        )
        workflow_result["stages"]["extractor"] = extract_result
        workflow_result["total_llm_calls"] += 1
        
        # Stage 4: Generator
        logger.info("[Pipeline] Stage 4: Generator - 内容生成")
        generate_result = await pipeline.call_generator(
            structured_json=extract_result.get("content", ""),
            voice_style=voice_style,
            voice_format=voice_format,
            voice_ratio=voice_ratio,
            audience_identity=audience_identity,
            audience_pain_points=audience_pain_points,
        )
        workflow_result["stages"]["generator"] = generate_result
        workflow_result["total_llm_calls"] += 1
        
        # P2: source_tag 验证
        enable_validation = request.get("enable_source_validation", True)
        if enable_validation:
            logger.info("[Pipeline] source_tag 验证")
            processor = get_source_tag_processor()
            content = generate_result.get("content", "")
            validation_result = processor.process_full_article(content, strict_mode=True)
            workflow_result["source_validation"] = {
                "valid_count": validation_result["valid_count"],
                "filtered_count": validation_result["filtered_count"],
                "rendered_html": validation_result["rendered_html"],
                "source_tags": validation_result["source_tags"],
            }
        
        return _success(workflow_result)
    except Exception as e:
        logger.error(f"Pipeline 工作流失败: {e}")
        return _error(msg=str(e))
