"""API 接口定义 - ArchGen v2.0"""

import os
import sys
import uuid
import json
import logging
import re
import asyncio
import threading
import httpx
import ipaddress
from pathlib import Path
from typing import Optional, Dict, List
from urllib.parse import urlparse
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Body, Depends, Header
from config.model_config import get_model_for_scene, get_default_max_tokens, V4_FLASH, V4_PRO
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse


def _v4_model(scene: str) -> str:
    """
    V4 迁移：统一模型选择入口。
    替代旧代码中的 V4_FLASH
    
    用法：
        model = _v4_model("场景名称")   # 返回 "deepseek-v4-pro" 或 "deepseek-v4-flash"
    """
    return get_model_for_scene(scene)

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


def _error_internal(e: Exception = None, default_msg="内部错误，请重试"):
    """安全错误响应：log 完整堆栈，返回通用消息（不泄露内部细节）"""
    if e:
        logger.error(f"内部错误: {e}", exc_info=True)
    return _error(msg=default_msg)


# ===== 安全世界工具（路径遍历 / SSRF / 认证） =====

# LLM base_url 主机白名单（防 SSRF）— 仅允许公网 LLM 服务
_ALLOWED_LLM_HOSTS = {"api.deepseek.com", "api.openai.com"}

# 敏感文件扩展名黑名单（即便在白名单目录内也禁止读取/写入）
_FORBIDDEN_EXTENSIONS = {".py", ".pyc", ".so", ".dll", ".exe", ".sh", ".bash",
                         ".env", ".pem", ".key", ".crt", ".p12", ".pfx",
                         ".yaml", ".yml", ".conf", ".ini", ".toml"}


def _validate_path_within_base(file_path: str, base_dir) -> bool:
    """检查 file_path 解析后是否在 base_dir 内（防路径遍历）。

    file_path 可以是相对路径（相对于 base_dir）或绝对路径。
    含 .. 跨目录跳转、符号链接逃逸均会返回 False。
    """
    try:
        base = Path(base_dir).resolve()
        p = Path(file_path)
        target = p.resolve() if p.is_absolute() else (base / file_path).resolve()
        return target == base or base in target.parents
    except Exception:
        return False


def _validate_path_in_allowed_bases(file_path: str, allowed_bases: list) -> bool:
    """检查绝对路径是否在任一允许的基础目录内。"""
    try:
        target = Path(file_path).resolve()
        for base in allowed_bases:
            base_resolved = Path(base).resolve()
            if target == base_resolved or base_resolved in target.parents:
                return True
        return False
    except Exception:
        return False


def _has_forbidden_extension(file_path: str) -> bool:
    """检查文件扩展名是否在敏感黑名单内。"""
    return Path(file_path).suffix.lower() in _FORBIDDEN_EXTENSIONS


def _get_allowed_read_bases() -> list:
    """获取允许读取文件的基础目录白名单。"""
    bases = []
    kb_cfg = _get_config("knowledge_base")
    kb_root = kb_cfg.get("root_path", "knowledge_base")
    bases.append(kb_root)
    storage_cfg = _get_config("storage")
    bases.append(storage_cfg.get("output_dir", "output"))
    bases.append(Path(__file__).parent / "config")
    bases.append(Path(__file__).parent / "knowledge_base")
    # persona 文件所在目录（用户配置）
    try:
        persona_path = _get_persona_path()
        if persona_path:
            bases.append(Path(persona_path).parent)
    except Exception:
        pass
    return bases


# 敏感系统目录前缀（/api/folders/verify 和 /api/folders/list 禁止访问）
_SENSITIVE_SYSTEM_PREFIXES = (
    "/etc", "/root", "/var", "/proc", "/sys", "/dev", "/boot", "/sbin",
    "/bin", "/usr/sbin", "/usr/bin", "/lib", "/lib64", "/run", "/srv",
    "/.ssh", "/.gnupg",
)


def _is_sensitive_system_path(path_str: str) -> bool:
    """检查路径是否为敏感系统目录（用于 folder browse 端点的轻量防护）。"""
    try:
        resolved = str(Path(path_str).resolve())
        for prefix in _SENSITIVE_SYSTEM_PREFIXES:
            if resolved == prefix or resolved.startswith(prefix + "/"):
                return True
        return False
    except Exception:
        return True


def _validate_llm_base_url(base_url: str) -> bool:
    """校验 LLM base_url 防 SSRF。

    白名单优先：api.deepseek.com, api.openai.com
    黑名单：localhost / 127.0.0.0/8 / 10.0.0.0/8 / 172.16.0.0/12 / 192.168.0.0/16 / 169.254.0.0/16 / ::1
    其他公网 host 默认拒绝（严格模式）。
    """
    if not base_url:
        return False
    try:
        parsed = urlparse(base_url)
        host = (parsed.hostname or "").lower()
        if not host:
            return False
        if host in _ALLOWED_LLM_HOSTS:
            return True
        # 检查是否为 IP
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        except ValueError:
            if host in {"localhost", "localhost.localdomain"}:
                return False
        # 默认拒绝（白名单严格模式）
        return False
    except Exception:
        return False


def _get_app_api_key() -> str:
    """读取服务间认证 API Key。未配置则返回空（关闭认证，向后兼容）。"""
    cfg = _get_config("app")
    return cfg.get("api_key", "") or os.environ.get("ARCHGEN_API_KEY", "")


def verify_api_key(x_api_key: str = Header(default="", alias="X-API-Key")):
    """FastAPI 依赖：校验 X-API-Key 请求头。

    未配置 ARCHGEN_API_KEY 时跳过认证（默认开放，向后兼容）。
    配置后所有加了 Depends(verify_api_key) 的端点都需要带 X-API-Key 头。
    """
    expected = _get_app_api_key()
    if not expected:
        return True
    if x_api_key and x_api_key == expected:
        return True
    raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


def _apply_infographic_hard_constraints(html: str) -> str:
    """零容忍约束硬替换：强制修正 LLM 不遵守 Prompt 的布局参数。

    1. 内容区高度必须为 h-[calc(100%-100px)]，任何其他数值一律归一化
    2. 序号徽章统一为 w-3.5 h-3.5 rounded-full（禁止 w-5/w-4/w-3）
    """
    # 用 regex 匹配任意数值的 h-[calc(100%-Npx)]，统一替换为 100px
    html = re.sub(r'h-\[calc\(100%-\d+px\)\]', 'h-[calc(100%-100px)]', html)
    # 徽章尺寸归一化
    html = re.sub(r'w-[345]\s+h-[345]\s+rounded-full', 'w-3.5 h-3.5 rounded-full', html)
    return html


def _extract_json(text: str) -> str:
    """从 LLM 回复中提取 JSON，兼容各种包裹格式。

    LLM 有时会在 JSON 前后附加说明文字（如"分析结果如下："），
    或使用 markdown 代码块包裹（```json ... ```）。
    此函数从文本中找到第一个 { 和最后一个 }，截取中间的 JSON 部分。
    """
    # 先尝试简单清理
    cleaned = text.strip()
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    # 如果清理后就是正常 JSON，直接返回
    if cleaned.startswith("{") or cleaned.startswith("["):
        return cleaned

    # 从文本中提取最外层 { } 或 [ ] 部分
    for prefix, suffix in [("{", "}"), ("[", "]")]:
        start = cleaned.find(prefix)
        end = cleaned.rfind(suffix)
        if start != -1 and end != -1 and end > start:
            return cleaned[start:end + 1]

    # 兜底：返回清理后的原文
    return cleaned


def _format_prompt_text(messages: list) -> str:
    """将 messages 数组格式化为人类可读的文本（保留原始换行和段落）。
    用于 AI 思考日志中展示完整 Prompt，替代 json.dumps 的转义显示问题。
    """
    role_labels = {"system": "SYSTEM", "user": "USER", "assistant": "ASSISTANT"}
    parts = []
    for i, m in enumerate(messages):
        role = m.get("role", "unknown").lower()
        content = m.get("content", "")
        label = role_labels.get(role, role.upper())
        if label == "ASSISTANT" and not content.strip():
            continue  # 跳过空的 assistant 占位
        parts.append(f"{'─' * 60}")
        parts.append(f"[{label}]")
        parts.append(f"{'─' * 60}")
        parts.append(content.strip())
        parts.append("")
    return "\n".join(parts)


def _log_llm_call_legacy(
    session_id: str,
    call_id: str,
    call_name: str,
    messages: list,
    result: str = None,
    error: str = None,
    model: str = None,
    temperature: float = None,
    duration: float = None,
    phase: str = "其他",
    thinking_chain: list = None,
):
    """
    为老式同步 LLM 调用（非 stream_llm_call）记录思考日志。
    在已有 LLM 调用的端点末尾调用此函数，无需重构代码。
    """
    import time
    llm_config = _get_config("llm")
    session = _get_session(session_id)
    if not session:
        return
    
    if "thinking_logs" not in session:
        session["thinking_logs"] = []
    
    if thinking_chain is None:
        thinking_chain = [
            {"step": 1, "action": "执行分析任务", "reason": f"{call_name}", "result": result[:200] if result else ""}
        ]
    
    log = {
        "call_id": call_id,
        "call_name": call_name,
        "phase": phase,
        "session_id": session_id,
        "start_time": time.time() - (duration or 0),
        "end_time": time.time(),
        "duration": duration or 0,
        "model": model or V4_FLASH,
        "temperature": temperature or 0.7,
        "status": "success" if not error else "failed",
        "full_prompt": _format_prompt_text(messages)[:8000],
        "final_output": result[:5000] if result else None,
        "result": result[:3000] if result else None,
        "error": error,
        "thinking_chain": thinking_chain,
        "log_id": f"log_{int(time.time() * 1000)}"
    }
    session["thinking_logs"].append(log)
    if len(session["thinking_logs"]) > 50:
        session["thinking_logs"] = session["thinking_logs"][-50:]


def _log_process_step(
    session_id: str,
    call_name: str,
    phase: str,
    steps: list,
    output: str = None,
    duration: float = None,
):
    """
    为非 LLM 的数据处理步骤记录思考日志。
    用于展示扫描、分类、筛选等中间过程。
    
    steps: [{"action": "...", "reason": "...", "result": "..."}, ...]
    """
    import time
    session = _get_session(session_id)
    if not session:
        return
    
    if "thinking_logs" not in session:
        session["thinking_logs"] = []
    
    log = {
        "call_id": f"process_{int(time.time() * 1000)}",
        "call_name": call_name,
        "phase": phase,
        "session_id": session_id,
        "start_time": time.time() - (duration or 0),
        "end_time": time.time(),
        "duration": duration or 0,
        "model": "—",
        "temperature": "—",
        "status": "success",
        "thinking_chain": steps,
        "result": output[:2000] if output else None,
        "log_id": f"log_{int(time.time() * 1000)}"
    }
    session["thinking_logs"].append(log)
    if len(session["thinking_logs"]) > 50:
        session["thinking_logs"] = session["thinking_logs"][-50:]


def _write_handoff_log(session_id: str, from_step: str, to_step: str, detail: str):
    """记录步骤间的手递手传递信息"""
    import time as _time
    session = _get_session(session_id)
    if not session:
        return
    if "thinking_logs" not in session:
        session["thinking_logs"] = []
    # 找出当前方向名
    topic_name = ""
    for t in session.get("mcp_topics", []):
        topic_name = t.get("name", "")
        break
    session["thinking_logs"].append({
        "call_id": f"handoff_{from_step}→{to_step}",
        "call_name": f"[Handoff] {from_step} → {to_step}",
        "phase": "handoff",
        "session_id": session_id,
        "start_time": _time.time(),
        "end_time": _time.time(),
        "duration": 0,
        "model": "system",
        "temperature": 0,
        "status": "success",
        "full_prompt": "",
        "final_output": detail,
        "result": f"传递信息: {detail}",
        "thinking_chain": [{
            "step": 1,
            "action": f"手递手: {from_step} → {to_step}",
            "reason": f"方向: {topic_name}",
            "result": detail,
        }],
        "log_id": f"log_{int(_time.time() * 1000)}"
    })


async def _call_llm(
    session_id: str = None,
    call_name: str = "",
    messages: list = None,
    model: str = None,
    temperature: float = None,
    max_tokens: int = None,
    timeout: float = None,
    seed: int = None,
    base_url: str = None,
    api_key: str = None,
    phase: str = "其他",
):
    """
    统一 LLM 调用入口。自动选模型、记录日志。

    session_id 支持两种传入方式：
    - str: 通过 _get_session(session_id) 获取 session dict
    - None: 不记录日志（独立模块无 session 场景）
    
    模型选择: 根据 call_name 从 SCENE_MODEL_MAP 查（默认 Flash）
    日志: 自动写入 session["thinking_logs"]

    用法：
        result = await _call_llm(
            session_id=session_id,
            call_name="方向检测",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        content = result["choices"][0]["message"]["content"]
    """
    import time as _time
    import httpx as _httpx
    
    llm_config = _get_config("llm")
    start_time = _time.time()
    call_id = f"{call_name}_{int(start_time * 1000)}"
    
    if not base_url:
        base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    if not api_key:
        api_key = llm_config.get("api_key", "")
    # SSRF 防护：校验 base_url 是否在白名单内
    if not _validate_llm_base_url(base_url):
        logger.error(f"[Security] LLM base_url 校验失败，疑似 SSRF: {base_url}")
        raise HTTPException(status_code=503, detail="LLM 服务地址不可用")
    if not model:
        # V4 迁移：根据业务场景自动选择 Pro / Flash
        model = get_model_for_scene(call_name)
    
    # max_tokens 智能调整:
    # - 调用方未指定（None）→ 自动: Flash=2048 / Pro=8192
    # - 调用方显式指定 → 尊重调用方
    if max_tokens is None:
        max_tokens = 8192 if model == V4_PRO else 2048
    if timeout is None:
        timeout = llm_config.get("timeout", 60)
    
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if seed is not None:
        payload["seed"] = seed
    
    try:
        async with _httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            response.raise_for_status()
            try:
                result = response.json()
            except Exception as json_err:
                raw_body = response.text[:500] if hasattr(response, 'text') else '(无法读取响应体)'
                raise Exception(f"LLM 返回非 JSON 响应: {type(json_err).__name__}: {json_err} | 原始响应: {raw_body}")
        
        elapsed = _time.time() - start_time
        parsed_content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # 记录成功日志
        session = _get_session(session_id) if isinstance(session_id, str) and session_id else None
        if session:
            if "thinking_logs" not in session:
                session["thinking_logs"] = []
            
            # 提取 token 用量
            usage = result.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            
            # 构建思考链（带 Token 消耗和模型信息）
            full_prompt_text = _format_prompt_text(messages)
            thinking_chain = [
                {"step": 1, "action": "构造提示词", 
                 "reason": f"将知识库分析结果、作者身份定位和选题要求组织成完整 Prompt",
                 "result": f"提示词总长 {len(full_prompt_text)} 字符（约 {len(full_prompt_text) // 2} 个中文字符）"},
                {"step": 2, "action": "调用大语言模型",
                 "reason": f"模型：{model}，推理用时 {elapsed:.1f} 秒",
                 "result": f"消耗 Token：输入 {prompt_tokens} + 输出 {completion_tokens} = 共 {total_tokens} tokens"},
                {"step": 3, "action": "解析推荐结果",
                 "reason": "从 LLM 返回的 JSON 中提取选题方向、覆盖度评分和缺失分析",
                 "result": f"输出内容 {len(parsed_content)} 字符"},
            ]
            
            session["thinking_logs"].append({
                "call_id": call_id,
                "call_name": call_name,
                "phase": phase,
                "session_id": session_id,
                "start_time": start_time,
                "end_time": _time.time(),
                "duration": elapsed,
                "model": model,
                "temperature": temperature if temperature is not None else 0.7,
                "status": "success",
                "full_prompt": full_prompt_text[:8000],
                "final_output": parsed_content[:5000],
                "result": f"Prompt {len(full_prompt_text)} 字符 → LLM 推理 {elapsed:.1f}s → 输出 {len(parsed_content)} 字符 ({total_tokens} tokens)",
                "thinking_chain": thinking_chain,
                "log_id": f"log_{int(_time.time() * 1000)}"
            })
            if len(session["thinking_logs"]) > 50:
                session["thinking_logs"] = session["thinking_logs"][-50:]
        
        return result
    except Exception as e:
        elapsed = _time.time() - start_time
        
        # 记录失败日志
        session = _get_session(session_id) if isinstance(session_id, str) and session_id else None
        if session:
            if "thinking_logs" not in session:
                session["thinking_logs"] = []
            session["thinking_logs"].append({
                "call_id": call_id,
                "call_name": call_name,
                "phase": phase,
                "session_id": session_id,
                "start_time": start_time,
                "end_time": _time.time(),
                "duration": elapsed,
                "model": model,
                "temperature": temperature if temperature is not None else 0.7,
                "status": "failed",
                "full_prompt": _format_prompt_text(messages)[:8000],
                "error": str(e)[:2000],
                "thinking_chain": [
                    {"step": 1, "action": "执行分析任务", "reason": call_name, "result": f"失败: {str(e)[:200]}"}
                ],
                "log_id": f"log_{int(_time.time() * 1000)}"
            })
            if len(session["thinking_logs"]) > 50:
                session["thinking_logs"] = session["thinking_logs"][-50:]
        raise


async def stream_llm_call(
    session_id: str,
    call_id: str,
    call_name: str,
    messages: list,
    model: str = None,
    temperature: float = 0.7,
    require_thinking_chain: bool = True
) -> dict:
    """
    统一流式LLM调用入口：自动记录思考日志 + 流式输出
    
    Args:
        session_id: 会话ID
        call_id: 唯一调用标识（如"editpanel_analyze_risk"）
        call_name: 显示名称（如"风险槽位核心观点分析"）
        messages: Prompt列表（OpenAI格式）
        model: 模型名，不传则用配置的默认模型
        temperature: 温度参数
        require_thinking_chain: 是否强制在Prompt末尾加思考链输出要求
    
    Returns:
        {
            "thinking_chain": [...],  // 思考步骤
            "result": "最终结果",      // 最终输出
            "log_id": "日志ID"        // 用于前端关联
        }
    """
    import time
    
    start_time = time.time()
    llm_config = _get_config("llm")
    base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = llm_config.get("api_key", "")
    default_model = V4_FLASH
    use_model = model or default_model
    
    # 构造思考日志
    thinking_log = {
        "call_id": call_id,
        "call_name": call_name,
        "session_id": session_id,
        "start_time": start_time,
        "model": use_model,
        "temperature": temperature,
        "status": "running",
        "full_prompt": _format_prompt_text(messages)[:5000],  # 限制长度
        "thinking_chain": [],
        "final_output": None,
        "error": None
    }
    
    try:
        if not api_key:
            raise ValueError("LLM API Key 未配置")
        
        # 如果需要思考链，在最后一条message后加格式要求
        if require_thinking_chain and messages:
            thinking_requirement = """
【输出格式要求】
请先输出你的思考过程，再输出最终结果，严格按以下JSON格式返回，不要加markdown代码块标记：
{
  "thinking_chain": [
    { "step": 1, "action": "你做了什么分析", "reason": "基于什么素材/信息", "result": "得出了什么结论" }
  ],
  "result": "最终输出内容"
}
"""
            last_msg = messages[-1]
            if isinstance(last_msg, dict) and "content" in last_msg:
                messages = messages[:-1] + [
                    {**last_msg, "content": last_msg["content"] + "\n\n" + thinking_requirement}
                ]
        
        # 调用LLM（流式）
        async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10)) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": use_model,
                    "messages": messages,
                    "max_tokens": 4096,
                    "temperature": temperature,
                    "stream": True,
                },
            )
            response.raise_for_status()
            
            # 收集流式输出
            full_text = ""
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if delta:
                        full_text += delta
                except:
                    pass
        
        # 解析结果（尝试解析thinking_chain和result）
        thinking_log["final_output"] = full_text
        try:
            # 先尝试直接解析JSON
            parsed = json.loads(full_text.strip())
            if isinstance(parsed, dict):
                if "thinking_chain" in parsed:
                    thinking_log["thinking_chain"] = parsed["thinking_chain"]
                if "result" in parsed:
                    thinking_log["result"] = parsed["result"]
                else:
                    thinking_log["result"] = full_text
            else:
                thinking_log["result"] = full_text
        except:
            # JSON解析失败，尝试找 { ... }
            try:
                start = full_text.find('{')
                end = full_text.rfind('}')
                if start >= 0 and end > start:
                    parsed = json.loads(full_text[start:end+1])
                    if isinstance(parsed, dict):
                        if "thinking_chain" in parsed:
                            thinking_log["thinking_chain"] = parsed["thinking_chain"]
                        if "result" in parsed:
                            thinking_log["result"] = parsed["result"]
                        else:
                            thinking_log["result"] = full_text
                    else:
                        thinking_log["result"] = full_text
                else:
                    thinking_log["result"] = full_text
            except:
                thinking_log["result"] = full_text
        
        thinking_log["status"] = "success"
        thinking_log["end_time"] = time.time()
        thinking_log["duration"] = thinking_log["end_time"] - start_time
        
        # 存储到session
        session = _get_session(session_id)
        if session:
            if "thinking_logs" not in session:
                session["thinking_logs"] = []
            log_id = f"log_{int(time.time() * 1000)}"
            thinking_log["log_id"] = log_id
            session["thinking_logs"].append(thinking_log)
            # 保留最近50条
            if len(session["thinking_logs"]) > 50:
                session["thinking_logs"] = session["thinking_logs"][-50:]
        
        return {
            "thinking_chain": thinking_log.get("thinking_chain", []),
            "result": thinking_log.get("result", thinking_log["final_output"]),
            "final_output": thinking_log["final_output"],
            "log_id": thinking_log.get("log_id", ""),
            "duration": thinking_log.get("duration", 0)
        }
    
    except Exception as e:
        thinking_log["status"] = "failed"
        thinking_log["error"] = str(e)
        thinking_log["end_time"] = time.time()
        thinking_log["duration"] = thinking_log["end_time"] - start_time
        
        # 存储错误日志
        session = _get_session(session_id)
        if session:
            if "thinking_logs" not in session:
                session["thinking_logs"] = []
            log_id = f"log_{int(time.time() * 1000)}"
            thinking_log["log_id"] = log_id
            session["thinking_logs"].append(thinking_log)
        
        logger.error(f"[stream_llm_call] {call_id} 失败: {e}")
        raise


def _try_repair_json(raw: str) -> str:
    """尝试修复截断的 JSON：找到最后一个完整对象/数组的闭合位置"""
    import re
    # 去掉尾部不完整内容，从后往前找最后一个 }
    depth = 0
    last_complete = len(raw)
    for i in range(len(raw) - 1, -1, -1):
        c = raw[i]
        if c == '}':
            depth += 1
        elif c == '{':
            depth -= 1
        if depth == 0 and c in ('}', ']'):
            # 找到最后一个完整的顶级闭合
            # 但这里应该找最外层的闭合
            pass
    # 简单策略：修剪尾部，找到最后一个 } 或 ]，补齐
    stripped = raw.rstrip()
    # 如果以 ] 结尾且前面有 [，说明数组完整
    if stripped.endswith(']'):
        return stripped
    # 尝试补一个 } 或 ] 
    # 先看开头是 { 还是 [
    first_char = raw.strip()[0] if raw.strip() else '{'
    # 找最后一个完整 token 的位置
    # 简单方法：从末尾找最后一个 }
    last_brace = raw.rfind('}')
    last_bracket = raw.rfind(']')
    if last_brace > last_bracket:
        return raw[:last_brace + 1]
    elif last_bracket > -1:
        return raw[:last_bracket + 1]
    # 都没有，返回空对象
    return '{}'


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
        return _error_internal(e)


# ===== Phase 1.5: 向量检索系统（MiniLM + NumPy 点积） =====

import numpy as np
from numpy.linalg import norm

# 向量索引：按文件夹路径 hash 分库存储，支持多知识库
#   _VECTORS_MAP: {folder_hash: {"vectors": np.ndarray, "meta": list}}
#   当前活跃索引由 load_vectors(folders) 或 ensure_index_load(folders) 设置
_VECTORS = None       # shape: (N, 384) — 当前活跃索引
_VECTOR_META = None   # List[Dict] — 当前活跃元数据
_VECTORS_MAP = {}     # {folder_hash: {"vectors": ..., "meta": ...}}
_ACTIVE_FOLDER_HASH = None
_EMBED_MODEL = None   # SentenceTransformer 缓存

VECTOR_ROOT = os.path.join(os.path.dirname(__file__), "vector_index")


def _get_folder_hash(dir_path: str) -> str:
    """对文件夹路径做 hash，作为向量索引子目录名"""
    import hashlib
    return hashlib.md5(os.path.abspath(dir_path).encode()).hexdigest()[:12]


def _get_vector_dir(folders: list) -> str:
    """根据文件夹列表计算索引存储目录"""
    if not folders:
        return os.path.join(VECTOR_ROOT, "default")
    h = _get_folder_hash(folders[0])
    return os.path.join(VECTOR_ROOT, h)


def _set_active_index(folder_hash: str):
    """切换到指定 hash 对应的索引"""
    global _VECTORS, _VECTOR_META, _ACTIVE_FOLDER_HASH
    entry = _VECTORS_MAP.get(folder_hash)
    if entry:
        _VECTORS = entry["vectors"]
        _VECTOR_META = entry["meta"]
        _ACTIVE_FOLDER_HASH = folder_hash
    else:
        _VECTORS = None
        _VECTOR_META = None
        _ACTIVE_FOLDER_HASH = None


def _load_vector_metadata(meta_path: str):
    """安全加载向量索引元数据。

    优先读 metadata.json（安全）；如果只有 metadata.pkl（旧索引），
    则用 pickle.load 但仅限本地构建产物（不含用户输入，风险可接受）。
    新版 build_index.py 默认产出 JSON。
    """
    json_path = meta_path
    if json_path.endswith(".pkl"):
        json_path = json_path[:-4] + ".json"
    # 优先 JSON
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # 向后兼容：读取旧 pkl 文件
    if os.path.exists(meta_path) and meta_path.endswith(".pkl"):
        logger.warning(f"[Security] 加载旧版 pickle 元数据（建议重新构建索引以转 JSON）: {meta_path}")
        import pickle
        with open(meta_path, "rb") as f:
            return pickle.load(f)
    raise FileNotFoundError(f"元数据文件不存在: {meta_path}")


def load_vectors(folders=None):
    """加载向量索引（启动时或选题时调用）。

    folders: 用户选择的文件夹列表，用于定位对应索引。
             为 None 时尝试加载 vector_index/default/。
    """
    vec_dir = _get_vector_dir(folders) if folders else os.path.join(VECTOR_ROOT, "default")
    h = os.path.basename(vec_dir)

    if h in _VECTORS_MAP:
        _set_active_index(h)
        return

    vec_path = os.path.join(vec_dir, "vectors.npy")
    meta_pkl = os.path.join(vec_dir, "metadata.pkl")
    meta_json = os.path.join(vec_dir, "metadata.json")
    meta_path = meta_json if os.path.exists(meta_json) else meta_pkl

    if os.path.exists(vec_path) and os.path.exists(meta_path):
        try:
            vecs = np.load(vec_path)
            meta = _load_vector_metadata(meta_path)
            _VECTORS_MAP[h] = {"vectors": vecs, "meta": meta}
            _set_active_index(h)
            logger.info(f"[Vector] 加载 {h}: {vecs.shape[0]} vectors, dim={vecs.shape[1]}")
        except Exception as e:
            logger.warning(f"[Vector] 加载失败 {h}: {e}")
    else:
        logger.warning(f"[Vector] 索引未找到 ({vec_dir})，运行 python build_index.py --md-dir=<文件夹> 构建")


def ensure_index_load(folders: list):
    """确保索引已加载；若索引不存在则自动后台构建（阻塞等待最多 300 秒）。

    选题管道在 Step 3 前调用此函数，保证向量搜索有数据。
    """
    import subprocess

    vec_dir = _get_vector_dir(folders)
    h = os.path.basename(vec_dir)
    vec_path = os.path.join(vec_dir, "vectors.npy")

    # 已加载 → 直接返回
    if h in _VECTORS_MAP:
        _set_active_index(h)
        return

    if os.path.exists(vec_path):
        load_vectors(folders)
        return

    # 索引不存在 → 自动构建
    if not folders:
        logger.warning("[Vector] 无 folders，跳过索引构建")
        return

    md_dir = folders[0]
    if not os.path.isdir(md_dir):
        logger.warning(f"[Vector] 目录不存在，跳过索引构建: {md_dir}")
        return

    logger.info(f"[Vector] 首次使用此文件夹，正在构建索引: {md_dir}")
    build_script = os.path.join(os.path.dirname(__file__), "build_index.py")
    try:
        result = subprocess.run(
            [sys.executable, build_script, "--md-dir", md_dir, "--output-dir", vec_dir],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0:
            logger.info(f"[Vector] 索引构建完成: {vec_dir}")
            vecs = np.load(vec_path)
            meta_path = os.path.join(vec_dir, "metadata.json")
            meta = _load_vector_metadata(meta_path)
            _VECTORS_MAP[h] = {"vectors": vecs, "meta": meta}
            _set_active_index(h)
            logger.info(f"[Vector] 已加载: {vecs.shape[0]} vectors")
        else:
            logger.error(f"[Vector] 索引构建失败: {result.stderr[:500]}")
    except subprocess.TimeoutExpired:
        logger.error("[Vector] 索引构建超时（300s）")
    except Exception as e:
        logger.error(f"[Vector] 索引构建异常: {e}")


_embed_model_lock = threading.Lock()

def get_embedding_model():
    """懒加载 SentenceTransformer（全局缓存，线程安全）
    
    双重检查锁 + 超时降级：如果模型正在被其他线程加载，等待最多 10 秒后降级返回 None
    """
    global _EMBED_MODEL
    if _EMBED_MODEL is not None:
        return _EMBED_MODEL
    
    acquired = _embed_model_lock.acquire(blocking=False)
    if not acquired:
        logger.info("[Vector] 模型正在后台加载中，本次跳过向量召回")
        return None
    
    try:
        if _EMBED_MODEL is not None:  # 双重检查
            return _EMBED_MODEL
        try:
            from sentence_transformers import SentenceTransformer
            _EMBED_MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", local_files_only=True)
            logger.info(f"[Vector] MiniLM 模型加载完成")
        except ImportError:
            logger.error("[Vector] sentence-transformers 未安装，运行: pip install sentence-transformers")
            return None
    finally:
        _embed_model_lock.release()
    return _EMBED_MODEL


def is_model_ready():
    """检查 MiniLM 模型是否已就绪（非阻塞）"""
    return _EMBED_MODEL is not None


def search_similar(query_vector: np.ndarray, top_k: int = 5) -> list:
    """
    在内存向量中余弦召回
    
    Returns: [{"meta": {...}, "score": float}, ...] 降序
    """
    if _VECTORS is None or _VECTOR_META is None:
        return []
    
    q = query_vector / (norm(query_vector) + 1e-8)
    vecs_n = _VECTORS / (norm(_VECTORS, axis=1, keepdims=True) + 1e-8)
    sims = np.dot(vecs_n, q)  # (N,)
    
    top_idx = np.argsort(sims)[-top_k:][::-1]
    return [
        {"meta": _VECTOR_META[i], "score": float(sims[i])}
        for i in top_idx
    ]


async def recall_with_dedup(representatives: list, top_k: int = 5) -> list:
    """
    混合检索：用代表文件的语义向量，在全量库中召回相似旧文 + 去重
    
    representatives: [{"name": ..., "path": ..., "_full_content": ...}, ...]
    返回: [{"name": ..., "path": ..., "content": ..., "score": float}, ...] 去重后
    """
    if _VECTORS is None or not _VECTOR_META:
        logger.warning("[Vector] 索引为空，跳过向量召回")
        return []
    
    model = get_embedding_model()
    if model is None:
        logger.warning("[Vector] 模型未加载，跳过向量召回")
        return []
    
    # 构造 query：拼接代表文件的 Front Matter + 首段
    query_parts = []
    for r in representatives[:5]:  # 最多用 5 篇构造 query
        content = r.get("_full_content", "")
        if content:
            fm = _extract_front_matter(content)
            if fm:
                query_parts.append(fm)
            first_para = content[:200] if content else r.get("name", "")
            query_parts.append(first_para)
    
    query_text = " ".join(query_parts)[:1000]  # 限制查询长度
    
    if not query_text.strip():
        return []
    
    # 编码 query
    q_vec = model.encode(query_text, convert_to_numpy=True)
    
    # 余弦召回
    recalled = search_similar(q_vec, top_k=top_k)
    
    if not recalled:
        return []
    
    # 去重：按 abs_path 比对
    rep_paths = {r.get("path", r.get("abs_path", "")) for r in representatives}
    rep_names = {r.get("name", "") for r in representatives}
    
    deduped = []
    excluded = []
    for r in recalled:
        meta = r["meta"]
        if meta["abs_path"] in rep_paths or meta["path"] in rep_names:
            excluded.append({
                "name": meta["path"],
                "score": r["score"],
                "reason": "已在密度精选代表中",
            })
            continue
        # 读取文件内容
        try:
            content = ""
            with open(meta["abs_path"], "r", encoding="utf-8") as f:
                content = f.read()
            deduped.append({
                "name": meta["path"],
                "path": meta["abs_path"],
                "abs_path": meta["abs_path"],
                "_full_content": content,
                "_density": calc_heuristic_density(content),
                "_recall_score": r["score"],
                "_source": "vector_recall",
            })
        except Exception as e:
            logger.warning(f"[Vector] 读取召回文件失败: {meta['abs_path']}: {e}")
            excluded.append({
                "name": meta["path"],
                "score": r["score"],
                "reason": f"文件读取失败: {e}",
            })
    
    logger.info(f"[Vector] 召回 {len(recalled)} 篇，去重后 {len(deduped)} 篇，排除 {len(excluded)} 篇")
    return {"recalled": deduped[:top_k], "excluded": excluded, "total_searched": len(recalled)}


def get_vector_index_info() -> Dict:
    """获取向量索引状态信息"""
    active_dir = os.path.join(VECTOR_ROOT, _ACTIVE_FOLDER_HASH) if _ACTIVE_FOLDER_HASH else os.path.join(VECTOR_ROOT, "default")
    if _VECTORS is not None and _VECTOR_META is not None:
        return {
            "loaded": True,
            "total_vectors": _VECTORS.shape[0],
            "dimension": int(_VECTORS.shape[1]),
            "directory": active_dir,
            "active_folder_hash": _ACTIVE_FOLDER_HASH,
        }
    return {"loaded": False, "directory": active_dir}


# ============================================================
# 选题管道：证据检测 + 素材评分 + 文档格式化
# ============================================================

def detect_evidence_in_content(content: str, fm: dict) -> tuple:
    """
    扫描正文内容，检测四种证据类型的出现次数。
    不依赖 Front Matter 标签，直接扫正文关键词组合。
    
    返回: (evidence_dict, days_old)
    """
    import re
    from datetime import datetime
    
    evidence = {
        "case_study": 0,
        "roi_data": 0,
        "manager_perspective": 0,
        "data_quality": 0
    }
    
    # 1. 案例检测：含"案例/实战/落地/项目/实践"关键词
    case_keywords = r'(案例|实战|落地|项目实践|真实|复盘)'
    entity_pattern = r'([A-Z][a-z]+|[一-龟]{2,4}(公司|集团|部门|团队|项目))'
    
    if re.search(case_keywords, content):
        if re.search(entity_pattern, content):
            evidence["case_study"] += 2  # 含实体名，强证据
        else:
            evidence["case_study"] += 1  # 弱证据
    
    # 2. ROI/数据检测：数字 + 百分比 + 业务指标
    roi_keywords = r'(ROI|成本|收益|节省|提升|增长|降低|效率|转化率|GMV|营收|付费|留存)'
    number_pattern = r'\d+(\.\d+)?%?'
    matches = re.findall(
        f'{roi_keywords}.{{0,30}}?{number_pattern}|{number_pattern}.{{0,30}}?{roi_keywords}',
        content
    )
    if matches:
        evidence["roi_data"] = min(len(matches), 5)
    
    # 3. 中层视角检测：核心读者群体关键词
    manager_keywords = r'(中层|管理者|决策者|主管|总监|负责人|团队管理|跨部门|协作|汇报|KPI|OKR|向上管理|领导力)'
    if re.search(manager_keywords, content):
        evidence["manager_perspective"] += 1
    
    # 4. 数据质量/口径说明
    quality_keywords = r'(样本量|调研|问卷|访谈|数据来源|口径|统计方法|方法论|实验|对照)'
    if re.search(quality_keywords, content):
        evidence["data_quality"] += 1
    
    # 5. 时效性检测：优先从 FM 读 date，兜底扫内容中的年份
    days_old = 365 * 5  # 默认 5 年前
    fm_date = fm.get('date', '')
    if fm_date:
        try:
            # 尝试多种日期格式
            for fmt in ['%Y-%m-%d', '%Y-%m', '%Y/%m/%d', '%Y%m%d']:
                try:
                    update_dt = datetime.strptime(str(fm_date)[:10], fmt)
                    days_old = (datetime.now() - update_dt).days
                    break
                except ValueError:
                    continue
        except Exception:
            pass
    
    if days_old >= 365 * 5:  # FM 没读到，尝试内容
        year_match = re.search(r'20\d{2}年?', content)
        if year_match:
            try:
                year = int(year_match.group(0).replace('年', ''))
                days_old = (datetime.now() - datetime(year, 1, 1)).days
            except ValueError:
                pass

    if days_old < 0:
        days_old = 0

    return evidence, days_old


# 缺失项关键词映射（用于指导 API 检索，显著提升命中率）
_DEFICIENCY_KEYWORDS = {
    "真实落地案例": ["案例", "实战", "落地", "企业", "实践"],
    "ROI 或成本收益数据": ["ROI", "投入产出", "成本", "收益", "数据"],
    "中层管理者视角": ["中层管理者", "管理者", "团队", "领导力", "管理"],
    "时效性不足": ["最新", "趋势", "前沿", "动态"],
    "信息密度偏低": ["深度分析", "系统", "框架", "方法论"],
}

def _scan_material_signals(evidence_totals: dict, latest_update_days: int, avg_density: float, matched_count: int = 0) -> dict:
    """素材雷达：只汇报信号事实，不做评分。
    
    选题阶段不应判断"缺了扣多少分"——因为还没决定写什么类型。
    方法论型不需要案例，实操型必须有 ROI。类型判断留给 Outline 阶段。
    这里只客观汇报：素材池里有什么、缺什么。
    """
    signals = {
        "has_real_cases": evidence_totals["case_study"] >= 3,
        "has_roi_data": evidence_totals["roi_data"] >= 3,
        "has_manager_view": evidence_totals["manager_perspective"] >= 3,
        "is_fresh": latest_update_days <= 365,
        "info_density_ok": avg_density >= 0.5,
    }
    
    good = sum(1 for v in signals.values() if v)
    total = len(signals)
    
    if good >= 4:
        verdict, vlevel = "素材充足，可直接撰写", "good"
    elif good >= 2:
        verdict, vlevel = "素材部分缺失，建议针对性补充", "warn"
    else:
        verdict, vlevel = "素材严重不足，建议暂存为灵感或补充调研", "bad"
    
    signal_details = [
        {"key": "has_real_cases", "label": "真实落地案例", "ok": signals["has_real_cases"],
         "detail": f"检测到 {evidence_totals['case_study']} 处案例证据，素材充实" if signals["has_real_cases"]
                   else f"仅 {evidence_totals['case_study']} 处案例证据，缺乏实证支撑"},
        {"key": "has_roi_data", "label": "ROI 数据", "ok": signals["has_roi_data"],
         "detail": f"检测到 {evidence_totals['roi_data']} 处量化数据，支撑充足" if signals["has_roi_data"]
                   else f"仅 {evidence_totals['roi_data']} 处量化数据，缺乏数据支撑"},
        {"key": "has_manager_view", "label": "管理者视角", "ok": signals["has_manager_view"],
         "detail": f"检测到 {evidence_totals['manager_perspective']} 处管理者视角，定位精准" if signals["has_manager_view"]
                   else f"仅 {evidence_totals['manager_perspective']} 处管理者视角"},
        {"key": "is_fresh", "label": "时效性", "ok": signals["is_fresh"],
         "detail": f"最新素材更新于 {latest_update_days} 天前，时效性良好" if signals["is_fresh"]
                   else f"最新素材更新于 {latest_update_days} 天前，内容可能过时"},
        {"key": "info_density_ok", "label": "信息密度", "ok": signals["info_density_ok"],
         "detail": f"相关素材平均密度 {avg_density:.0%}，干货含量充足" if signals["info_density_ok"]
                   else f"相关素材平均密度 {avg_density:.0%}，干货含量偏低"},
    ]
    
    # 兼容旧的 deficiency/satisfied 格式（补充环节仍需要）
    deficiency = [{
        "item": s["label"], 
        "severity": "high" if s["key"] in ("has_real_cases",) and not s["ok"] else "medium",
        "explanation": s["detail"],
    } for s in signal_details if not s["ok"]]
    
    satisfied = [{
        "item": s["label"],
        "explanation": s["detail"],
    } for s in signal_details if s["ok"]]
    
    return {
        "signal_report": {
            "signals": signals,
            "good_count": good,
            "total_count": total,
            "verdict": verdict,
            "verdict_level": vlevel,
            "signal_details": signal_details,
        },
        # 兼容旧格式
        "deficiency_details": deficiency,
        "satisfied_details": satisfied,
        # 补充环节用的数据保留
        "deficiency_details_full": [
            {
                "item": s["label"],
                "severity": "high" if s["key"] in ("has_real_cases",) and not s["ok"] else "medium",
                "explanation": s["detail"],
                "suggested_count": max(1, 3 - evidence_totals.get({"has_real_cases":"case_study","has_roi_data":"roi_data","has_manager_view":"manager_perspective"}.get(s["key"], "case_study"), 0)),
                "suggested_keywords": _DEFICIENCY_KEYWORDS.get(s["label"], [f"{s['label']} 实践 案例"]),
            } for s in signal_details if not s["ok"]
        ],
    }


def calculate_material_scores(direction_name: str, all_docs_map: dict) -> dict:
    """
    计算单个方向的素材完整度评分 (0-100)。
    复用现有向量索引（search_similar + get_embedding_model），不做全量重新编码。
    
    all_docs_map: {"文件路径": {"_full_content": ..., "name": ..., ...}, ...}
    """
    model = get_embedding_model()
    if model is None or _VECTORS is None:
        # 即便向量模型未就绪，也要输出完整的 signal_report（空信号），避免前端雷达卡在"扫描中"
        fallback_report = _scan_material_signals(
            {"case_study": 0, "roi_data": 0, "manager_perspective": 0, "data_quality": 0},
            latest_update_days=3650, avg_density=0.0, matched_count=0
        )
        return {
            "direction": direction_name,
            "material_score": 0,
            "related_count": 0,
            "evidence_counts": {"case_study": 0, "roi_data": 0, "manager_perspective": 0, "data_quality": 0},
            "latest_update_days": 365 * 10,
            "avg_density": 0.0,
            "deficiency_details": fallback_report.get("deficiency_details", [
                {"item": "向量模型未就绪", "severity": "high", "explanation": "无法进行语义匹配，无法计算素材完整度"}
            ]),
            "satisfied_details": fallback_report.get("satisfied_details", []),
            "signal_report": fallback_report.get("signal_report", {}),
            "matched_docs": [],
        }
    
    # 1. 编码方向名称 → 在现有 FAISS 索引中搜索
    try:
        q_vec = model.encode(direction_name, convert_to_numpy=True)
        search_results = search_similar(q_vec, top_k=20)
    except Exception as e:
        logger.warning(f"[MaterialScore] 向量搜索失败: {e}")
        search_results = []
    
    # 2. 匹配全库文档，统计证据
    evidence_totals = {"case_study": 0, "roi_data": 0, "manager_perspective": 0, "data_quality": 0}
    latest_update_days = 365 * 10
    densities = []
    matched_count = 0
    matched_docs = []  # 雷达匹配到的文档列表（path/name/score），供写作阶段复用

    for res in search_results:
        meta = res["meta"]
        # 多路径尝试匹配（metadata 中的路径格式多样）
        doc_abs_dir = meta.get("abs_path", "")
        doc_rel = meta.get("path", "")
        full_doc = None
        
        candidates = [
            os.path.join(doc_abs_dir, doc_rel) if doc_abs_dir and doc_rel else "",
            doc_rel,
            doc_abs_dir,
            os.path.basename(doc_rel) if doc_rel else "",
        ]
        for cand in candidates:
            if not cand:
                continue
            full_doc = all_docs_map.get(cand)
            if full_doc is not None:
                break
        if full_doc is None:
            continue
        
        matched_count += 1
        content = full_doc.get("_full_content", full_doc.get("content", ""))
        fm = full_doc.get("front_matter", {})
        if not fm:
            # 从内容提取 FM
            extracted = _extract_front_matter(content)
            fm = {"date": ""}
        
        evidence, days_old = detect_evidence_in_content(content, fm)
        
        for key in evidence_totals:
            evidence_totals[key] += evidence.get(key, 0)
        
        if days_old < latest_update_days:
            latest_update_days = days_old
        
        density = full_doc.get("_density", calc_heuristic_density(content))
        densities.append(density)
        matched_docs.append({
            "path": full_doc.get("path", doc_abs_dir or doc_rel),
            "abs_path": doc_abs_dir or full_doc.get("path", ""),
            "name": full_doc.get("name", os.path.basename(doc_rel or doc_abs_dir or "")),
            "score": round(float(res.get("score", 0)), 3),
        })

    avg_density = sum(densities) / len(densities) if densities else 0.0
    
    # 3. 应用评分公式
    score = 0.0
    score += min(matched_count / 10.0, 1.0) * 40
    score += min(evidence_totals["case_study"] / 3.0, 1.0) * 20
    score += min(evidence_totals["roi_data"] / 3.0, 1.0) * 15
    score += min(evidence_totals["manager_perspective"] / 3.0, 1.0) * 25
    score += min(evidence_totals["data_quality"] / 3.0, 1.0) * 5
    
    # 扣分项
    if latest_update_days > 365:
        score -= 20
    if latest_update_days > 730:
        score -= 20
    if avg_density < 0.5:
        score -= 15
    if avg_density < 0.3:
        score -= 15
    
    report = _scan_material_signals(evidence_totals, latest_update_days, avg_density, matched_count)
    return {
        "direction": direction_name,
        "material_score": max(0, round(score)),
        "related_count": matched_count,
        "evidence_counts": evidence_totals,
        "latest_update_days": latest_update_days,
        "avg_density": round(avg_density, 2),
        "matched_docs": matched_docs,
        **report,
    }


def format_selected_docs(selected_docs: list, max_total_chars: int = 12000) -> str:
    """
    将 Phase 1 精选文档格式化为 LLM 可读的摘要文本。
    每篇控制在 800 字以内，总长度硬性熔断。
    
    selected_docs: [{"name": ..., "_full_content": ..., "_density": ..., "path": ...}, ...]
    """
    formatted_parts = []
    current_chars = 0
    target_chars_per_doc = 800
    
    for i, doc in enumerate(selected_docs):
        name = doc.get("name", f"文档{i+1}")
        path = doc.get("path", "")
        content = doc.get("_full_content", "")
        density = doc.get("_density", 0)
        
        # 提取 Front Matter
        fm = _extract_front_matter(content)
        fm_display = fm[:200] if fm else "（无 Front Matter）"
        
        # 提取标题结构
        lines = content.split('\n')
        headers = []
        for line in lines:
            if line.startswith('# ') or line.startswith('## '):
                headers.append(line.strip())
        headers_str = ' > '.join(headers[:6]) if headers else "（无标题结构）"
        
        # 智能截断
        truncated = smart_truncate(content, max_chars=target_chars_per_doc)
        
        # 组装单篇摘要
        doc_block = (
            f"### 文档 {i+1}：{name}\n"
            f"- 路径：{path}\n"
            f"- 信息密度：{density:.0%}\n"
            f"- 内容结构：{headers_str}\n"
            f"- Front Matter 摘要：{fm_display}\n"
            f"\n内容摘要：\n{truncated}\n"
        )
        
        block_chars = len(doc_block)
        if current_chars + block_chars > max_total_chars:
            remaining = len(selected_docs) - i
            formatted_parts.append(f"\n... [还有 {remaining} 篇文档因长度限制省略] ...\n")
            break
        
        formatted_parts.append(doc_block)
        current_chars += block_chars
    
    return "\n---\n".join(formatted_parts)


# ============================================================
# Step 2 + Step 5 Prompt 模板
# ============================================================

NOMINATION_PROMPT = """你是一位拥有 10 年经验的**资深内容策略师**，擅长从海量信息中挖掘高价值选题。
你的任务是：基于**作者的核心定位**和**知识库的宏观分布**，提名 8-10 个最具潜力的写作方向。

---
## 🔴 作者身份定位（宪法级约束，必须遵守）
{persona_content}

---
## 📊 知识库宏观分布（仅作分布参考，不代表内容深度）
*   **总文件数**：{total_files} 篇
*   **分类交叉统计**（单篇可多标签）：
    {category_distribution}
*   **注**：分类为交叉标签，单篇可同时属于多个分类（如一篇可同时标"技巧 + 产品"），
    故分类计数总和可能大于总文件数。
*   **基石锚点**（知识库密度最高的核心文档，选题时应主动呼应其方法论）：
    {anchor_docs}

---
## 🚫 绝对禁令
1.  **严禁判断素材完整度**：你此刻没有权限读取具体文件内容，因此绝对不能评价"素材够不够"、"是否有案例"。此类判断将由系统后续完成。
2.  **严禁编造数据**：严禁编造文档数量、百分比、ROI 数据或具体人名。提及文档数量时必须使用上文的总文件数（{total_files} 篇），严禁使用"50篇"、"近百篇"等虚构数字。
3.  **避免泛泛而谈**：拒绝"AI 未来展望"这类虚题，必须紧扣"落地"、"效率"、"决策"、"系统化"。

---
## 📝 推理约束
1.  **使用观察性语言**：描述推荐理由时用事实陈述，禁止过程性修辞。
    *   ❌ 错误："通过高频关键词交叉印证，发现……"
    *   ✅ 正确："基于知识库中「成本」「ROI」相关分类占比较高，建议……"
    *   ❌ 错误："经过深度提炼，得出以下结论……"
    *   ✅ 正确："从知识库分类分布来看，该方向有较好的素材基础。"
2.  **引用已知数据**：推荐每个方向时，尽可能关联到上文的具体分类或锚点文档。

以上为本次参考数据。推荐方向时必须锚定上文的数据（文件数、分类分布、锚点文档），
禁止忽略已有数据凭空编造。

---
## ✅ 输出要求
请直接输出 JSON 对象，不要包含任何解释性文字或 markdown 代码块。

**格式**：
{{
  "nominated_directions": [
    {{"name": "方向名称（简洁有力，吸引决策者）", "description": "一句话描述该方向如何解决受众痛点（30 字以内）。"}}
  ]
}}

**示例**（仅展示格式，实际请输出 8-10 个）：
{{
  "nominated_directions": [
    {{"name": "中层管理者的 AI 决策避坑指南", "description": "基于系统化思维，梳理决策流程中的常见幻觉与验证机制。"}},
    {{"name": "小微企业的零代码自动化改造路径", "description": "利用现有工具链，构建低成本、高可靠性的业务流系统。"}}
  ]
}}
"""


SCORING_PROMPT = """你是一位**资深选题评审官**，以严苛和务实著称。
你的任务是：基于**作者身份**、**精选素材内容**以及**系统预计算的素材完整度**，对以下提名方向进行最终评审。

---
## 🔴 作者身份定位（宪法级约束）
{persona_content}

---
## 📚 精选素材内容（Phase 1 密度精选，质量最高）
以下是系统基于信息密度评分精选出的核心文档摘要（已做语义切片处理）：

{selected_docs_content}

---
## 📊 待评审方向及系统预计算数据
系统已对每个方向的素材完整度进行了全库扫描和计算。请务必尊重以下数据，不要质疑或修改它们。

{directions_json}

---
## 🧮 评分规则（必须严格执行）

请对每个方向进行评分：

1. **direction_score（方向适合度，0-100）**：
   - 由你判断。该方向是否符合作者的核心定位？是否能击中目标读者的真实痛点？
   - 高分标准：能直接落地实践、有系统化思维框架、去概念化的务实风格
   - 低分标准：过于学术理论、过于基础入门、或偏离核心读者群体

2. **material_score（素材完整度，0-100）**：
   - 系统预计算，你无权修改。直接引用输入数据中提供的值。
   - 该分数已综合考虑：相关文件数量、案例/ROI/中层视角含量、时效性、信息密度。

3. **reason（评分理由，30 字内）**：
   - 仅评价该方向为何匹配或不匹配作者身份与读者定位。**严禁提及素材完整度**（案例数/ROI/时效/密度等已由系统雷达提供，见输入数据）

⚠️ 注意：综合评分将由系统自动计算（方向适合度 × 0.6 + 素材完整度 × 0.4），你不需要计算。

---
## ✅ 输出要求

请直接输出 JSON 对象，不要包含任何解释性文字或 markdown 代码块。

**格式**：
{{
  "topics": [
    {{
      "name": "方向名称",
      "description": "方向描述（延续提名时的描述）",
      "direction_score": 85,
      "material_score": 78,
      "reason": "简要说明方向匹配度"
    }}
  ],
  "summary": "知识库内容概况（100 字内），说明各类别分布和文件总数"
}}

**注意**：
- material_score 必须与输入数据完全一致，不得自行修改
- 按 direction_score 降序排列 topics 数组
- 从所有提名方向中选出最优的 3-5 个作为最终推荐
"""


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
    model = V4_FLASH
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
        from src.ai_pulse_client import get_ai_pulse_client
        # 从缺失项提取搜索关键词（至少 2 字符才有效）
        keywords = [w for w in missing_item.replace("，", " ").replace("、", " ").split() if len(w) >= 2]
        client = get_ai_pulse_client()
        cases = await client.fetch_latest_cases(keywords, days=7, take=3)
        ai_pulse_cases = [
            {
                "title": c["title"],
                "source": c["source"],
                "summary": c["summary"],
                "url": c["url"],
                "score": c["score"],
            }
            for c in cases
        ]
        if ai_pulse_cases:
            logger.info(f"AI-Pulse 检索成功：{len(ai_pulse_cases)} 条，关键词={keywords}")
        else:
            logger.warning(f"AI-Pulse 检索返回 0 条，关键词={keywords}")
    except Exception as e:
        logger.warning(f"AI-Pulse 检索失败：{e}")
        ai_pulse_cases = []

    # Step 2: Web 搜索降级（AI-Pulse 不足时，通过 DuckDuckGo 搜索补充）
    web_search_cases = []
    if not ai_pulse_cases:
        try:
            from src.web_search import search_web_batch
            search_queries = [missing_item[:80]]  # 用缺失项本身作为搜索关键词
            web_results = await search_web_batch(search_queries, max_per_query=3)
            web_search_cases = [
                {
                    "title": r["title"],
                    "source": r.get("source", "web"),
                    "summary": r.get("snippet", ""),
                    "url": r.get("url", ""),
                    "score": 0,
                }
                for r in web_results
            ]
            if web_search_cases:
                logger.info(f"Web 搜索成功：{len(web_search_cases)} 条")
            else:
                logger.warning(f"Web 搜索返回 0 条，关键词={missing_item[:50]}")
        except Exception as e:
            logger.warning(f"Web 搜索失败：{e}")
            web_search_cases = []

    # 合并用户勾选案例、AI-Pulse 案例、Web 搜索案例
    all_cases = selected_cases + ai_pulse_cases + web_search_cases

    # 判断内容来源
    has_search = len(all_cases) > 0
    is_web_only = len(web_search_cases) > 0 and len(ai_pulse_cases) == 0
    has_kb = kb_context and len(kb_context.strip()) > 0

    if has_search and has_kb:
        content_source = "web+kb" if is_web_only else "ai-pulse+kb"
    elif has_search:
        content_source = "web" if is_web_only else "ai-pulse"
    elif has_kb:
        content_source = "kb"
    else:
        content_source = "ai_inference"

    # 格式化检索案例
    cases_context = ""
    if all_cases:
        case_source_label = "Web 搜索" if is_web_only else "AI-Pulse"
        cases_list = "\n".join([
            f"• 【{c.get('title', '')}】\n  来源：{c.get('source', 'Web')}\n  摘要：{c.get('summary', '')}"
            for c in all_cases
        ])
        cases_context = f"\n【{case_source_label} 检索到的相关案例】（请优先引用这些案例中的事实和数据）\n{cases_list}"

    # 格式化知识库上下文
    kb_context_str = ""
    if kb_context:
        kb_context_str = f"\n【知识库补充内容】（AI生成时请优先引用以下内容）\n{kb_context}"

    # 推断依据说明模板
    source_note_map = {
        "ai-pulse+kb": "基于 AI-Pulse 检索案例 + 知识库内容 + 上下文推理",
        "ai-pulse": "基于 AI-Pulse 检索案例 + 上下文推理",
        "web+kb": "基于 Web 搜索案例 + 知识库内容 + 上下文推理",
        "web": "基于 Web 搜索案例 + 上下文推理",
        "kb": "基于知识库内容 + 上下文推理",
        "ai_inference": "Web 搜索和知识库均无匹配内容，采用纯 AI 上下文推理补充（内容仅供参考，建议核实）",
    }

    # 根据来源生成说明
    if is_web_only:
        workflow_note = """【工作流说明】
1. 系统已通过 Web 搜索自动检索到相关案例（见下方"Web 搜索检索案例"）
2. 系统已加载绑定的知识库内容（见下方"知识库补充内容"）
3. 你需要基于 MCP 摘要 + Web 搜索案例 + 知识库内容，做上下文推断补充"""
    else:
        workflow_note = """【工作流说明】
1. 系统已通过 AI-Pulse API 自动检索到外部案例（见下方"AI-Pulse 检索案例"）
2. 系统已加载绑定的知识库内容（见下方"知识库补充内容"）
3. 你需要基于 MCP 摘要 + AI-Pulse 案例 + 知识库内容，做上下文推断补充"""

    prompt = f"""你是一个内容策划专家。请根据以下信息，为指定的缺失项生成补充内容。

{workflow_note}

【缺失项】
{missing_item}

【MCP 素材摘要】
{mcp_summary}
{cases_context}{kb_context_str}

【作者身份定位】（只影响语言风格，不影响内容事实）
{persona_summary}

请为这个缺失项生成补充内容，要求：
1. 优先引用检索案例中的信息（如有）
2. 其次引用知识库内容（如有）
3. 结合 MCP 摘要中的已有信息做推断
4. 如果检索案例和知识库都没有足够信息，基于常识做合理推断，并在 inference_note 中标注【纯 AI 推理，建议核实】
5. 语言风格要符合作者身份定位（简洁、实战导向）
6. 内容要具体、可操作

返回 JSON 格式（不要 markdown 代码块）：
{{
  "content": "生成的补充内容",
  "inference_note": "说明推断依据，例如：'{source_note_map[content_source]}'"
}}

注意：
- 如果检索到案例，必须体现其中的关键信息（公司名、数据、效果等）
- 宁可内容少而精，不要编造

请直接返回 JSON：
"""

    try:
        import time
        start_time = time.time()
        result = await _call_llm(
            session_id=session_id,
            call_name="ai_supplement",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.3,
            seed=42,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            phase="AI补充",
        )
        parsed_content = result["choices"][0]["message"]["content"].strip()
        parsed_content = parsed_content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        supplement = json_mod.loads(parsed_content)
        
        # 添加来源信息
        supplement["source"] = content_source

        return _success(supplement)
    except Exception as e:
        logger.error(f"AI 自动补充失败: {e}")
        return _error_internal(e)


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
        return _error_internal(e)


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
        return _error_internal(e)


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
        return _error_internal(e)


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
        return _error_internal(e)


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
        return _error_internal(e)


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
        return _error_internal(e)


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
    AI 推断补充 + 匹配素材（方案 B）
    请求体：
    {
        "session_id": "会话 ID",
        "missing_item": "缺失项描述",
        "mcp_summary": "MCP 摘要",
        "selected_cases": [...],       // API 检索案例
        "existing_content": "已有补充内容",
        "kb_files": [...],             // 知识库文件路径列表
        "use_web_search": false,       // 是否启用联网搜索
        "web_search_keyword": "",      // 联网搜索关键词
        "user_prompt": "",             // 用户手册输入
        "user_files": [...],           // 用户上传文件
    }
    
    返回：
    {
        "content": "推断补充文字",
        "supplement_type": "...",
        "confidence": 0.8,
        "inference_note": "...",
        "matched_materials": {
            "kb_files": [{"path": "...", "name": "...", "content": "..."}],
            "ai_pulse_articles": [{"title": "...", "source": "...", "summary": "...", "url": "..."}]
        }
    }
    """
    session_id = request.get("session_id", "")
    missing_item = request.get("missing_item", "")
    mcp_summary = request.get("mcp_summary", "")
    selected_cases = request.get("selected_cases", [])
    existing_content = request.get("existing_content", "")
    kb_files = request.get("kb_files", [])
    use_web_search = request.get("use_web_search", False)
    web_search_keyword = request.get("web_search_keyword", "")
    user_prompt = request.get("user_prompt", "")
    user_files = request.get("user_files", [])
    
    llm_config = _get_config("llm")
    base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = llm_config.get("api_key", "")
    model = V4_FLASH
    timeout = llm_config.get("timeout", 60)
    
    persona_summary = ""
    try:
        persona_parsed = _get_persona_parsed()
        if persona_parsed:
            persona_summary = persona_parsed.get("summary", "")
    except:
        pass
    
    # ========== 方案 B：收集匹配素材 ==========
    matched_materials = {
        "kb_files": [],
        "ai_pulse_articles": [],
    }
    
    # 1. 读取知识库文件内容
    kb_context = ""
    if kb_files:
        try:
            kb = KnowledgeBaseReader(_get_config("knowledge_base"))
            for fp in kb_files:
                try:
                    content = kb.read_file(fp)
                    if content:
                        # 截取前 3000 字避免 token 爆炸
                        truncated = content[:3000] + ("..." if len(content) > 3000 else "")
                        name = fp.split("/")[-1] if "/" in fp else fp
                        matched_materials["kb_files"].append({
                            "path": fp,
                            "name": name,
                            "content": truncated,
                        })
                except Exception as e:
                    logger.warning(f"读取知识库文件失败 {fp}: {e}")
            if matched_materials["kb_files"]:
                kb_files_text = "\n".join([
                    f"【{m['name']}】\n{m['content']}"
                    for m in matched_materials["kb_files"]
                ])
                kb_context = f"\n【知识库匹配文件】\n{kb_files_text}"
        except Exception as e:
            logger.warning(f"初始化知识库读取器失败: {e}")
    
    # 2. 联网搜索（AI-Pulse）
    ai_pulse_context = ""
    if use_web_search:
        try:
            from src.ai_pulse_client import AIPulseClient
            ai_pulse_config = _get_config("ai_pulse")
            if ai_pulse_config.get("enabled", False):
                client = AIPulseClient(
                    base_url=ai_pulse_config.get("base_url", "http://8.130.148.166:8887"),
                    timeout=ai_pulse_config.get("timeout", 5),
                )
                search_kw = web_search_keyword or missing_item[:20] or "AI"
                pulse_cases = await client.fetch_latest_cases(
                    keywords=[search_kw],
                    days=7,
                    take=5,
                )
                if not pulse_cases:
                    pulse_cases = await client.fetch_latest_cases(
                        keywords=[],
                        days=7,
                        take=5,
                    )
                for case in (pulse_cases or []):
                    article = {
                        "title": case.get("title", ""),
                        "source": case.get("source", ""),
                        "summary": case.get("summary", ""),
                        "url": case.get("url", ""),
                    }
                    matched_materials["ai_pulse_articles"].append(article)
                
                if matched_materials["ai_pulse_articles"]:
                    pulse_text = "\n".join([
                        f"• 【{a['title']}】来源：{a['source']}\n  摘要：{a['summary']}"
                        for a in matched_materials["ai_pulse_articles"]
                    ])
                    ai_pulse_context = f"\n【AI-Pulse 联网检索结果】\n{pulse_text}"
        except Exception as e:
            logger.warning(f"AI-Pulse 检索失败: {e}")
    
    # ========== 构建 prompt（含匹配素材） ==========
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
    
    user_files_context = ""
    if user_files:
        files_text = "\n".join([
            f"• {f.get('name', '')}: {f.get('content', '')[:500]}"
            for f in user_files
        ])
        user_files_context = f"\n【用户上传文件】\n{files_text}"
    
    user_prompt_context = ""
    if user_prompt:
        user_prompt_context = f"\n【用户补充说明】\n{user_prompt}"
    
    # 统一 prompt
    prompt = f"""你是一个内容策划专家。请根据以下信息，为指定缺失项生成补充内容。

【缺失项】
{missing_item}

【MCP 素材摘要】
{mcp_summary}
{cases_context}
{kb_context}
{ai_pulse_context}
{existing_context}
{user_files_context}
{user_prompt_context}

【作者身份定位】
{persona_summary}

═══════════ 核心原则（必须严格执行）═══════════

【Cherry 补充原则】
1. 边界原则：已有素材说了什么 = 边界，绝不越界添加已有素材没说的观点
2. 增厚原则：已有素材说了但只说半句 = 帮他说完（拆层、加类比、加假设案例）
3. 不发明原则：已有素材完全没说的 = 不替他说，如需补充必须用疑问句式
4. 提问>断言：不确定时用"这可能意味着..."而不是"这是..."

【素材来源优先级】（严格按顺序使用）
- 第1层：知识库匹配文件中的内容（标注：[知识库]）
- 第2层：AI-Pulse 联网检索结果（标注：[联网检索]）
- 第3层：MCP 摘要/API 案例中隐含但未展开的内容（标注：[原文推导]）
- 第4层：公开资料中的通用知识（标注：[公开资料]）
- 绝对禁止：编造具体数据、编造人名/公司案例、编造研究报告

请直接返回 JSON（不要 markdown 代码块）：
{{
  "content": "生成的补充内容",
  "supplement_type": "fill",
  "confidence": 0.75,
  "inference_note": "说明推断依据，如：'基于知识库文件X + 联网检索Y 推断'"
}}

supplement_type 取值：thicken（增厚）/ fill（补全）/ infer（推断）
confidence 取值 0-1，越高越可信

注意：
- 优先使用知识库匹配文件和联网检索的具体信息
- 所有补充内容标注来源：[知识库]/[联网检索]/[原文推导]/[公开资料]
- 宁可内容少而精，不要编造
"""
    
    try:
        result = await _call_llm(
            session_id=session_id,
            call_name="AI推断补充",
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0.3,
            max_tokens=2048,
            seed=42,
            timeout=timeout,
            phase="补充信息",
        )
        
        parsed_content = result["choices"][0]["message"]["content"].strip()
        parsed_content = parsed_content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        supplement = json_mod.loads(parsed_content)
        
        # 确保返回格式
        supplement.setdefault("supplement_type", "infer")
        supplement.setdefault("confidence", 0.7)
        
        # 验证
        valid_types = ["thicken", "fill", "infer"]
        if supplement.get("supplement_type") not in valid_types:
            supplement["supplement_type"] = "infer"
        try:
            conf = float(supplement.get("confidence", 0.7))
            # ══ 修复：LLM 可能显式返回 0，setdefault 无法拦截 ══
            if conf <= 0:
                conf = 0.7
            supplement["confidence"] = max(0.0, min(1.0, conf))
        except:
            supplement["confidence"] = 0.7
        
        # 方案 B：附带匹配素材
        supplement["matched_materials"] = matched_materials

        # 丰富最近一条日志的 thinking_chain：AI推断补充详情
        session = _get_session(session_id)
        if session:
            logs = session.get("thinking_logs", [])
            if logs:
                last = logs[-1]
                supp_type_map = {"thicken": "增厚补充", "fill": "补全补充", "infer": "推断补充"}
                supp_type_name = supp_type_map.get(supplement.get("supplement_type", "infer"), "补充")
                content_text = supplement.get("content", "")
                content_words = len(content_text) if content_text else 0
                sources = supplement.get("sources", [])
                source_names = "、".join(sources) if sources else "知识库推断"
                chain = [
                    {"step": 1, "action": f"AI{supp_type_name}", "reason": f"针对缺失项进行{supp_type_name}，补充{content_words}字，数据来源：{source_names}", "result": f"补充完成，置信度{int(supplement.get('confidence', 0.7) * 100)}%"},
                ]
                kb_files = matched_materials.get("kb_files", [])
                pulse_articles = matched_materials.get("ai_pulse_articles", [])
                step_idx = 2
                for kf in kb_files:
                    chain.append({"step": step_idx, "action": f"知识库素材：{kf.get('name', '未命名文件')}", "reason": "匹配到知识库相关文件，提取关键信息", "result": f"引用了{kf.get('name', '')}中的内容"})
                    step_idx += 1
                for pa in pulse_articles:
                    chain.append({"step": step_idx, "action": f"联网检索：{pa.get('title', '未命名文章')}", "reason": f"通过AI-Pulse检索到相关案例，来源{pa.get('source', '未知')}", "result": "已纳入参考素材"})
                    step_idx += 1
                last["thinking_chain"] = chain
        
        return _success(supplement)
    except Exception as e:
        logger.error(f"AI 推断失败: {e}")
        return _error_internal(e)


@router.get("/api/kb/files")
async def get_kb_files(category: Optional[str] = None):
    """列出知识库文件"""
    try:
        kb = KnowledgeBaseReader(_get_config("knowledge_base"))
        files = kb.list_directory(category)
        return _success(files)
    except Exception as e:
        logger.error(f"列出知识库文件失败: {e}")
        return _error_internal(e)


@router.post("/api/kb/read")
async def read_kb_file(request: Dict = Body(...), _auth=Depends(verify_api_key)):
    """读取知识库文件内容"""
    file_path = request.get("file_path")
    if not file_path:
        return _error(code=400, msg="缺少 file_path 参数")
    # 路径遍历防护：file_path 必须解析后在知识库根目录内
    kb_cfg = _get_config("knowledge_base")
    kb_root = kb_cfg.get("root_path", "knowledge_base")
    if not _validate_path_within_base(file_path, kb_root):
        logger.warning(f"[Security] KB 路径遍历拦截: {file_path}")
        return _error(code=403, msg="文件路径越界，禁止访问")
    if _has_forbidden_extension(file_path):
        return _error(code=403, msg="禁止读取该类型文件")
    try:
        kb = KnowledgeBaseReader(kb_cfg)
        content = kb.read_file(file_path)
        if content is None:
            return _error(code=404, msg="文件不存在或无法读取")
        return _success({"content": content, "file_path": file_path})
    except Exception as e:
        logger.error(f"读取文件失败: {e}")
        return _error_internal(e)


# ===== 本地文件夹接口（新增） =====

ALLOWED_EXTENSIONS = {".md", ".txt", ".markdown", ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp"}
TEXT_EXTENSIONS = {".md", ".txt", ".markdown"}


@router.post("/api/folders/verify")
async def verify_folder(request: Dict = Body(...), _auth=Depends(verify_api_key)):
    """验证文件夹是否存在并可读取"""
    folder_path = request.get("path", "")
    if not folder_path:
        return _error(code=400, msg="缺少 path 参数")
    if _is_sensitive_system_path(folder_path):
        logger.warning(f"[Security] 敏感系统路径拦截: {folder_path}")
        return _error(code=403, msg="禁止访问该系统路径")
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
        return _error_internal(e)


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
async def list_folder_files(request: Dict = Body(...), _auth=Depends(verify_api_key)):
    """列出文件夹结构（返回树形结构，包含子文件夹）"""
    folder_path = request.get("path", "")
    if not folder_path:
        return _error(code=400, msg="缺少 path 参数")
    if _is_sensitive_system_path(folder_path):
        logger.warning(f"[Security] 敏感系统路径拦截: {folder_path}")
        return _error(code=403, msg="禁止访问该系统路径")
    try:
        path = Path(folder_path)
        if not path.exists() or not path.is_dir():
            return _error(code=404, msg="文件夹不存在")

        tree = _build_folder_tree(path, path)
        return _success(tree)
    except PermissionError:
        return _error(code=403, msg="没有读取权限")
    except Exception as e:
        return _error_internal(e)


@router.post("/api/folders/read")
async def read_folder_file(request: Dict = Body(...), _auth=Depends(verify_api_key)):
    """读取文件夹中的文件内容"""
    folder_path = request.get("folder_path", "")
    file_path = request.get("file_path", "")
    if not folder_path or not file_path:
        return _error(code=400, msg="缺少 folder_path 或 file_path 参数")
    # 路径遍历防护：folder_path 本身必须在允许的基础目录白名单内（防 folder_path=/etc）
    allowed_bases = _get_allowed_read_bases()
    if not _validate_path_in_allowed_bases(folder_path, allowed_bases):
        logger.warning(f"[Security] folder_path 越界拦截: folder={folder_path}")
        return _error(code=403, msg="文件夹路径越界，禁止访问")
    # 路径遍历防护：file_path 必须解析后在 folder_path 内
    if not _validate_path_within_base(file_path, folder_path):
        logger.warning(f"[Security] 路径遍历拦截: folder={folder_path}, file={file_path}")
        return _error(code=403, msg="文件路径越界，禁止访问")
    # 敏感扩展名黑名单
    if _has_forbidden_extension(file_path):
        logger.warning(f"[Security] 敏感扩展名拦截: {file_path}")
        return _error(code=403, msg="禁止读取该类型文件")
    try:
        full_path = (Path(folder_path).resolve() / file_path).resolve()
        if not full_path.exists():
            return _error(code=404, msg="文件不存在")
        content = full_path.read_text(encoding="utf-8")
        return _success({"content": content, "file_path": str(full_path)})
    except UnicodeDecodeError:
        return _error(code=400, msg="文件不是文本格式")
    except PermissionError:
        return _error(code=403, msg="没有读取权限")
    except Exception as e:
        return _error_internal(e)


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
        return _error_internal(e)


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
        return _error_internal(e)


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
        return _error_internal(e)


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

        result = await _call_llm(
            session_id=None,
            call_name="generate_field",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0,
            phase="字段生成",
        )
        content = result["choices"][0]["message"]["content"].strip()
        return _success({"content": content})

    except Exception as e:
        logger.error(f"AI 辅助生成失败: {e}")
        return _error_internal(e)


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
        return _error_internal(e)


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
        return _error_internal(e)


# ===== 生成接口 =====

@router.post("/api/framework/suggest-from-slots")
async def suggest_framework_from_slots(request: Dict = Body(...)):
    """
    V4: 从槽位结构 + 提纲内容 AI 推荐最合适的配图框架类型
    请求体：
    {
        "slots": [
            {"label": "优势分析", "outlines": ["内部资源优势", "技术壁垒"]},
            {"label": "劣势分析", "outlines": ["资金不足", "人才短缺"]}
        ]
    }
    返回：
    {
        "framework_key": "swot",
        "reason": "检测到优势/劣势维度，建议使用SWOT分析框架"
    }
    """
    slots = request.get("slots", [])
    if not slots:
        return _success({"framework_key": "analysis", "reason": "无槽位数据，使用默认分析框架"})

    slot_desc = []
    for s in slots:
        label = s.get("label", "")
        outlines = s.get("outlines", [])
        outline_text = "、".join(outlines[:3]) if outlines else ""
        slot_desc.append(f"- {label}" + (f": {outline_text}" if outline_text else ""))
    slot_text = "\n".join(slot_desc)

    llm_config = _get_config("llm")
    base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = llm_config.get("api_key", "")
    model = V4_FLASH
    timeout = llm_config.get("timeout", 30)

    framework_options = [
        "swot（优势/劣势/机会/威胁四象限）",
        "comparison（对比/比较多个维度）",
        "causal（因果/原因-影响链）",
        "timeline（时间线/阶段/流程演进）",
        "analysis（背景/现状/问题分析）",
        "sequence（步骤序列/阶段划分）",
        "process（业务流程/工作流）",
    ]
    options_text = "\n".join(framework_options)

    prompt = f"""你是一个信息图表类型推荐专家。以下是用户写作的槽位结构（维度）和提纲要点：

{slot_text}

请从以下图表类型中选择最匹配的一个（只返回代号，不要解释）：
{options_text}

只需返回类型代号，例如：swot"""

    try:
        result = await _call_llm(
            session_id=None,
            call_name="配图生成",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.1,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            phase="框架推荐",
        )
        text = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip().lower()
        valid_keys = ["swot", "comparison", "causal", "timeline", "analysis", "sequence", "process"]
        for k in valid_keys:
            if k in text:
                reason_map = {
                    "swot": "检测到多维度结构化分析",
                    "comparison": "检测到对比/比较关系",
                    "causal": "检测到因果逻辑链",
                    "timeline": "检测到时间/阶段演进",
                    "analysis": "检测到分析型结构",
                    "sequence": "检测到步骤序列",
                    "process": "检测到流程结构",
                }
                return _success({"framework_key": k, "reason": reason_map.get(k, "AI 自动匹配")})
        return _success({"framework_key": "analysis", "reason": f"LLM 返回未知类型 {text}，使用默认"})
    except Exception as e:
        logger.warning(f"框架推荐异常: {e}")
        return _success({"framework_key": "analysis", "reason": "AI 推荐异常，使用默认"})


@router.post("/api/generate")
async def generate_diagram(
    framework_key: str = Form(...),
    text: str = Form(...),
    style: str = Form("minimal"),
    size: str = Form("default"),
    _auth=Depends(verify_api_key),
):
    """生成架构图"""
    try:
        logger.info(f"收到生成请求: 框架={framework_key}")

        extractor = StructureExtractor(_get_config("llm"))
        # 解析框架名称 → key（前端可能传中文名）
        resolved_key = extractor.resolve_framework_key(framework_key)
        data = extractor.extract(text, framework_key)

        generator = HTMLGenerator(_get_config("storage"))
        html = generator.render(data, resolved_key, style, size)

        output_dir = Path(_get_config("storage").get("output_dir", "output"))
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{uuid.uuid4().hex}.png"

        screenshot = ScreenshotService()
        await screenshot.capture(html, str(output_path), size)

        logger.info(f"生成完成: {output_path}")
        return FileResponse(str(output_path), media_type="image/png", filename="diagram.png")

    except NotImplementedError as e:
        logger.warning(f"功能未实现: {e}")
        raise HTTPException(status_code=501, detail="该框架暂未实现，请尝试其他框架")
    except Exception as e:
        logger.error(f"生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="生成失败，请稍后重试或检查输入参数")


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
        extractor = StructureExtractor(_get_config("llm"))
        # 解析框架名称 → key（前端可能传中文名）
        resolved_key = extractor.resolve_framework_key(framework_key)
        # 容缺模式：LLM 基于用户数据和原文补全缺失字段
        if source_text and data:
            try:
                extracted = extractor.extract(source_text, framework_key, user_data=data)
                html = generator.render(extracted, resolved_key, style, size)
            except Exception as llm_err:
                logger.warning(f"LLM 提取失败，直接使用用户数据: {llm_err}")
                html = generator.render(data, resolved_key, style, size)
        else:
            html = generator.render(data, resolved_key, style, size)
        return _success({"html": html})
    except Exception as e:
        logger.error(f"预览生成失败: {e}")
        return _error_internal(e)


@router.post("/api/generate/async")
async def generate_diagram_async(
    background_tasks: BackgroundTasks,
    request: Dict = Body(default={}),
):
    """异步生成架构图

    Schema 兼容（与 /api/generate/infographic 对齐）：
      - framework_key | framework_name  （二选一，前者优先）
      - text | article_content           （二选一，前者优先）
      - style, size, session_id          （可选）
    """
    framework_key = request.get("framework_key") or request.get("framework_name", "")
    text = request.get("text") or request.get("article_content", "")
    style = request.get("style", "minimal")
    size = request.get("size", "default")
    session_id = request.get("session_id", "")

    if not framework_key:
        return _error(code=400, msg="缺少 framework_key / framework_name 参数")
    if not text:
        return _error(code=400, msg="缺少 text / article_content 参数")

    task_id = str(uuid.uuid4())
    async_tasks[task_id] = {"status": "pending", "progress": 0}
    background_tasks.add_task(_process_async, task_id, framework_key, text, style, size)

    # 记录配图生成日志
    _log_llm_call_legacy(
        session_id=session_id,
        call_id=f"step5_generate_diagram_{task_id}",
        call_name="配图生成",
        messages=[{"role": "user", "content": f"框架: {framework_key}\n样式: {style}\n尺寸: {size}\n文本: {text[:200]}"}],
        result=f"任务已创建，task_id: {task_id}",
        duration=0,
        thinking_chain=[
            {"step": 1, "action": "生成配图", "reason": f"为框架「{framework_key}」生成架构图，样式{style}，尺寸{size}", "result": f"任务已创建，编号{task_id}"},
        ]
    )

    return _success({"task_id": task_id})


@router.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    """查询异步任务进度"""
    if task_id not in async_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    return _success(async_tasks[task_id])


# ===== 配图生成（信息图：LLM 直出 HTML） =====

_INFOGRAPHIC_SIZE_STRATEGY = {
    "9:16": "纵向堆叠，每个模块占满宽度，模块间用分隔线或间距区分，适合滑动浏览。每模块高度约六分之一。",
    "2.35:1": "横向宽幅，模块必须水平排列，使用 grid-cols-3 或 grid-cols-4。每个模块高度固定，宽度自适应。绝对禁止纵向堆叠。",
    "default": "灵活混合布局，重要模块全宽，次要模块 2-3 列 grid。",
}


def _get_size_strategy(width: int, height: int) -> str:
    """根据宽高比返回布局策略文本"""
    if height <= 0:
        return _INFOGRAPHIC_SIZE_STRATEGY["default"]
    ratio = width / height
    if ratio <= 0.6:
        return _INFOGRAPHIC_SIZE_STRATEGY["9:16"]
    elif ratio >= 2.0:
        return _INFOGRAPHIC_SIZE_STRATEGY["2.35:1"]
    else:
        return _INFOGRAPHIC_SIZE_STRATEGY["default"]


@router.post("/api/generate/infographic")
async def generate_infographic(request: Dict = Body(...), _auth=Depends(verify_api_key)):
    """生成信息图 HTML。LLM 根据文章内容 + 框架 + 尺寸直接输出 Tailwind HTML。
    
    请求体:
        framework_name: 框架名（如"SWOT分析"）
        article_content: 文章全文（Markdown）
        width: 画布宽度（默认1080）
        height: 画布高度（默认1920）
        persona_context: 可选，人设上下文
    """
    framework_name = request.get("framework_name", "通用分析")
    article_content = request.get("article_content", "")
    width = request.get("width", 1080)
    height = request.get("height", 1920)
    persona_context = request.get("persona_context", "")
    composition_hint = request.get("composition_hint", "")

    if not article_content.strip():
        return _error(code=400, msg="缺少 article_content 参数")

    layout_strategy = _get_size_strategy(width, height)
    hint_section = f"\n## 额外构图指令（需严格遵守）\n{composition_hint}\n" if composition_hint.strip() else ""

    prompt = f"""# Role: 资深前端工程师 & 信息密度优化专家
## 任务：将以下内容转化为信息图海报（{width}×{height}px）

## 一、零容忍约束（只要违反任何一条，直接视为输出不合格）

> 以下代码片段必须原封不动出现在输出中，不允许任何字符修改：
> 
> 内容区容器：`<div class="h-[calc(100%-100px)] overflow-hidden p-3 flex flex-col gap-2">`
> 序号徽章：`<span class="w-3.5 h-3.5 rounded-full bg-gradient-to-r from-primary to-secondary text-white text-[7px] font-bold flex items-center justify-center shrink-0">`

1. **内容区空间预算公式写死**：必须是 `h-[calc(100%-100px)]`，不允许 72、88、96、98、102 等任何其他数值
2. **序号徽章尺寸写死**：所有模块的序号圆形徽章必须是 `w-3.5 h-3.5`，不允许 w-3、w-4、w-5 等任何其他尺寸

## 二、硬性约束（违反即报废）

### 1. 画布与容器
- 外层容器：必须使用 `aspect-[3/4]`（方图）或对应比例的 Tailwind 原生类，搭配 `max-w-md` 限制宽度
- **严禁使用 `style="aspect-ratio"` 内联样式，违反即报废**
- 背景：浅色系 `bg-white`，卡片用 `bg-gray-50`
- **顶部标题栏固定**：`h-10 bg-gradient-to-r from-primary/5 to-secondary/5 px-4 py-2`，居中或左对齐标题，文字 10px font-semibold
- 底部标注栏固定 `h-10`（文字 8px text-gray-500），完整渐变背景 `from-primary to-secondary text-white`
- **严禁内容被底栏截断**。如果 6 个模块高度超出，允许增加到 7-8 个更薄的模块，或压缩行高，或减少每个模块的要点行数，但绝不允许最后一个模块被裁切

### 2. 字号层级（五级锁死，禁止浮动 — 违反即报废）
- 顶栏标题：10px font-semibold — 仅顶部标题栏使用
- 模块标题：11px font-semibold — 模块1标题用 `text-primary`，其余模块标题用 `text-gray-800`（体现视觉层级差异）
- 正文要点：9px text-gray-700 leading-tight — 模块内容列表
- 副文说明：8px text-gray-600 — 次要描述文字
- 辅助标签：7px text-gray-500 — 技术细节、节点标注、角标
- **违规判定：任何模块正文使用 ≥10px 视为违反约束**

### 3. 色彩系统（含使用位置规则）
自定义颜色（通过 tailwind.config 注入）：
- primary: #165DFF（品牌蓝）— 仅用于模块标题、Font Awesome 图标、圆形序号徽章、渐变端点
- secondary: #36CFFB（辅助蓝）— 仅作为渐变的另一端，与 primary 搭配

透明度梯度（严格遵守）：
- from-primary/5 to-secondary/5 → 顶栏背景（微妙，几乎不可见）
- from-primary/10 to-secondary/10 → 模块1背景（略可见，突出但不刺眼）
- from-primary to-secondary → 圆形徽章、底栏（完整渐变，视觉锚点）

禁止规则：
- 禁止在正文 (gray-700) 中使用 primary 色（太刺眼）
- 禁止在非渐变场景使用 secondary 色
- 禁止使用 #165DFF 和 #36CFFB 以外的蓝色
- 渐变透明度不允许超过 10%（模块1背景为唯一例外）

### 4. 布局规则
- 模块间距：gap-2，模块内边距：p-3
- **所有卡片统一使用 rounded-xl（≈12-16px 圆角）**，严禁小圆角
- 内容少的模块：使用 `grid-cols-2` 或 `w-1/2` 并列，节省纵向空间
- 内容多的模块：`grid-cols-1` 全宽 + `leading-tight` 压缩行高
- **流程类模块**：水平 `flex` + `w-1/5` 节点 + **图标在上文字在下垂直堆叠** + 箭头 `fa-chevron-right` 水平穿于节点之间
- **每个模块的高度应自然适配其内容量**。内容多的模块自然高一些，内容少的自然矮一些
- **禁止在模块最外层容器使用 `flex-1`**（它会导致所有模块强制等高）。模块内部子元素可以自由使用 flex-1

### 5. 代码规范
- 必须包含：
  `<script src="https://cdn.tailwindcss.com"></script>`
  `<link href="https://cdn.jsdelivr.net/npm/font-awesome@4.7.0/css/font-awesome.min.css" rel="stylesheet">`
  `<script>tailwind.config = {{ theme: {{ extend: {{ colors: {{ primary: '#165DFF', secondary: '#36CFFB' }} }} }} }}</script>`
- 必须定义卡片阴影工具类：
  `<style type="text/tailwindcss">@layer utilities {{ .card-shadow {{ box-shadow: 0 1px 6px rgba(22, 93, 255, 0.06); }} }}</style>`
- 禁止使用 `style` 属性，所有样式必须通过 Tailwind 类名实现
- HTML 结构必须完整闭合，每个标签都有对应闭合标签

### 6. 模块视觉层级（行交替 + 核心亮点）

#### 6.1 行交替配色
- 整体采用**行交替节奏**：同行模块共享一种底色，不同行交替变化，形成视觉呼吸感
- 渐变行：`bg-gradient-to-r from-primary/10 to-secondary/5 rounded-xl`
- 纯白行：`bg-white card-shadow rounded-xl`
- 交替模式示例：第1行渐变 → 第2行纯白 → 第3行渐变 → ...
- **由 LLM 根据实际布局自行决定第几行用哪种底色，不写死**

#### 6.2 核心亮点色块
- 整张图中选 **1 个语义上最核心的模块**（不一定是第一个模块，由内容重要性决定），附带**结论色块**
- 结论色块格式：`bg-gradient-to-r from-primary to-secondary text-white px-3 py-1.5 rounded-lg text-center font-bold`，内容为文章最核心的数字或结论（如"3天上线"、"98%准确率"）
- 结论色块嵌入该模块内部（网格右侧/底部/标题旁），与文字紧凑排列，**禁止孤立悬浮造成大面积留白**

#### 6.3 内容密度
- **每个子模块至少包含 3-4 行要点**，宁可文字小一点、行高低一点，也要保证信息量充足

### 7. 模块结构
- **模块数量完全由文章语义决定，自适应范围 4-9 个**。信息密度高、主题多 → 拆细为 7-9 个；内容精简、主题少 → 4-6 个。**禁止为了凑数而强行拆分，也禁止合并语义不同的子主题**
- 每个模块 `data-module-id="01"/"02"...`
- 每个模块包含：**左侧独立序号圆形徽章**（必须是 `w-3.5 h-3.5`，尺寸写死，不允许放大或缩小，`rounded-full bg-gradient-to-r from-primary to-secondary text-white text-[7px] font-bold flex items-center justify-center shrink-0`）+ 标题行 + 要点列表
- **序号徽章必须与标题文字水平排列，完全独立**，不是标题的一部分
- 每个要点必须有前置 Font Awesome 图标，按以下语义选择：
  - fa-star → AI 亮点、核心功能
  - fa-code → 技术架构、开发流程
  - fa-rocket → 部署、上线、发布
  - fa-database → 数据、存储方案
  - fa-check-circle → 验证、去重、合规
  - fa-clock-o → 定时任务、时效
  - fa-handshake-o → 协作、需求对齐
  - fa-filter → 筛选、过滤规则
  - fa-cogs → 系统配置、引擎

## 二、执行步骤（必须按顺序思考）

### Step 1: 内容蒸馏（最关键）
- 阅读输入素材，提取不超过 6 个核心信息点
- **严禁使用完整句子，必须压缩为短语/关键词**
- 示例："双LLM降本策略，简单任务用DeepSeek V3.2，复杂推理用V4 Pro" → 蒸馏为「双LLM降本：V3.2 轻量 / V4 Pro 复杂」

### Step 2: 空间意识
以下为引导性思考，帮助建立"空间有限"的认知（非精确计算，用 CSS 公式实现）：
- 内容区总高度 ≈ 容器高度 - 48px（顶栏+底栏）
- 若 6 个模块用 `flex-1` + `space-y-1.5` 可自动均分
- 若某模块要点超过 4 条，考虑用 `grid-cols-2` 双列排列以节省纵向空间
- 若某模块要点超过 5 条，必须精简内容

### Step 3: 代码生成
根据蒸馏后的内容和布局约束，生成完整的 HTML。

## 三、框架与风格
- 框架：{framework_name}
- 画布策略：{layout_strategy}
{hint_section}
## 四、输入素材
{article_content[:8000]}

## 输出要求
直接输出 `<!DOCTYPE html>` 开头的完整 HTML 代码。不要 markdown 代码块标记（不要 ```html 或 ```），不要解释文字。"""

    try:
        result = await _call_llm(
            call_name="infographic_generate",
            messages=[
                {"role": "system", "content": "你是一个严格遵守工程约束的前端开发工程师。你输出的是可运行的 HTML 代码，不是设计稿。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=16384,
        )
        raw_html = result["choices"][0]["message"]["content"]
        # 清理可能的 markdown 包裹
        cleaned = raw_html.strip()
        # 零容忍约束硬替换（LLM 可能不遵守 Prompt 约束，这里强制修正）
        cleaned = _apply_infographic_hard_constraints(cleaned)
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:cleaned.rfind("```")].strip()
        # 确认以 <!DOCTYPE 或 <html 开头
        if not (cleaned.lower().startswith("<!doctype") or cleaned.lower().startswith("<html")):
            # 尝试从回复中提取 HTML 片段
            html_start = cleaned.find("<!DO")
            if html_start == -1:
                html_start = cleaned.find("<html")
            if html_start == -1:
                html_start = cleaned.find("<div")
            if html_start >= 0:
                cleaned = cleaned[html_start:]
            else:
                return _error(code=1, msg="LLM 未返回有效 HTML，请重试")

        return _success({"html": cleaned})
    except Exception as e:
        logger.error(f"信息图生成失败: {e}")
        return _error_internal(e, "配图生成失败，请重试")


@router.post("/api/generate/infographic/revise")
async def revise_infographic(request: Dict = Body(...)):
    """根据用户反馈修改信息图 HTML。遵循最小变更原则——只修改目标模块。
    
    请求体:
        current_html: 当前的 HTML 代码
        instruction: 用户的修改指令（自然语言）
        framework_name: 框架名（可选）
        article_content: 文章内容（可选）
        target_module_id: 可选，指定要修改的模块 ID（如"03"），不指定则由 LLM 自动判断
    """
    current_html = request.get("current_html", "")
    instruction = request.get("instruction", "")
    framework_name = request.get("framework_name", "")
    article_content = request.get("article_content", "")
    target_module_id = request.get("target_module_id", "")

    if not current_html.strip():
        return _error(code=400, msg="缺少 current_html 参数")
    if not instruction.strip():
        return _error(code=400, msg="缺少 instruction 参数")

    # 构建模块定位约束
    module_constraint = ""
    if target_module_id:
        module_constraint = f"""**关键约束：** 你只能修改 data-module-id="{target_module_id}" 对应的 <div> 块。
其他所有模块的 HTML 必须保持逐字符不变（包括空格、换行、属性顺序）。
这是硬性要求，违反则视为失败。"""
    else:
        module_constraint = "**约束：** 尽可能只修改与用户指令相关的模块，其余模块保持原样不变。"

    prompt = f"""你是信息图修改专家。根据用户指令，精确修改指定的模块。

{module_constraint}

**用户指令：** {instruction}

**技术约束：**
- 保持 Tailwind CDN + Font Awesome CDN 引用不变
- 保持容器尺寸（width/height）不变
- 保持 data-module-id 属性不变（数量和值都不得变）
- 保持字号系统和颜色方案的连贯性
- 你的修改必须与当前视觉风格融合，不引入不相称的设计元素

{"**框架上下文：** " + framework_name if framework_name else ""}
{"**原文参考：** " + article_content[:1000] if article_content else ""}

**当前 HTML：**
{current_html}

**输出要求：**
- 只输出完整 HTML 代码（从 <!DOCTYPE html> 开始）
- 不添加 markdown 代码块标记
- 不添加任何解释说明文字"""

    try:
        result = await _call_llm(
            call_name="infographic_revise",
            messages=[
                {"role": "system", "content": "你是信息图修改专家，严格按最小变更原则修改 HTML。只输出完整 HTML，不解释。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=16384,
        )
        raw_html = result["choices"][0]["message"]["content"]
        cleaned = raw_html.strip()
        # 零容忍约束硬替换（与 generate_infographic 保持一致）
        cleaned = _apply_infographic_hard_constraints(cleaned)
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:cleaned.rfind("```")].strip()
        if not (cleaned.lower().startswith("<!doctype") or cleaned.lower().startswith("<html")):
            html_start = cleaned.find("<!DO")
            if html_start == -1:
                html_start = cleaned.find("<html")
            if html_start == -1:
                html_start = cleaned.find("<div")
            if html_start >= 0:
                cleaned = cleaned[html_start:]
            else:
                return _error(code=1, msg="LLM 未返回有效 HTML，请重试")

        return _success({"html": cleaned})
    except Exception as e:
        logger.error(f"信息图修改失败: {e}")
        return _error_internal(e, "配图修改失败，请重试")


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
        
        result = await _call_llm(
            session_id=None,
            call_name="analyze_directions",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.2,
            seed=42,
            phase="方向分析",
        )
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
        
        result = await _call_llm(
            session_id=None,
            call_name="content_structure",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8192,
            temperature=0.2,
            seed=42,
            phase="内容结构",
        )
        content = result["choices"][0]["message"]["content"].strip()
        content = content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        try:
            parsed = json_mod.loads(content)
        except (json_mod.JSONDecodeError, ValueError):
            parsed = _safe_json_parse(content, "outlines")
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
        
        result = await _call_llm(
            session_id=session_id,
            call_name="outline_versions",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.5,
            seed=42,
            phase="提纲版本",
        )
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
        return _error_internal(e)


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
        
        result = await _call_llm(
            session_id=None,
            call_name="section_alignment",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0,
            seed=42,
            phase="方向检测",
        )
        content = result["choices"][0]["message"]["content"].strip()
        content = content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        try:
            parsed = json_mod.loads(content)
        except (json_mod.JSONDecodeError, ValueError):
            parsed = _safe_json_parse(content, "outlines")
        
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
        return _error_internal(e)


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
        
        result = await _call_llm(
            session_id=None,
            call_name="generate_section",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.3,
            seed=42,
            phase="段落生成",
        )
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
        return _error_internal(e)


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
        
        result = await _call_llm(
            session_id=None,
            call_name="rewrite_section",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.3,
            seed=42,
            phase="段落重写",
        )
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
        return _error_internal(e)


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
        
        result = await _call_llm(
            session_id=None,
            call_name="全文生成",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8192,
            temperature=0.3,
            seed=42,
            phase="文章生成",
        )
        full_content = result["choices"][0]["message"]["content"].strip()
        
        # 记录思考日志
        usage = result.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        paragraphs = [p for p in full_content.split("\n\n") if p.strip()]
        sections = [p for p in full_content.split("## ") if p.strip()]
        word_count = len(full_content)
        
        _log_process_step(
            session_id=session_id,
            call_name="全文生成",
            phase="写稿",
            steps=[
                {"step": 1, "action": "组装文章结构和素材",
                 "reason": f"方向「{direction_name}」，含 {len(structure.get('sections', []))} 个正文章节 + 开篇 + 结尾，素材 {len(source_text)} 字",
                 "result": "Prompt 已构造完毕，送入 LLM 生成"},
                {"step": 2, "action": "LLM 一次性生成全文",
                 "reason": f"使用 {llm_config.get('model', V4_PRO)} 模型，输入 {prompt_tokens} token，输出 {completion_tokens} token",
                 "result": f"生成 {word_count} 字，共 {len(paragraphs)} 个段落、{len(sections)} 个章节"},
                {"step": 3, "action": "素材来源标注",
                 "reason": "对生成内容中的引用和推断进行自动标注，区分原文引用和 AI 推断",
                 "result": f"有效标签 {processed['valid_count']} 个，已过滤 {processed['filtered_count']} 个"},
            ],
            output=f"全文生成完成：{word_count} 字，{len(sections)} 个章节",
            duration=999,
        )
        
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
        return _error_internal(e)


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
                result = await _call_llm(
                    session_id=session_id,
                    call_name="智能补全",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2048,
                    temperature=0.3,
                    seed=42,
                    phase="智能补全",
                )
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
    
    ai_count = len([v for v in result_sections.values() if v["source"] == "ai"])
    original_count = len([v for v in result_sections.values() if v["source"] == "original"])
    supplement_count = len([v for v in result_sections.values() if v["source"] == "supplement"])
    
    # 记录思考日志
    fill_detail_steps = []
    step_idx = 1
    for sec_info in sections_to_fill:
        key = sec_info["key"]
        sec_result = result_sections.get(key, {})
        source_type = sec_result.get("source", "unknown")
        content = sec_result.get("content", "")
        if source_type == "original":
            desc = "素材充足，直接复用原文"
        elif source_type == "supplement":
            desc = "素材部分覆盖，AI 在原素材基础上补充扩展"
        elif source_type == "ai":
            desc = "素材不足，AI 从零生成"
        else:
            desc = "回退使用预填内容"
        fill_detail_steps.append({
            "step": step_idx,
            "action": f"「{sec_info['title']}」：{desc}",
            "reason": f"生成了 {len(content)} 字内容",
            "result": "已写入最终文章"
        })
        step_idx += 1
    
    _log_process_step(
        session_id=session_id,
        call_name="智能补全",
        phase="写稿",
        steps=fill_detail_steps,
        output=f"智能补全完成：{len(sections_to_fill)} 个段落（{original_count} 段复用原文、{ai_count} 段 AI 生成）",
        duration=999,
    )
    
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
    # 从配置文件加载（持久化）
    try:
        config = _get_config("persona")
        if config and config.get("file_path"):
            _persona_file_path = config["file_path"]
            return _persona_file_path
    except Exception:
        pass
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
async def parse_persona(request: Dict = Body(default={}), _auth=Depends(verify_api_key)):
    """
    解析身份定位文件，提取六维结构化信息（AI推理）
    使用 LLM 将非结构化身份文件解析为六维动态行为模型
    """
    # 优先使用传入的路径，如果没有则使用配置中的路径
    content = ""
    file_path = request.get("file_path", "")
    if file_path:
        # 路径遍历防护：file_path 必须在允许的白名单目录内
        if not _validate_path_in_allowed_bases(file_path, _get_allowed_read_bases()):
            logger.warning(f"[Security] persona/parse 路径越界: {file_path}")
            return _error(code=403, msg="文件路径越界，禁止访问")
        if _has_forbidden_extension(file_path):
            return _error(code=403, msg="禁止读取该类型文件")
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
        model = V4_FLASH
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
        
        result = await _call_llm(
            session_id=None,
            call_name="parse_persona",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0,
            seed=42,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            phase="身份解析",
        )
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
        return _error_internal(e)


async def _parse_persona_sync(content: str):
    """同步解析身份定位内容，返回六维结构化信息"""
    try:
        llm_config = _get_config("llm")
        base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
        api_key = llm_config.get("api_key", "")
        model = V4_FLASH
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
        
        result = await _call_llm(
            session_id=None,
            call_name="parse_persona_sync",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0,
            seed=42,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            phase="身份解析",
        )
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


async def auto_parse_persona(app=None):
    """启动后自动解析身份定位文件，填充六维模型缓存"""
    try:
        import asyncio
        # 等 3 秒让服务器完全启动
        if app:
            await asyncio.sleep(3)
        
        content = _get_persona_content()
        if not content:
            logger.warning("身份定位文件为空或不存在，跳过自动解析")
            return
        
        logger.info("开始自动解析身份定位文件...")
        
        llm_config = _get_config("llm")
        base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
        api_key = llm_config.get("api_key", "")
        model = V4_FLASH
        timeout = llm_config.get("timeout", 60)
        
        if not api_key:
            logger.warning("LLM 未配置 API Key，跳过身份解析")
            return
        
        # 加载六维配置模板
        dimensions_template = ""
        try:
            dim_path = Path(__file__).parent / "config" / "persona_dimensions.md"
            if dim_path.exists():
                dimensions_template = dim_path.read_text(encoding="utf-8")
        except Exception:
            pass
        
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
  "summary": "身份定位的整体描述（200字内），用于作为文章作者身份背景传给LLM"
}}

请直接返回 JSON：
"""
        
        result = await _call_llm(
            session_id=None,
            call_name="auto_parse_persona",
            messages=[{"role": "user", "content": prompt}],
            model=model,
            max_tokens=1024,
            temperature=0,
            seed=42,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            phase="身份自动解析",
        )
        parsed_content = result["choices"][0]["message"]["content"].strip()
        parsed_content = parsed_content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        parsed = json_mod.loads(parsed_content)
        
        _persona_parsed_cache["content"] = content
        _persona_parsed_cache["parsed"] = parsed
        
        summary = parsed.get("summary", "")[:200]
        logger.info(f"身份定位自动解析完成，摘要: {summary}")
    except Exception as e:
        logger.warning(f"身份定位自动解析失败（不影响使用）: {e}")


@router.get("/api/persona/info")
async def get_persona_info():
    """获取身份定位信息：文件路径 + 内容 + 解析后的结构化信息（六维模型）

    注意：GET 接口不触发 LLM 解析（避免 50s+ 阻塞）。
    若缓存不可用，返回 parsed=null，前端可通过 POST /api/persona/parse 主动触发解析。
    """
    file_path = _get_persona_path()
    content = ""
    exists = False
    parsed = None
    try:
        if Path(file_path).exists():
            content = Path(file_path).read_text(encoding="utf-8")
            exists = True
            # 仅返回缓存结果，不主动触发 LLM 解析（防 GET 阻塞）
            parsed = _get_persona_parsed()
    except Exception as e:
        logger.warning(f"读取身份定位文件失败: {e}")

    return _success({
        "file_path": file_path,
        "content": content,
        "exists": exists,
        "parsed": parsed,
    })

@router.post("/api/persona/set_path")
async def set_persona_path(request: Dict = Body(...), _auth=Depends(verify_api_key)):
    """设置身份定位文件路径（同时持久化到 config.yaml）"""
    global _persona_file_path
    file_path = request.get("file_path", "")
    if not file_path:
        return _error(code=400, msg="缺少 file_path 参数")

    # 路径安全校验：必须是 .md/.txt 且在用户主目录或知识库内
    if _has_forbidden_extension(file_path):
        return _error(code=403, msg="禁止设置该类型文件")
    suffix = Path(file_path).suffix.lower()
    if suffix not in {".md", ".txt", ".markdown"}:
        return _error(code=403, msg="仅支持 .md / .txt 文件")

    if not Path(file_path).exists():
        return _error(code=400, msg="文件不存在")

    _persona_file_path = file_path
    
    # 持久化到 config.yaml
    try:
        import yaml
        config_path = Path(__file__).parent / "config" / "config.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            config.setdefault("persona", {})["file_path"] = file_path
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            logger.info(f"身份定位路径已持久化到 config.yaml: {file_path}")
    except Exception as e:
        logger.warning(f"持久化身份路径到 config.yaml 失败: {e}")
    
    return _success({"file_path": file_path})

@router.post("/api/persona/save")
async def save_persona(request: Dict = Body(...), _auth=Depends(verify_api_key)):
    """保存身份定位内容到文件"""
    content = request.get("content", "")
    file_path = _get_persona_path()

    # 写入前再次校验路径合法性（防 set_path 后被篡改）
    if not file_path or _has_forbidden_extension(file_path):
        return _error(code=403, msg="目标文件路径不合法")
    suffix = Path(file_path).suffix.lower()
    if suffix not in {".md", ".txt", ".markdown"}:
        return _error(code=403, msg="仅支持写入 .md / .txt 文件")

    try:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        Path(file_path).write_text(content, encoding="utf-8")
        return _success({"file_path": file_path})
    except Exception as e:
        logger.error(f"保存身份定位失败: {e}", exc_info=True)
        return _error_internal(e, default_msg="保存失败，请检查文件路径和权限")


# ===== MCP 检索接口 =====

async def llm_filter_by_titles(topic: str, file_list: List[Dict], llm_config: Dict, top_n: int = 15) -> List[int]:
    """
    用 LLM 从全量标题列表中筛选出与 topic 最相关的文件
    
    Args:
        topic: 用户主题/关键词
        file_list: [{relative_path, title, name}, ...]
        llm_config: {base_url, api_key, model, timeout}
        top_n: 返回最相关的 N 个
        
    Returns:
        排序后的文件索引列表（最相关在前）
    """
    if not file_list:
        return []
    if not topic:
        return list(range(min(len(file_list), top_n)))

    # 构建标题列表文本
    lines = []
    for i, f in enumerate(file_list):
        title = f.get("title", "") or f.get("name", "")
        lines.append(f"{i+1}. {title}")
    title_text = "\n".join(lines)

    prompt = f"""你有以下 {len(file_list)} 篇文档的标题列表：

{title_text}

用户想找与「{topic}」相关的文档。
请返回最相关的 {top_n} 篇的编号（按相关度从高到低排序）。
只返回编号，每行一个，例如：
3
7
12
不需要任何解释。"""

    base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = llm_config.get("api_key", "")
    model = V4_FLASH
    timeout = llm_config.get("timeout", 60)

    try:
        result = await _call_llm(
            session_id=None,
            call_name="mcp_title_filter",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            phase="文件过滤",
        )
        text = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        
        # 解析编号
        indices = []
        for line in text.split("\n"):
            line = line.strip()
            if line.isdigit():
                idx = int(line) - 1
                if 0 <= idx < len(file_list):
                    indices.append(idx)
        
        if not indices:
            # 解析失败，回退
            return list(range(min(len(file_list), top_n)))
        
        return indices
    except Exception as e:
        logger.warning(f"LLM 标题筛选异常: {e}")
        return list(range(min(len(file_list), top_n)))


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
    
    if not session_id:
        return _error(code=400, msg="缺少 session_id")
        
    try:
        # Step 1: 扫描所有绑定的文件夹，获取全量标题列表
        llm_config_for_filter = _get_config("llm")
        all_title_files = []  # [{relative_path, title, name, folder_path}]
        folder_readers = {}   # folder_path -> reader (复用)
        
        for folder_path in folders:
            try:
                reader = LocalFolderReader(folder_path)
                folder_readers[folder_path] = reader
                titles = reader.list_file_titles()
                for t in titles:
                    t["folder_path"] = folder_path
                all_title_files.extend(titles)
            except Exception as e:
                logger.warning(f"扫描文件夹失败 {folder_path}: {e}")
                
        if not all_title_files:
            return _success({
                "summary": f"未找到与「{topic}」相关的内容。请尝试其他关键词或添加更多文件夹。",
                "source_files": [],
                "file_count": 0,
                "summary_type": "no_result",
            })

        logger.info(f"MCP 检索: 全量标题 {len(all_title_files)} 个，使用 LLM 筛选与「{topic}」相关的文件")
        
        # Step 2: LLM 筛选最相关的 15 篇
        filtered_indices = await llm_filter_by_titles(topic, all_title_files, llm_config_for_filter, top_n=15)
        target_title_files = [all_title_files[i] for i in filtered_indices if i < len(all_title_files)]
        
        if not target_title_files:
            return _success({
                "summary": f"未找到与「{topic}」相关的内容。请尝试其他关键词或添加更多文件夹。",
                "source_files": [],
                "file_count": 0,
                "summary_type": "no_result",
            })
        
        source_files = [f["name"] for f in target_title_files]
        logger.info(f"MCP 检索: LLM 筛选到 {len(target_title_files)} 个文件: {source_files[:10]}{'...' if len(source_files) > 10 else ''}")
        
        # Step 3: 读取全文（最多 5 个文件，控制 token 使用）
        max_files = 5
        target_files_with_content = []
        for f in target_title_files[:max_files]:
            fp = f["path"]
            fpath = Path(fp)
            reader_key = f["folder_path"]
            try:
                reader = folder_readers.get(reader_key) or LocalFolderReader(reader_key)
                content_text = fpath.read_text(encoding="utf-8", errors="ignore")
                target_files_with_content.append({
                    "name": f["name"],
                    "path": fp,
                    "content": content_text,
                })
            except Exception as e:
                logger.warning(f"读取文件失败 {f['name']}: {e}")
        
        if not target_files_with_content:
            return _success({
                "summary": f"与「{topic}」相关的文件存在但读取失败。",
                "source_files": source_files,
                "file_count": len(target_title_files),
                "summary_type": "no_result",
            })
        
        # Step 4: 拼接上下文
        context_parts = []
        for c in target_files_with_content:
            context_parts.append(f"## {c['name']}\n\n{c['content']}")
        context = "\n\n---\n\n".join(context_parts)

        # Step 5: 调用 LLM 总结
        llm_config = _get_config("llm")
        base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
        api_key = llm_config.get("api_key", "")
        model = V4_FLASH
        timeout = llm_config.get("timeout", 30)
        
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
        
        result = await _call_llm(
            session_id=None,
            call_name="mcp_search_summary",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0,
            seed=42,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            phase="MCP检索",
        )
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
            "file_count": len(target_title_files),
            "summary_type": "ok",
        })
        
    except Exception as e:
        logger.error(f"MCP 检索失败: {e}", exc_info=True)
        return _error_internal(e)


# ===== MCP 题材推荐接口 =====

# ---- Phase 1: 语义切片 + 密度评分工具函数 ----

def _extract_front_matter(content: str) -> str:
    """提取 Markdown Front Matter（YAML 三明治）"""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            return content[:end + 3]
    return ""


def _extract_headers(content: str) -> str:
    """提取 H1/H2 标题列表"""
    headers = re.findall(r"^#{1,2}\s+(.+)$", content, re.M)
    if not headers:
        return ""
    return "\n".join(f"- {h}" for h in headers)


def _find_safe_cut_point(text: str, max_len: int) -> int:
    """
    在 text 中找安全的截断点，截断点必须在：
    - 句号后
    - 或换行后
    - 或代码块结束标记（```）后
    - 或表格行结束后
    禁止在代码块中间或表格中间断开
    """
    if len(text) <= max_len:
        return len(text)
    
    # 检查 max_len 位置是否在代码块内
    code_block_starts = [m.start() for m in re.finditer(r"```", text[:max_len])]
    inside_code_block = len(code_block_starts) % 2 == 1
    
    # 如果在代码块内，回退到代码块结束位置
    if inside_code_block:
        # 找到最近的代码块开始位置之前
        last_code_start = code_block_starts[-1] if code_block_starts else 0
        # 回退到代码块开始前的安全位置
        search_start = last_code_start - 5
        if search_start < 100:
            search_start = 100  # 至少保留一些内容
        text_before_code = text[:last_code_start]
        if text_before_code:
            return _find_safe_cut_point(text_before_code, len(text_before_code) - 1)
        return max_len
    
    # 检查是否在表格行内（| 开头或包含 |）
    line_start = text.rfind("\n", 0, max_len)
    if line_start < 0:
        line_start = 0
    line_at_cut = text[line_start:max_len]
    if "|" in line_at_cut and line_at_cut.strip().startswith("|"):
        # 在表格内，找到表格开始前
        table_start = text.rfind("\n\n", 0, max_len)
        if table_start < 0:
            table_start = text.rfind("\n", 0, max_len)
        if table_start > 50:
            return table_start
        return max_len
    
    # 正常情况：从句号或换行处断开
    # 从 max_len 位置往回找最近的句号或换行
    safe_chars = [".", "\n", "。", "！", "？", ")", "）", "】", "」"]
    for i in range(max_len, max(50, max_len - 200), -1):
        if text[i] in safe_chars:
            # 额外检查：不在代码块内
            code_marks_before = len(re.findall(r"```", text[:i]))
            if code_marks_before % 2 == 0:
                return i + 1
    
    # 兜底：在最近一个换行处断开
    last_nl = text.rfind("\n", 0, max_len)
    if last_nl > 50:
        return last_nl
    
    return max_len


def smart_truncate(content: str, max_chars: int = 1500) -> str:
    """
    语义切片：保留文件骨架，不在代码块/表格中间截断
    
    保留顺序:
    1. Front Matter（完整保留）
    2. H1/H2 标题列表（理解结构）
    3. 第一段（凤头）
    4. 中间内容（安全截断）
    5. 最后一段（豹尾）
    """
    if not content or len(content) <= max_chars:
        return content
    
    parts = []
    used = 0
    
    # 1. Front Matter
    fm = _extract_front_matter(content)
    if fm:
        parts.append(fm)
        used += len(fm) + 2
        content_body = content[len(fm):].lstrip("\n")
    else:
        content_body = content
    
    # 2. Headers
    headers = _extract_headers(content_body)
    if headers:
        header_block = f"## 文章结构\n{headers}"
        parts.append(header_block)
        used += len(header_block) + 2
    
    # 3 & 4 & 5. 正文：首段 + 中间 + 尾段
    remaining = max_chars - used - 50  # 预留 [...] 标记空间
    if remaining < 200:
        remaining = 200
    
    paragraphs = content_body.split("\n\n")
    if len(paragraphs) <= 3:
        # 短文直接保留
        body_text = content_body[:remaining]
        parts.append(body_text)
    else:
        first_p = paragraphs[0] if paragraphs else ""
        last_p = paragraphs[-1] if len(paragraphs) > 1 else ""
        
        # 首段（不超过 remaining 的 30%）
        first_part = first_p[:int(remaining * 0.3)]
        parts.append(f"【开篇】\n{first_part}")
        
        # 中间内容
        middle = content_body[len(first_p):]
        if last_p and len(paragraphs) > 1:
            middle = content_body[len(first_p):-len(last_p)]
        
        middle_max = remaining - len(first_part) - min(len(last_p), 300) - 100
        if middle_max > 100:
            cut = _find_safe_cut_point(middle, middle_max)
            if cut > 0:
                parts.append("\n[...内容截断...]\n")
                parts.append(middle[:cut].rstrip())
        
        # 尾段
        if last_p:
            parts.append(f"\n[...内容截断...]\n【结论】\n{last_p[:300]}")
    
    return "\n\n".join(parts)


def calc_heuristic_density(content: str) -> float:
    """
    启发式信息密度估算 (0.0-1.0)
    
    优先读 Front Matter 的 density 字段
    兜底用启发式公式:
      structure(最多0.5) + 干货(最多0.4) × 长度惩罚
    
    A) Front Matter density 字段 → 直接使用（如果存在）
    B) 启发式估算
    """
    # A: Front Matter density 字段优先
    fm = _extract_front_matter(content)
    if fm:
        match = re.search(r"density\s*:\s*([0-9.]+)", fm)
        if match:
            try:
                val = float(match.group(1))
                return round(max(0.0, min(1.0, val)), 2)
            except ValueError:
                pass
    
    # B: 启发式估算
    if not content or len(content.strip()) < 50:
        return 0.1
    
    # 结构分：标题 + 列表 + 代码块 + 表格
    h_count = len(re.findall(r"^#{1,3}\s", content, re.M))
    list_count = len(re.findall(r"^\s*[-*+]\s|^\s*\d+\.\s", content, re.M))
    code_blocks = len(re.findall(r"```", content))
    code_count = code_blocks // 2 if code_blocks >= 2 else 0
    table_count = len(re.findall(r"^\|.+\|", content, re.M))
    
    structure = min(0.5, h_count * 0.05 + list_count * 0.02 + code_count * 0.1 + table_count * 0.08)
    
    # 干货分：代码块权重高
    substance = min(0.4, code_count * 0.15 + table_count * 0.12)
    
    # 长度惩罚
    length = len(content)
    if length < 300:
        penalty = 0.5
    elif length < 800:
        penalty = 0.7
    elif length > 8000:
        penalty = 0.8
    else:
        penalty = 1.0
    
    return round(min(1.0, (structure + substance) * penalty), 2)


def _calc_file_score(file_info: Dict) -> float:
    """
    文件质量评分（密度优先 + 时效性）
    
    formula: score = density × log(max(word_count, 1)) × 0.9^years_since_mtime
    """
    import math
    
    content = file_info.get("_full_content", "")
    density = calc_heuristic_density(content)
    word_count = max(len(content.split()), 1)
    density_factor = math.log(max(word_count, 1))
    
    # 时效性因子
    mtime_str = file_info.get("mtime", "")
    import datetime as dt
    try:
        if isinstance(mtime_str, (int, float)):
            mtime = dt.datetime.fromtimestamp(mtime_str)
        else:
            mtime = dt.datetime.fromisoformat(mtime_str.replace("Z", "+00:00"))
            if mtime.tzinfo:
                mtime = mtime.replace(tzinfo=None)
        years = (dt.datetime.now() - mtime).days / 365.25
        recency = 0.9 ** max(years, 1.0)
    except Exception:
        recency = 0.81  # 默认 ~2年
    
    score = density * density_factor * recency
    return round(score, 2)


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


def _get_category_display_name(cat_key: str) -> str:
    """分类键名 → 中文业务名称"""
    try:
        from src.classifier import ContentClassifier
        cats = ContentClassifier({}).get_categories()
        if cat_key in cats:
            return cats[cat_key].get("name", cat_key)
    except Exception:
        pass
    # 兜底映射
    _FALLBACK = {
        "ai-models": "模型技术", "ai-products": "AI产品",
        "industry": "行业洞察", "paper": "学术研究",
        "tip": "实战技巧", "case": "实战案例",
        "methodology": "方法论", "tool": "工具教程",
        "trend": "行业趋势", "personal": "个人品牌",
    }
    return _FALLBACK.get(cat_key, cat_key)


def _get_category_business_name(cat_key: str) -> str:
    """分类键名 → 完整中文业务名称（用于业务解释）"""
    try:
        from src.classifier import ContentClassifier
        cats = ContentClassifier({}).get_categories()
        if cat_key in cats:
            return f"{cats[cat_key].get('name', cat_key)}（{cats[cat_key].get('description', '')}）"
    except Exception:
        pass
    _FULL = {
        "ai-models": "模型技术（大模型发布、评测、架构演进）",
        "ai-products": "AI产品（工具/平台/应用发布与更新）",
        "industry": "行业洞察（政策、趋势、融资、商业模式）",
        "paper": "学术研究（论文、研究报告、技术突破）",
        "tip": "实战技巧（教程、经验、最佳实践）",
        "case": "实战案例（具体企业/项目的AI落地复盘）",
        "methodology": "方法论（系统化框架、思维模型）",
        "tool": "工具教程（AI工具的操作指南）",
        "trend": "行业趋势（市场分析、前景判断）",
        "personal": "个人品牌（博主运营、增长方法论）",
    }
    return _FULL.get(cat_key, cat_key)


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
    session_id = request.get("session_id", "")
    
    if not folders:
        return _error(code=400, msg="缺少 folders 参数")
    
    if not session_id:
        return _error(code=400, msg="缺少 session_id")
    
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
            return await _auto_recommend_topics(session_id, folders)
        
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
        model = V4_FLASH
        timeout = llm_config.get("timeout", 60)
        
        persona_content = _get_persona_summary()
        persona_context = f"\n\n作者身份定位：\n{persona_content}" if persona_content else ""
        
        prompt = f"""你是一个专业的选题策划师。请分析以下资料，推荐 3-5 个值得写的文章题材。

【上下文信息】
*   本次扫描文件数：{len(source_files)} 篇（展示前 {max_files} 篇的内容摘要）
*   搜索目录：{', '.join(folders)}

资料列表：
{', '.join(source_files)}

资料内容摘要：
{context[:4000]}
{persona_context}

【推理约束】
1.  **严禁编造数字**：提及文档数量时必须使用「本次扫描文件数：{len(source_files)} 篇」，严禁使用"50篇"、"上百篇"等虚构数字。
2.  **使用观察性语言**：描述总结时用事实陈述，禁止过程性修辞。
    *   ❌ 错误："基于对50篇素材的聚类分析，通过高频关键词交叉印证……"
    *   ✅ 正确："本次扫描了 {len(source_files)} 篇资料，主要集中在XX领域。建议以下写作方向：……"

要求：
1. 分析这批资料涵盖的主题
2. 推荐 3-5 个写作方向，每个方向包含：
   - name: 方向名称（如"技术深度分析"）
   - description: 一句话描述写什么
   - coverage: 资料覆盖度 0-1（浮点数）
   - reason: 为什么值得写（50 字内），**仅评价方向与作者定位/读者匹配度，严禁提及素材（案例/ROI/数据/时效/密度等）**
   - needed: 需要补充什么（由系统素材雷达提供，你可留空）
   - direction_score: 方向适合度 0-100（该方向与作者定位的匹配程度，非素材完整度）
   - direction_analysis: 为什么适合这个方向（30 字内），**仅评价方向与人设匹配，严禁提及素材**
3. 返回 JSON 格式（不要 markdown 代码块）：
{{
    "topics": [
        {{"name": "...", "description": "...", "coverage": 0.8, "reason": "...", "needed": "", "direction_score": 85, "direction_analysis": "..."}}
    ],
    "summary": "这批资料的整体情况（100字内，必须使用真实文件数 {len(source_files)} 篇）"
}}

评分说明：
- direction_score（方向适合度）：该方向与作者定位、读者群体的匹配程度，0-100分
- 素材完整度由系统雷达另行计算（案例数/ROI/管理者视角/时效/密度），你不需要输出 material_score/deficiency_details

请直接返回 JSON：
"""
        
        result = await _call_llm(
            session_id=session_id,
            call_name="MCP题材推荐",
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0,
            max_tokens=4096,
            seed=42,
            timeout=timeout,
            phase="选题",
        )
        
        content = result["choices"][0]["message"]["content"].strip()
        content = content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        try:
            parsed = json_mod.loads(content)
        except (json_mod.JSONDecodeError, ValueError):
            parsed = _safe_json_parse(content, "topics")
        
        topics = parsed.get("topics", [])
        summary = parsed.get("summary", "")
        
        # ━━━━ 统一后处理：用 Python 计算素材雷达信号（客观数据），覆盖 LLM 的主观猜测 ━━━━
        if topics:
            # 构建 all_docs_map（用于向量匹配和证据统计）
            all_docs_map = {}
            for f in unique_files:
                try:
                    folder = f.get("folder_path") or folders[0]
                    reader = LocalFolderReader(folder)
                    results = reader.read_files([f["path"]])
                    for c in results:
                        key = c.get("name", c.get("path", ""))
                        all_docs_map[key] = {
                            "_full_content": c.get("content", ""),
                            "name": c.get("name", ""),
                            "path": c.get("path", ""),
                        }
                except Exception as e:
                    logger.warning(f"读取文件失败 {f.get('name', '')}: {e}")
            
            # 对每个方向用 Python 客观计算素材信号
            for t in topics:
                try:
                    scores = calculate_material_scores(t["name"], all_docs_map)
                    # 保留 LLM 的 direction_* 字段，覆盖 material_* 字段
                    t["material_score"] = scores.get("material_score", t.get("material_score", 50))
                    t["deficiency_details"] = scores.get("deficiency_details", [])
                    t["satisfied_details"] = scores.get("satisfied_details", [])
                    t["signal_report"] = scores.get("signal_report", {})
                except Exception as e:
                    logger.warning(f"素材信号计算失败 {t.get('name', '')}: {e}")
        
        return _success({
            "topics": topics,
            "summary": summary,
            "source_files": source_files,
            "file_count": len(unique_files),
        })
        
    except Exception as e:
        logger.error(f"MCP 题材分析失败: {e}", exc_info=True)
        return _error_internal(e)


@router.post("/api/mcp/match-files")
async def mcp_match_files(request: Dict = Body(...)):
    """
    按主题匹配文件并返回内容（不调 LLM，纯关键词匹配 + 文件读取）
    请求体: { topic: str, folders: [str] }
    返回: { matched_files: [{name, path, content}], total: int }
    """
    topic = request.get("topic", "").strip()
    folders = request.get("folders", [])

    if not folders:
        return _error(code=400, msg="缺少 folders 参数")
    if not topic:
        return _error(code=400, msg="缺少 topic 参数")

    try:
        all_matched_files = []
        for folder_path in folders:
            try:
                reader = LocalFolderReader(folder_path)
                files = reader.list_files(keyword=topic, limit=50)
                for f in files:
                    f["folder_path"] = folder_path
                all_matched_files.extend(files)
            except Exception as e:
                logger.warning(f"扫描文件夹失败 {folder_path}: {e}")

        if not all_matched_files:
            return _success({
                "matched_files": [],
                "total": 0,
            })

        # 去重（按相对路径）
        seen_paths = set()
        unique_files = []
        for f in all_matched_files:
            rel = f.get("relative_path", f["path"])
            if rel not in seen_paths:
                seen_paths.add(rel)
                unique_files.append(f)

        logger.info(f"MCP match-files: 关键词「{topic}」匹配到 {len(unique_files)} 个文件")

        # 读取全部匹配文件的内容（上限 30 个，防止 payload 过大）
        max_files = 30
        target_files = unique_files[:max_files]
        target_paths = [f["path"] for f in target_files]

        # 按文件夹分组读取（不同文件夹可能需要不同的 reader）
        content_map = {}
        for target in target_files:
            try:
                folder = target["folder_path"]
                reader = LocalFolderReader(folder)
                results = reader.read_files([target["path"]])
                for c in results:
                    content_map[c["name"]] = c["content"]
            except Exception as e:
                logger.warning(f"读取文件失败 {target.get('name', '')}: {e}")
                content_map[target.get("name", "")] = ""

        matched_files = []
        for f in unique_files[:max_files]:
            matched_files.append({
                "name": f["name"],
                "path": f.get("relative_path", f["path"]),
                "content": content_map.get(f["name"], ""),
            })

        return _success({
            "matched_files": matched_files,
            "total": len(unique_files),
        })

    except Exception as e:
        logger.error(f"MCP match-files 失败: {e}", exc_info=True)
        return _error_internal(e)


async def _auto_recommend_topics(session_id: str, folders: List[str]):
    """自动推荐值得写的话题：按分类统计后推荐（支持大规模知识库）"""
    try:
        from datetime import datetime, timedelta
        import time as _time
        import random
        
        session = _get_session(session_id)
        
        _t0 = _time.time()
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
        
        # 记录扫描结果
        # 计算文件大小和修改时间范围
        total_size = sum(f.get("size", 0) for f in all_file_basenames.values())
        total_size_kb = total_size / 1024
        mtimes = [f.get("mtime", 0) for f in all_file_basenames.values() if f.get("mtime", 0) > 0]
        time_range = ""
        if mtimes:
            from datetime import datetime
            newest = datetime.fromtimestamp(max(mtimes)).strftime("%Y-%m-%d")
            oldest = datetime.fromtimestamp(min(mtimes)).strftime("%Y-%m-%d")
            time_range = f"，时间跨度 {oldest} ~ {newest}"
        
        # 文件列表摘要（最多列 10 个，超出省略）
        all_names = [f.get("name", f.get("relative_path", "?")) for f in all_file_basenames.values()]
        name_list = "、".join(all_names[:10])
        if len(all_names) > 10:
            name_list += f" 等共 {len(all_names)} 篇"
        
        _log_process_step(
            session_id=session_id,
            call_name="文件夹扫描",
            phase="选题",
            steps=[
                {"step": 1, "action": f"扫描 {len(folders)} 个知识库目录", 
                 "reason": f"遍历目录下所有 .md 文件，按路径自动去重",
                 "result": f"找到 {total_count} 篇 Markdown 文档（去重后）"},
                {"step": 2, "action": "文件概览",
                 "reason": f"总大小 {total_size_kb:.0f} KB{time_range}",
                 "result": f"文件列表：{name_list}"},
            ],
            output=f"扫描完成：{total_count} 篇文档，总 {total_size_kb:.0f} KB",
            duration=_time.time() - _t0,
        )
        _scan_end = _time.time()
        
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
        
        # 记录分类结果
        cat_display = [_get_category_display_name(k) for k in category_counts]
        
        # 构建每个类别下的文件明细
        classify_steps = [
            {"step": 1, "action": "逐篇读取文章内容", 
             "reason": f"共 {total_count} 篇文档，读取全文用于分类和后续分析",
             "result": f"成功读取 {len(unique_files)} 篇，{total_count - len(unique_files)} 篇读取失败"},
        ]
        classify_steps.append({
            "step": 2, "action": "按业务领域自动归类",
            "reason": f"根据文章 Front Matter 标签和正文内容，自动识别所属业务领域（模型技术/AI产品/行业洞察/学术研究/实战技巧等）",
            "result": f"分成 {len(category_counts)} 个类别（{', '.join(cat_display)}），{len(uncategorized)} 篇未归类"
        })
        
        # 每类下列出具体文件
        step_idx = 3
        for cat_key, files in category_counts.items():
            cat_name = _get_category_display_name(cat_key)
            file_names = "、".join([f["name"] for f in files[:8]])
            if len(files) > 8:
                file_names += f" 等 {len(files)} 篇"
            classify_steps.append({
                "step": step_idx,
                "action": f"「{cat_name}」类：{len(files)} 篇",
                "reason": f"这些文章主要涉及该领域的实操、理论或案例",
                "result": file_names
            })
            step_idx += 1
        
        _log_process_step(
            session_id=session_id,
            call_name="内容分类",
            phase="选题",
            steps=classify_steps,
            output=f"分类完成：{len(category_counts)} 个类别（{', '.join(cat_display)}），{len(uncategorized)} 篇未归类",
            duration=_time.time() - _scan_end,
        )
        _classify_end = _time.time()
        
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
        
        # ========== Phase 1: 密度优先 + 多样性兜底精选 ==========
        # Step 3: 为每个文件计算质量评分
        for f in unique_files:
            f["_quality_score"] = _calc_file_score(f)
            f["_density"] = calc_heuristic_density(f.get("_full_content", ""))
        
        # 识别动态锚点（信息密度最高的 3 个文件）
        all_sorted = sorted(unique_files, key=lambda x: x["_density"], reverse=True)
        anchors = all_sorted[:3]
        anchor_names = [a["name"] for a in anchors]
        anchor_densities = [f"{a['_density']:.2f}" for a in anchors]
        
        # 构建每篇锚点的详细信息
        anchor_steps = [{
            "step": 1, 
            "action": "识别信息密度最高的核心文档",
            "reason": "在所有文档中，按信息密度（结构完整度 + 干货含量 × 长度系数）排序，找到知识库中最具代表性的基石文档",
            "result": f"从 {len(unique_files)} 篇中筛选出 Top 3 锚点文档"
        }]
        for idx, a in enumerate(anchors, 2):
            word_cnt = len(a.get("_full_content", "").split())
            anchor_steps.append({
                "step": idx,
                "action": f"锚点文档：{a['name']}",
                "reason": f"信息密度 {a['_density']:.0%}，全文约 {word_cnt} 词，质量和完整度在同类中领先",
                "result": f"作为核心代表文件送入后续精选和 LLM 分析"
            })
        
        _log_process_step(
            session_id=session_id,
            call_name="动态锚点识别",
            phase="选题",
            steps=anchor_steps,
            output=f"动态锚点: {', '.join(anchor_names)}",
            duration=0,
        )

        # Step 4: 密度优先 + 多样性兜底精选（最多 10 篇）
        MAX_SELECT = 10
        selected = []
        selection_tags = {}  # {path: "保底"|"补位"} 标记每篇的入选原因
        
        # 4a: 每类保底 1 篇（多样性兜底）
        for cat_key, cat_files in category_counts.items():
            if not cat_files:
                continue
            best = max(cat_files, key=lambda x: x.get("_quality_score", 0))
            selected.append(best)
            selection_tags[best["path"]] = f"保底（{_get_category_display_name(cat_key)}类Top1）"

        # 4b: 未分类也保底 1 篇
        if uncategorized:
            best_uncat = max(uncategorized, key=lambda x: x.get("_quality_score", 0))
            selected.append(best_uncat)
            selection_tags[best_uncat["path"]] = "保底（未分类Top1）"

        # 4c: 剩余名额按全局 score 降序补位
        selected_paths = {f["path"] for f in selected}
        remaining_slots = MAX_SELECT - len(selected)
        all_others = [f for f in all_sorted if f["path"] not in selected_paths]
        for f in all_others[:remaining_slots]:
            selected.append(f)
            selection_tags[f["path"]] = "补位（全局高分）"
        
        # 重新按分类排序（保证输出有序）
        selected.sort(key=lambda x: x.get("_quality_score", 0), reverse=True)
        
        llm_results = []
        selection_details = []
        for f in selected:
            content = smart_truncate(f.get("_full_content", ""), max_chars=1500)
            if content:
                llm_results.append(f"## {f['name']}\n\n{content}")
            cats = _classify_file(f)
            cat_key = cats[0] if cats else "未分类"
            cat_str = _get_category_display_name(cat_key)
            selection_details.append(f"{f['name']}(密度{f['_density']:.2f}, 分{f['_quality_score']:.0f}, {cat_str})")
        
        context = "\n\n---\n\n".join(llm_results)
        total_tokens = sum(len(f.get("_full_content", "").split()) for f in selected)

        # 记录精选过程（业务语言，带每篇明细）
        selection_steps = [
            {"step": 1, "action": "密度优先排序",
             "reason": "综合评分公式：信息密度 × 内容规模 × 时效系数。三维度兼顾文章质量、篇幅深度和新鲜度",
             "result": f"从 {len(unique_files)} 篇候选文档中按综合质量评分排序"},
            {"step": 2, "action": "多样性兜底——每类保底至少 1 篇",
             "reason": f"共 {len(category_counts)} 个业务类别，每类选质量最高的 1 篇确保覆盖面，避免单一领域垄断选题",
             "result": f"各类别均已覆盖，无遗漏"},
        ]
        
        # 每篇入选文件的明细
        step_idx = 3
        for f in selected:
            tag = selection_tags.get(f["path"], "入选")
            score = f.get("_quality_score", 0)
            density = f.get("_density", 0)
            word_cnt = len(f.get("_full_content", "").split())
            cats = _classify_file(f)
            cat_name = _get_category_display_name(cats[0]) if cats else "未分类"
            selection_steps.append({
                "step": step_idx,
                "action": f"入选：{f['name']}",
                "reason": f"质量分 {score:.0f}，信息密度 {density:.0%}，约 {word_cnt} 词，属「{cat_name}」领域，{tag}",
                "result": "已纳入 LLM 上下文用于选题推荐"
            })
            step_idx += 1
        
        selection_steps.append({
            "step": step_idx,
            "action": "语义切片——保留文章骨架",
            "reason": "每篇文档截取标题结构、开头和结尾，中间按段落安全截断，不打断代码块和表格，确保 LLM 理解文章核心",
            "result": f"最终上下文约 {sum(len(f.get('_full_content', '').split()) for f in selected)} 词，{len(context)} 字符"
        })
        
        _log_process_step(
            session_id=session_id,
            call_name="密度优先精选",
            phase="选题",
            steps=selection_steps,
            output=f"精选 {len(selected)} 篇文档送入 LLM 分析",
            duration=_time.time() - _classify_end,
        )

        # 记录排除的关键文件
        excluded_notable = [f for f in all_sorted[15:18] if f["_density"] > 0.5 and f["path"] not in selected_paths]
        if excluded_notable:
            excluded_names = [f"{e['name']}(密度{e['_density']:.2f})" for e in excluded_notable]
            _log_process_step(
                session_id=session_id,
                call_name="排除说明",
                phase="选题",
                steps=[
                    {"step": 1, "action": "高分但未入选的文件", 
                     "reason": "已满 10 篇上限，需在所有类别保底后被挤出",
                     "result": f"排除: {', '.join(excluded_names)}"},
                ],
                output=f"排除了 {len(excluded_notable)} 篇高质量文件（名额已满）",
                duration=0,
            )
        
        # ========== Phase 1.5: 向量检索增强（10 篇代表 + 最多 5 篇向量召回） ==========
        _recall_t0 = _time.time()
        try:
            recall_result = await recall_with_dedup(selected, top_k=5)
            if isinstance(recall_result, dict):
                recalled = recall_result.get("recalled", [])
                recalled_excluded = recall_result.get("excluded", [])
                total_searched = recall_result.get("total_searched", 0)
            else:
                # 兼容旧格式（list）
                recalled = recall_result or []
                recalled_excluded = []
                total_searched = len(recalled)
        except Exception as e:
            logger.warning(f"[Vector] 召回异常（非致命）: {e}")
            recalled = []
            recalled_excluded = []
            total_searched = 0
        
        _recall_duration = _time.time() - _recall_t0
        
        if recalled:
            # 将召回文件的 content 追加到上下文
            for f in recalled:
                truncated = smart_truncate(f.get("_full_content", ""), max_chars=1200)
                if truncated:
                    llm_results.append(f"## [向量召回] {f['name']} (相似度 {f.get('_recall_score', 0):.2f})\n\n{truncated}")
                    selection_details.append(f"{f['name']}(召回, 分{f['_recall_score']:.2f})")
            
            context = "\n\n---\n\n".join(llm_results)
        
        # 记录向量召回日志
        recall_steps = [
            {"step": 1, "action": "语义向量搜索", 
             "reason": f"用密度精选的 {len(selected)} 篇代表文件构造语义查询，在全量 {len(unique_files)} 篇知识库中检索语义相似的文件",
             "result": f"搜索完成，共检索 {total_searched} 篇候选"},
            {"step": 2, "action": "去重检查",
             "reason": "与密度精选结果逐篇对比文件名和路径，排除重复，确保不浪费上下文空间",
             "result": f"去重后新增 {len(recalled)} 篇，排除 {len(recalled_excluded)} 篇重复"},
        ]
        
        # 召回的每篇文件单独列出详情
        if recalled:
            for idx, f in enumerate(recalled, 1):
                recall_steps.append({
                    "step": f"2.{idx}", 
                    "action": f"召回文件：{f['name']}",
                    "reason": f"与已有代表文件语义相似度 {f.get('_recall_score', 0):.0%}，内容相关度高",
                    "result": f"已加入上下文，文件名：{f['name']}，相似度：{f.get('_recall_score', 0):.0%}"
                })
        
        # 被排除的文件说明
        if recalled_excluded:
            for idx, e in enumerate(recalled_excluded, 1):
                recall_steps.append({
                    "step": f"2.{len(recalled) + idx}",
                    "action": f"排除：{e['name']}",
                    "reason": e.get("reason", "重复"),
                    "result": f"相似度 {e.get('score', 0):.0%} 但已存在，不重复加入"
                })
        
        if not recalled and not recalled_excluded and total_searched == 0:
            recall_steps.append({
                "step": 2, "action": "无新增文件", 
                "reason": "向量索引为空或模型未就绪，跳过此步骤不影响选题主流程",
                "result": "合并上下文仍为密度精选结果"
            })
        
        _log_process_step(
            session_id=session_id,
            call_name="混合检索（向量召回）",
            phase="选题",
            steps=recall_steps,
            output=f"向量召回新增 {len(recalled)} 篇，排除 {len(recalled_excluded)} 篇重复，合并共 {len(selected) + len(recalled)} 篇上下文",
            duration=_recall_duration,
        )
        
        # ========== 新选题管道：Step 2 提名 → Python 算分 → Step 5 评分 ==========
        # Step 1.5: 确保向量索引已就绪（首次使用此文件夹时自动构建）
        ensure_index_load(folders)
        _pipeline_t0 = _time.time()
        
        persona_content = _get_persona_summary()
        
        # 构建 all_docs_map（多路径索引 → 完整信息，供 calculate_material_scores 使用）
        all_docs_map = {}
        for f in unique_files:
            full_path = f["path"]
            all_docs_map[full_path] = f
            # 同时用绝对路径索引
            abs_path = os.path.abspath(full_path) if not os.path.isabs(full_path) else full_path
            all_docs_map[abs_path] = f
            # 同时用纯文件名索引（去目录前缀）
            base_name = os.path.basename(full_path)
            if base_name not in all_docs_map:
                all_docs_map[base_name] = f
        
        llm_config = _get_config("llm")
        model = V4_FLASH
        timeout = llm_config.get("timeout", 60)
        
        # Step 2: LLM 提名方向（只看宏观分布，不碰具体内容）
        cat_dist_lines = []
        for cat_key, cat_files in sorted(category_counts.items(), key=lambda x: len(x[1]), reverse=True):
            cat_name = _get_category_display_name(cat_key)
            cat_dist_lines.append(f"    *   {cat_name}：{len(cat_files)} 篇")
        cat_dist_str = "\n".join(cat_dist_lines) if cat_dist_lines else "（无分类数据）"
        
        anchor_lines = []
        for i, a in enumerate(anchors[:3], 1):
            anchor_lines.append(f"    {i}. {a['name']}（密度 {a['_density']:.0%}）")
        anchor_str = "\n".join(anchor_lines) if anchor_lines else "（无锚点文档）"
        
        nom_prompt = NOMINATION_PROMPT.format(
            persona_content=persona_content or "（未设置身份定位）",
            total_files=total_count,
            category_distribution=cat_dist_str,
            anchor_docs=anchor_str,
        )
        
        nom_result = await _call_llm(
            session_id=session_id,
            call_name="方向提名",
            messages=[{"role": "user", "content": nom_prompt}],
            model=model,
            temperature=0.3,
            max_tokens=2000,
            seed=42,
            timeout=timeout,
            phase="选题",
        )
        
        nom_content = nom_result["choices"][0]["message"]["content"].strip()
        nom_content = nom_content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        nom_parsed = json_mod.loads(nom_content)
        nominated = nom_parsed.get("nominated_directions", [])
        logger.info(f"[Pipeline] Step 2 提名: {len(nominated)} 个方向")
        
        # Step 3: Python 对每个提名方向计算 material_score
        directions_with_scores = []
        for d in nominated:
            score_data = calculate_material_scores(d["name"], all_docs_map)
            directions_with_scores.append({
                "name": d["name"],
                "description": d.get("description", ""),
                "material_score": score_data["material_score"],
                "related_count": score_data["related_count"],
                "evidence_counts": score_data["evidence_counts"],
                "latest_update_days": score_data["latest_update_days"],
                "avg_density": score_data["avg_density"],
                "deficiency_details": score_data["deficiency_details"],
                "satisfied_details": score_data.get("satisfied_details", []),
                "signal_report": score_data.get("signal_report", {}),
                "matched_docs": score_data.get("matched_docs", []),
            })
        logger.info(f"[Pipeline] Step 3 素材评分: {len(directions_with_scores)} 个方向")
        
        # Step 4: LLM 评分（看到精选文档 + 预计算 material_score）
        formatted_docs = format_selected_docs(selected)
        
        scoring_prompt = SCORING_PROMPT.format(
            persona_content=persona_content or "（未设置身份定位）",
            selected_docs_content=formatted_docs,
            directions_json=json_mod.dumps(directions_with_scores, ensure_ascii=False, indent=2),
        )
        
        score_result = await _call_llm(
            session_id=session_id,
            call_name="选题评分",
            messages=[{"role": "user", "content": scoring_prompt}],
            model=model,
            temperature=0,
            max_tokens=3000,
            seed=42,
            timeout=timeout,
            phase="选题",
        )
        
        score_content = score_result["choices"][0]["message"]["content"].strip()
        score_content = score_content.replace("```json", "").replace("```", "").strip()
        parsed = json_mod.loads(score_content)
        
        topics = parsed.get("topics", [])
        summary = parsed.get("summary", "")
        
        # Step 5: Python 后处理 —— 计算 overall_score + 排序 + 截断 Top 5
        for topic in topics:
            # ══ 评分容错：setdefault 无法拦截 LLM 显式返回 0 的情况 ══
            dir_score = topic.get("direction_score", 0)
            material = topic.get("material_score", 0)
            coverage = topic.get("coverage", 0)
            
            # 1) coverage 为 0 或缺失 → 从 material_score 推导或设默认值
            if coverage == 0 or coverage is None:
                if material > 0:
                    topic["coverage"] = round(material / 100, 2)
                else:
                    topic["coverage"] = 0.5  # 默认中等覆盖
                coverage = topic["coverage"]
            
            # 2) direction_score 为 0 → 从 coverage 推导（参考方向分析的容错逻辑）
            if dir_score <= 0:
                topic["direction_score"] = max(20, int(coverage * 80))
                dir_score = topic["direction_score"]
            
            # 3) material_score 为 0 → 从 direction_score + coverage 推导
            if material <= 0:
                topic["material_score"] = max(20, int(dir_score - 40 + coverage * 50))
                material = topic["material_score"]
            
            topic["overall_score"] = round(dir_score * 0.6 + material * 0.4)
            # 计算公式透明化（供前端 hover tooltip 使用）
            topic["_score_formula"] = f"{dir_score}×0.6 + {material}×0.4 = {topic['overall_score']}"
            topic["coverage"] = round(material / 100, 2)
        
        topics.sort(key=lambda x: x["overall_score"], reverse=True)
        topics = topics[:5]
        
        # 将 Step 3 计算的 deficiency_details 精确附加到每个 topic
        # 匹配策略：精确匹配 → 子串匹配 → 计算包含最多的作为候选
        def _fuzzy_match(name, candidates):
            # 先精确匹配
            exact = [d for d in candidates if d["name"] == name]
            if exact:
                return exact[0]
            # 再子串匹配
            sub = [d for d in candidates if name in d["name"] or d["name"] in name]
            if sub:
                return max(sub, key=lambda d: len(d["name"]))
            return None
        
        for topic in topics:
            matched = _fuzzy_match(topic["name"], directions_with_scores)
            if matched:
                topic["_material_detail"] = matched
                details = matched.get("deficiency_details", [])
                satisfied = matched.get("satisfied_details", [])
                signal_report = matched.get("signal_report", {})
                logger.debug(f"[Radar] 匹配成功: {topic['name'][:30]}... → signal_details={len(signal_report.get('signal_details', []))}")
            else:
                # 模糊匹配失败，直接用 LLM 返回的 topic name 重新计算素材信号
                logger.warning(f"[Radar] 模糊匹配失败，重新计算: {topic['name'][:30]}...")
                try:
                    recalc = calculate_material_scores(topic["name"], all_docs_map)
                    details = recalc.get("deficiency_details", [])
                    satisfied = recalc.get("satisfied_details", [])
                    signal_report = recalc.get("signal_report", {})
                except Exception:
                    details = []
                    satisfied = []
                    signal_report = {}
            
            # ═════ 保底：如果 signal_report 缺失但 deficiency/satisfied 存在，反向构造 ═════
            if not signal_report.get("signal_details") and (details or satisfied):
                good_count = len(satisfied)
                total_count = len(details) + len(satisfied)
                if total_count == 0:
                    total_count = 5
                
                # 从 deficiency/satisfied 反向组装 signal_details
                signal_details = []
                for d in details:
                    label = d.get("item", "")
                    signal_details.append({
                        "key": label,
                        "label": label,
                        "ok": False,
                        "detail": d.get("explanation", ""),
                    })
                for d in satisfied:
                    label = d.get("item", "")
                    signal_details.append({
                        "key": label,
                        "label": label,
                        "ok": True,
                        "detail": d.get("explanation", ""),
                    })
                
                # 计算 verdict
                ng_count = len([s for s in signal_details if not s.get("ok")])
                if ng_count == 0:
                    verdict, vlevel = "素材充足，可直接撰写", "good"
                elif ng_count <= 2:
                    verdict, vlevel = "素材部分缺失，建议针对性补充", "warn"
                else:
                    verdict, vlevel = "素材严重不足，建议暂存为灵感或补充调研", "bad"
                
                signal_report = {
                    "signals": {},
                    "good_count": good_count,
                    "total_count": total_count,
                    "verdict": verdict,
                    "verdict_level": vlevel,
                    "signal_details": signal_details,
                }
                logger.debug(f"[Radar] 反向构造 signal_report: {topic['name'][:30]}... good={good_count}, total={total_count}")
            
            mat = topic.get("material_score", 0)
            
            topic["deficiency_details"] = details
            topic["satisfied_details"] = satisfied
            topic["signal_report"] = signal_report
            # 雷达匹配文档：选题 → 写作桥梁
            radar_matched = matched.get("matched_docs", []) if matched else []
            
            topic["evaluation"] = {
                "direction_score": topic.get("direction_score", 0),
                "material_score": mat,
                "deficiency_score": 100 - mat,
                "overall_score": topic["overall_score"],
                "direction_analysis": topic.get("direction_analysis", topic.get("reason", "")),
                "deficiency_details": details,
                "satisfied_details": satisfied,
                "signal_report": signal_report,
                "matched_docs": radar_matched,
                "supplement_strategy": "信息充足" if mat >= 70 else "需补充关键信息" if mat >= 40 else "素材严重不足",
            }
        
        logger.info(f"[Pipeline] Step 5 后处理: {len(topics)} 个最终选题, 耗时 {_time.time() - _pipeline_t0:.1f}s")
        
        # 保存到 session 供后续步骤（角度推荐等）使用
        session["mcp_summary"] = summary
        session["mcp_topics"] = topics
        # 雷达上下文：选题 → 写作桥梁，保存每个方向的匹配文档坐标
        if "radar_context" not in session:
            session["radar_context"] = {"topics": []}
        session["radar_context"]["topics"] = [
            {"name": t["name"], "matched_docs": t.get("evaluation", {}).get("matched_docs", []),
             "deficiency_details": t.get("evaluation", {}).get("deficiency_details", []),
             "satisfied_details": t.get("evaluation", {}).get("satisfied_details", []),
             "signal_report": t.get("evaluation", {}).get("signal_report", {}),
            }
            for t in topics
        ]
        # 手递手日志
        _write_handoff_log(session_id, "选题推荐", "补充 Step 1",
            f"传递 {len(topics)} 个选题方向到下一步，"
            f"雷达已为每个方向匹配 {len(session['radar_context']['topics'][0].get('matched_docs', []))} 篇文档，"
            f"共 {sum(len(t.get('evaluation', {}).get('matched_docs', [])) for t in topics)} 篇（去重）")
        
        return _success({
            "topics": topics,
            "summary": summary,
            "source_files": list(all_file_basenames.keys()),
            "file_count": total_count,
        })
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"自动推荐失败: {e}\n{error_detail}")
        return _success({
            "topics": [
                {"name": "综合分析报告", "description": "从多个维度全面分析", "coverage": 0.5, "reason": "通用题材", "needed": "具体数据"},
            ],
            "summary": f"分析失败: {str(e)[:200]}，请重试。",
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
_sessions_lock = asyncio.Lock()  # 保护 AIPULSE 后台任务与主请求的并发写入

def _get_session(session_id: str) -> Dict:
    """获取或创建会话状态。使用 setdefault 保证原子性创建。"""
    session = _sessions.setdefault(session_id, {
        "mcp_summary": "",
        "mcp_files": [],
        "completeness": 0,
        "supplement_count": 0,
        "check_count": 0,
        "step1": {},
        "step2": {},
        "step3": {},
        "outline": [],
        "material_pool": [],
        "confirmed_slots": [],
        "slot_materials": {},
        "slot_outlines": {},
        "radar_context": {  # 选题 → 写作桥梁：每个方向的雷达匹配文档
            "topics": [],  # [{name, matched_docs: [{path, abs_path, name, score}]}]
        },
    })
    # 确保 V4 字段存在（兼容旧 session，setdefault 原子化）
    session.setdefault("material_pool", [])
    session.setdefault("confirmed_slots", [])
    session.setdefault("slot_materials", {})
    session.setdefault("slot_outlines", {})
    return session


async def _get_session_for_async(session_id: str) -> Dict:
    """异步获取 session（用于后台任务，加锁防止并发写入冲突）"""
    async with _sessions_lock:
        return _get_session(session_id)


@router.post("/api/workflow/session/create")
async def create_session(request: Dict = Body(default={})):
    """创建新会话，可选传入 MCP 素材"""
    session_id = str(uuid.uuid4())[:8]
    _sessions[session_id] = {
        "mcp_summary": request.get("mcp_summary", ""),
        "mcp_files": request.get("mcp_files", []),
        "mcp_topic": request.get("mcp_topic", ""),
        "completeness": 0,
        "supplement_count": 0,
        "check_count": 0,
        "step1": {},
        "step2": {},
        "step3": {},
        "outline": [],
        "material_pool": [],
        "confirmed_slots": [],
        "slot_materials": {},
        "slot_outlines": {},
    }
    logger.info(f"Session {session_id} 创建，MCP 文件: {len(_sessions[session_id]['mcp_files'])}个")
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
    model = V4_FLASH
    timeout = llm_config.get("timeout", 60)
    
    # 获取身份定位信息（使用 _get_persona_summary 有回退逻辑）
    persona_summary = ""
    try:
        persona_summary = _get_persona_summary()
    except:
        pass
    
    # 获取已保存的补充内容（草稿、智能补充等）
    supplements_text = ""
    try:
        from pathlib import Path
        supplements_dir = Path(__file__).parent / "data" / "supplements"
        supp_file = supplements_dir / f"{session_id}.json"
        if supp_file.exists():
            import json
            with open(supp_file, "r", encoding="utf-8") as f:
                supplements_data = json.load(f)
            if supplements_data:
                supplements_text = "\n【已补充内容】\n"
                for item_id, item_data in supplements_data.items():
                    item_text = item_data.get("text", "")
                    if item_text:
                        supplements_text += f"- {item_id}: {item_text[:300]}...\n"
    except Exception as e:
        logger.warning(f"读取补充内容失败: {e}")
    
    prompt = f"""你是一个内容策划专家（门卫模式）。请评估以下素材的信息完整度，用于生成文章。

核心原则：抓大放小。你正在评估的是一份草稿，不是最终成品。允许内容不够完美，但不允许方向错误。

【MCP 素材摘要】
{mcp_summary}

【作者身份定位】
{persona_summary}
{supplements_text}

请从以下 3 个维度评估（每个 0-100分）：

1. 方向适合度（direction_score）：该素材适合写什么类型/方向的内容？评估素材与主流写作方向（如干货教程、行业分析、案例拆解、观点评论等）的匹配程度。说明适合什么方向。

2. 内容缺失度（deficiency_score）：素材中缺少哪些关键内容？如身份定位缺失、具体案例缺失、数据支撑缺失等。逐项说明每项缺了什么、为什么重要。

3. 综合评分（overall_score）：综合以上两个维度，给出文章可写性的整体评分。

返回 JSON 格式（不要 markdown 代码块）：
{{
  "completeness": 0-100的数字（与 overall_score 相同，用于兼容旧版UI），
  "direction_score": 0-100,
  "direction_analysis": "该素材适合写XX方向/类型的内容，因为...（具体说明为什么适合这个方向）",
  "deficiency_score": 0-100,
  "deficiency_details": [
    {{"item": "缺失项具体名称", "severity": "high/medium/low", "explanation": "为什么缺失、有什么影响、缺失在哪里"}}
  ],
  "overall_score": 0-100,
  "supplement_strategy": "补充策略描述（先补什么、再补什么）",
  "missing_critical": ["关键缺失项1 - 必须补充", "关键缺失项2 - 必须补充"],
  "missing_optional": ["可选缺失项1 - 建议补充", "可选缺失项2 - 建议补充"]
}}

direction_analysis 示例：
- 好的："该素材核心讨论了AI在中小企业财务自动化中的应用场景，包含具体工具选型和技术路线对比，适合写「AI行业应用案例拆解」方向"
- 差的："素材不太完整"（太模糊）

deficiency_details 示例：
- {{"item": "作者身份定位文件", "severity": "high", "explanation": "未找到身份定位文件（persona.md），无法确定内容视角和立场，建议补充作者身份信息"}}
- {{"item": "具体案例数据", "severity": "medium", "explanation": "缺少具体的行业案例或数据支撑，建议补充1-2个真实案例"}}

规则（门卫模式 - 严格执行）：
- overall_score >= 70: 信息基本充足，可以进入下一步
- overall_score 50-69: 需要补充后再推进
- overall_score < 50: 素材严重不足，建议先补充基础素材

missing_critical 只包含以下3种情况（缺一不可，严格限制）：
1. 方向严重偏离：素材与选定方向完全无关
2. 实质性空白：核心模块完全没有文字
3. 事实性冲突：补充内容与已知事实直接矛盾

以下情况 ABSOLUTELY NOT 列入 missing_critical（即使完全没有也要放到 missing_optional）：
- 没有案例 → 放到 missing_optional
- 没有数据 → 放到 missing_optional
- 案例不够具体 → 放到 missing_optional
- 数据是推断/假设的 → 放到 missing_optional
- 结构组织不够好 → 放到 missing_optional
- 语言不够优美 → 放到 missing_optional
- 目标读者不够细化 → 放到 missing_optional

记住：你的任务是判断"能不能继续写"，不是"写得好不好"。

请直接返回 JSON：
"""
    
    try:
        logger.info(f"开始评估完整度, session: {session_id}")
        # 走 _call_llm，自动记录日志
        result = await _call_llm(
            session_id=session_id,
            call_name="完整度评估",
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0,
            max_tokens=1024,
            seed=42,
            timeout=httpx.Timeout(30, connect=10),
            phase="补充",
        )
        
        parsed_content = result["choices"][0]["message"]["content"].strip()
        parsed_content = parsed_content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        evaluation = json_mod.loads(parsed_content)
        
        session["completeness"] = evaluation.get("completeness", 0)
        session["supplement_count"] = evaluation.get("supplement_count", 3)
        
        # 丰富最近一条日志的 thinking_chain：完整度评估详情
        logs = session.get("thinking_logs", [])
        if logs:
            last = logs[-1]
            chain = [{"step": 1, "action": "完整度综合评估", "reason": "评估素材信息完整度，判断是否可以继续写作", "result": f"完整度评分：{session['completeness']}分，建议补充{session['supplement_count']}次"}]
            missing_critical = evaluation.get("missing_critical", [])
            missing_optional = evaluation.get("missing_optional", [])
            step_idx = 2
            for item in missing_critical:
                chain.append({"step": step_idx, "action": f"关键缺失项：{item}", "reason": f"缺失项：{item}，严重程度：必须补充，否则无法继续写作", "result": "标记为必须补充项"})
                step_idx += 1
            for item in missing_optional:
                chain.append({"step": step_idx, "action": f"可选缺失项：{item}", "reason": f"缺失项：{item}，严重程度：建议补充，但不阻塞写作流程", "result": "标记为建议补充项"})
                step_idx += 1
            if not missing_critical and not missing_optional:
                chain.append({"step": 2, "action": "缺失项检查", "reason": "素材信息基本完整，未发现明显缺失", "result": "无关键缺失项，可直接进入下一步"})
            last["thinking_chain"] = chain
        
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
    mcp_files = request.get("mcp_files", [])  # 前端传入的 MCP 文件列表
    
    session = _get_session(session_id)
    
    # 持久化到 session（兼容后续步骤）
    if mcp_files and not session.get("mcp_files"):
        session["mcp_files"] = mcp_files
        logger.info(f"[Directions] 持久化 MCP 文件到 session: {len(mcp_files)}个")
    
    llm_config = _get_config("llm")
    base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = llm_config.get("api_key", "")
    model = V4_FLASH
    timeout = llm_config.get("timeout", 60)
    
    persona_summary = ""
    try:
        persona_summary = _get_persona_summary()
    except:
        pass

    # 收集 MCP 文件内容（优先用请求传入的，否则从 session 读）
    mcp_files_block = ""
    all_mcp_files = (mcp_files if mcp_files else session.get("mcp_files", []))
    if isinstance(all_mcp_files, list) and all_mcp_files:
        mcp_files_block = "\n【MCP 知识库文件】\n"
        for f in all_mcp_files[:15]:
            if isinstance(f, dict):
                name = f.get("name", f.get("filename", f.get("path", "unknown")))
                content = f.get("text", f.get("content", f.get("summary", "")))
                if content:
                    mcp_files_block += f"\n--- {name} ---\n{content[:500]}\n"
            elif isinstance(f, str):
                mcp_files_block += f"\n- {f[:300]}\n"

    # 收集补充素材信息（step2）
    step2_supplement = session.get("step2", {}).get("supplement_2", {})
    supplement_text_block = ""
    if isinstance(step2_supplement, dict):
        files = step2_supplement.get("files", [])
        if files:
            supplement_text_block += "\n【用户补充文件】\n"
            for f in files[:5]:
                supplement_text_block += f"- {f.get('name','')}: {f.get('content','')[:300]}\n"
        mats = step2_supplement.get("materials", [])
        if mats:
            supplement_text_block += "\n【AI推断素材】\n"
            for m in mats[:5]:
                supplement_text_block += f"- {m.get('title','')}: {m.get('content','')[:300]}\n"
        text = step2_supplement.get("text", "")
        if text:
            supplement_text_block += f"\n【用户自述补充】\n{text[:500]}"

    prompt = f"""你是一个内容策划专家。请基于以下素材，推荐4-5个写作方向。

【MCP 素材摘要】
{mcp_summary[:2000]}
{mcp_files_block}

【作者身份定位】
{persona_summary}

{supplement_text_block}

═══════════ 透明推理原则（必须严格执行）═══════════
1. 每个方向必须有推荐理由（基于素材中的哪一点）
2. 标注推荐来源：
   - user_content: 直接从素材推导
   - user_implied: 素材隐含但未明说
   - general_knowledge: 基于通用领域知识
3. 提供4-5个选项，不替用户做决定
4. 标注置信度：high/medium/low（由你判断，基于素材充分度）

═══════════ 生成原则 ═══════════
- 如果素材不足，标注 confidence=low，不要编造
- 如果推荐基于通用知识，标注 source=general_knowledge
- 每个方向必须具体可操作，不要泛泛而谈
- evidence_quote 可选：如果能准确引用素材原文就加上，不能则留空字符串

请推荐4-5个写作方向，返回 JSON 格式（不要 markdown 代码块）：
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
    "frameworks": ["推荐框架1", "推荐框架2"],
    "direction_score": 85,
    "direction_analysis": "该素材适合写此方向，因为...",
    "deficiency_score": 70,
    "deficiency_details": [
      {{"item": "缺失项名称", "severity": "high/medium/low", "explanation": "为什么缺失、有什么影响"}}
    ],
    "overall_score": 78
  }}
]

最后增加一个推荐字段：
{{
  "directions": [...],
  "recommendation": "主张型",
  "recommendation_reason": "你的素材有明确主张语气，且有反面质疑（适合做驳论）"
}}

每个方向的 3 个评分说明：
- direction_score（方向适合度）：该素材与这个方向的匹配程度，0-100分
- deficiency_score（内容完整度）：写这个方向时素材的完整程度，0-100分（越高越完整）
- overall_score（综合评分）：综合以上两个维度，0-100分

请直接返回 JSON：
"""
    
    try:
        import time
        # 走 _call_llm，自动记录日志
        result = await _call_llm(
            session_id=session_id,
            call_name="方向分析",
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0,
            max_tokens=4096,
            seed=42,
            timeout=timeout,
            phase="选题",
        )
        
        parsed_content = result["choices"][0]["message"]["content"].strip()
        parsed_content = parsed_content.replace("```json", "").replace("```", "").strip()
        import json as json_mod
        try:
            result_data = json_mod.loads(parsed_content)
        except json_mod.JSONDecodeError as e:
            logger.warning(f"方向推荐 JSON 解析失败: {e}, 尝试修复...")
            # 尝试截断到最后一个完整的 } 后再拼一个 }
            last_complete = _try_repair_json(parsed_content)
            try:
                result_data = json_mod.loads(last_complete)
            except json_mod.JSONDecodeError:
                return _error(msg=f"方向推荐返回格式异常: {str(e)[:100]}")
        
        # ═══════════════════════════════════════════════════════
        # 置信度优化：风险加权置信度（MEMORY.md 2026-06-21 决策）
        # 公式：effective_confidence = raw_confidence * SOURCE_RISK_MAP[source_type]
        # - anchored (user_content): 1.0 全额有效
        # - inferred (user_implied/general_knowledge): 0.3 打 3 折
        # ═══════════════════════════════════════════════════════
        
        # ══ 关键词匹配计算 coverage ══
        import re
        from collections import Counter
        
        all_materials_text = []
        # MCP 文件内容
        for f in session.get("mcp_files", []) or []:
            if isinstance(f, dict):
                name = f.get("name", f.get("filename", ""))
                content = f.get("text", f.get("content", ""))
                if name: all_materials_text.append(name)
                if content: all_materials_text.append(content[:2000])
        
        # 补充素材
        supplement = session.get("step2", {}).get("supplement_2", {})
        if isinstance(supplement, dict):
            for f in supplement.get("files", []) or []:
                name = f.get("name", "")
                content = f.get("content", "")
                if name: all_materials_text.append(name)
                if content: all_materials_text.append(content[:2000])
            for m in supplement.get("materials", []) or []:
                title = m.get("title", "")
                content = m.get("content", "")
                if title: all_materials_text.append(title)
                if content: all_materials_text.append(content[:2000])
        
        def extract_keywords(text):
            cn = re.findall(r'[\u4e00-\u9fa5]{2,}', str(text))
            en = re.findall(r'[A-Za-z]{3,}', str(text))
            return [w.lower() for w in cn + en]
        
        all_keywords = []
        for text in all_materials_text:
            all_keywords.extend(extract_keywords(text))
        
        keyword_counts = Counter(all_keywords)
        significant_keywords = {w for w, c in keyword_counts.items() if c >= 2}
        
        def calc_coverage_by_keywords(direction):
            if not significant_keywords:
                return 0.4 if all_materials_text else 0.25
            dir_text = str(direction.get("name", "")) + " " + str(direction.get("description", ""))
            dir_keywords = set(extract_keywords(dir_text))
            match_count = len(dir_keywords & significant_keywords)
            total_count = len(dir_keywords) if len(dir_keywords) > 0 else 1
            return round(min(match_count / total_count * 1.5, 0.95), 2)
        
        SOURCE_RISK_MAP = {
            "user_content": 1.0,      # 锚定事实：全额有效
            "user_implied": 0.3,      # AI 推断：打 3 折
            "general_knowledge": 0.3, # 通用知识：打 3 折
        }
        
        CONFIDENCE_VALUE_MAP = {
            "high": 0.9,
            "medium": 0.6,
            "low": 0.3,
        }
        
        def calculate_effective_confidence(direction: dict) -> dict:
            """计算有效置信度并添加展示字段"""
            source = direction.get("source", "user_implied")
            raw_confidence = direction.get("confidence", "medium")
            
            # 计算风险系数
            risk_factor = SOURCE_RISK_MAP.get(source, 0.3)
            
            # 计算原始置信度数值
            raw_value = CONFIDENCE_VALUE_MAP.get(raw_confidence, 0.6)
            
            # 计算有效置信度
            effective_value = raw_value * risk_factor
            
            # 生成展示标签和颜色
            if source == "user_content":
                # anchored: 高确定性
                confidence_label = f"✅ 高确定性 ({int(effective_value * 100)}%)"
                confidence_color = "green"
                confidence_tooltip = "基于知识库原文，可信度高"
            else:
                # inferred: 高风险推断
                confidence_label = f"🔴 高风险推断 ({int(effective_value * 100)}%)"
                confidence_color = "red"
                confidence_tooltip = "纯 AI 生成，请务必核验"
            
            direction["effective_confidence"] = round(effective_value, 2)
            direction["confidence_label"] = confidence_label
            direction["confidence_color"] = confidence_color
            direction["confidence_tooltip"] = confidence_tooltip
            direction["source_type"] = "anchored" if source == "user_content" else "inferred"
            
            return direction
        
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
                d.setdefault("direction_score", 0)
                d.setdefault("direction_analysis", "")
                d.setdefault("deficiency_score", 0)
                d.setdefault("deficiency_details", [])
                d.setdefault("overall_score", 0)
                
                # ══ 统一推导：setdefault 无法拦截 LLM 显式返回 0 的情况 ══
                dir_score = d.get("direction_score", 0)
                def_score = d.get("deficiency_score", 0)
                coverage = d.get("coverage", 0)
                
                # 1) coverage 为 0 或缺失 → 关键词匹配重新计算
                if coverage == 0 or coverage is None:
                    d["coverage"] = calc_coverage_by_keywords(d)
                coverage = d["coverage"]
                
                # 2) direction_score 为 0 → 从 coverage 推导
                if dir_score <= 0:
                    d["direction_score"] = max(20, int(coverage * 80))
                    dir_score = d["direction_score"]
                
                # 3) deficiency_score 为 0 → 从 direction_score + coverage 推导
                if def_score <= 0:
                    d["deficiency_score"] = max(20, int(dir_score - 40 + coverage * 50))
                
                # 4) overall_score 为 0 → 综合 direction_score + deficiency_score 推导
                if d.get("overall_score", 0) <= 0:
                    d["overall_score"] = min(int(0.6 * d["direction_score"] + 0.4 * d["deficiency_score"]), 90)
                
                # 校验字段值
                if d.get("source") not in valid_sources:
                    d["source"] = "user_implied"
                if d.get("confidence") not in valid_confidence:
                    d["confidence"] = "medium"
                
                # 应用置信度优化
                calculate_effective_confidence(d)
            
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
                d.setdefault("direction_score", 0)
                d.setdefault("direction_analysis", "")
                d.setdefault("deficiency_score", 0)
                d.setdefault("deficiency_details", [])
                d.setdefault("overall_score", 0)
                
                # ══ 统一推导：setdefault 无法拦截 LLM 显式返回 0 的情况 ══
                dir_score = d.get("direction_score", 0)
                def_score = d.get("deficiency_score", 0)
                coverage = d.get("coverage", 0)
                
                if coverage == 0 or coverage is None:
                    d["coverage"] = calc_coverage_by_keywords(d)
                coverage = d["coverage"]
                
                if dir_score <= 0:
                    d["direction_score"] = max(20, int(coverage * 80))
                    dir_score = d["direction_score"]
                
                if def_score <= 0:
                    d["deficiency_score"] = max(20, int(dir_score - 40 + coverage * 50))
                
                if d.get("overall_score", 0) <= 0:
                    d["overall_score"] = min(int(0.6 * d["direction_score"] + 0.4 * d["deficiency_score"]), 90)
                
                if d.get("source") not in valid_sources:
                    d["source"] = "user_implied"
                if d.get("confidence") not in valid_confidence:
                    d["confidence"] = "medium"
                
                calculate_effective_confidence(d)
            
            result_data = {
                "directions": result_data,
                "recommendation": "",
                "recommendation_reason": "",
            }
        
        return _success(result_data)
    except Exception as e:
        logger.error(f"方向推荐失败: {e}")
        return _error_internal(e)


@router.post("/api/workflow/directions/evaluate")
async def evaluate_user_direction(request: Dict = Body(...)):
    """评估用户自定义方向（根据 MCP 素材 + 补充素材打分）"""
    import time
    start_time = time.time()
    
    session_id = request.get("session_id", "")
    custom_direction = request.get("direction", "").strip()
    
    if not session_id or not custom_direction:
        return _error(code=400, msg="缺少 session_id 或 direction")
    
    session = _get_session(session_id)
    
    llm_config = _get_config("llm")
    base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = llm_config.get("api_key", "")
    model = V4_FLASH
    timeout = llm_config.get("timeout", 60)
    
    if not api_key:
        return _error(msg="LLM 未配置")
    
    # 收集素材
    mcp_summary = session.get("mcp_summary", "")
    step2_supplement = session.get("step2", {}).get("supplement_2", {})
    supplement_text_block = ""
    if isinstance(step2_supplement, dict):
        files = step2_supplement.get("files", [])
        if files:
            supplement_text_block += "\n【用户补充文件】\n"
            for f in files[:5]:
                supplement_text_block += f"- {f.get('name','')}: {f.get('content','')[:300]}\n"
        mats = step2_supplement.get("materials", [])
        if mats:
            supplement_text_block += "\n【AI推断素材】\n"
            for m in mats[:5]:
                supplement_text_block += f"- {m.get('title','')}: {m.get('content','')[:300]}\n"
        text = step2_supplement.get("text", "")
        if text:
            supplement_text_block += f"\n【用户自述补充】\n{text[:500]}"
    
    persona_summary = ""
    try:
        persona_summary = _get_persona_summary()
    except:
        pass
    
    prompt = f"""你是一个内容策划专家。请评估用户自定义的写作方向是否适合当前素材。

【用户自定义方向】
{custom_direction}

【MCP 素材摘要】
{mcp_summary}

【用户补充素材】
{supplement_text_block}

【作者身份定位】
{persona_summary}

请评估这个方向，返回 JSON（不要 markdown 代码块）：
{{
  "direction_score": 0-100,
  "direction_analysis": "评估理由（50-100字）",
  "deficiency_score": 0-100,
  "deficiency_details": [
    {{"item": "缺失内容", "severity": "high/medium/low", "explanation": "说明"}}
  ],
  "overall_score": 0-100,
  "suggestion": "改进建议（50字内）"
}}"""
    
    try:
        result = await _call_llm(
            session_id=session_id,
            call_name="evaluate_direction",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.1,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            phase="方向评估",
        )
        content = result["choices"][0]["message"]["content"].strip()
        content = content.replace("```json", "").replace("```", "").strip()
        import json as jmod
        data = jmod.loads(content)
        data.setdefault("direction_score", 0)
        data.setdefault("deficiency_score", 0)
        data.setdefault("overall_score", 0)
        data.setdefault("direction_analysis", "")
        data.setdefault("deficiency_details", [])
        data.setdefault("suggestion", "")

        # ══ 统一推导：setdefault 无法拦截 LLM 显式返回 0 的情况 ══
        dir_score = data.get("direction_score", 0)
        def_score = data.get("deficiency_score", 0)
        overall_score = data.get("overall_score", 0)
        
        # direction_score 为 0 → LLM 未正确打分，给合理默认
        if dir_score <= 0:
            data["direction_score"] = 50
            dir_score = 50
        
        # deficiency_score 为 0 → 从 direction_score 推导
        if def_score <= 0:
            data["deficiency_score"] = max(20, int(dir_score - 30))
        
        # overall_score 为 0 → 综合推导
        if overall_score <= 0:
            data["overall_score"] = min(int(0.6 * dir_score + 0.4 * data["deficiency_score"]), 90)

        _log_llm_call_legacy(session_id, "step1_evaluate_direction", "方向评估", messages=[{"role": "user", "content": prompt}], result=content, duration=time.time() - start_time, thinking_chain=[
            {"step": 1, "action": "评估用户自定义方向", "reason": f"针对用户指定的方向「{custom_direction}」，评估其与当前素材的匹配度", "result": f"评估完成：方向评分{data.get('direction_score', 0)}，综合评分{data.get('overall_score', 0)}"},
        ])

        return _success(data)
    except Exception as e:
        logger.error(f"自定义方向评估失败: {e}")
        _log_llm_call_legacy(session_id, "step1_evaluate_direction", "方向评估", messages=[{"role": "user", "content": prompt}], error=str(e), thinking_chain=[
            {"step": 1, "action": "方向评估失败", "reason": f"评估方向「{custom_direction}」时发生错误", "result": "评估中断"},
        ])
        return _error_internal(e)

def _safe_json_parse(raw: str, fallback_key: str = "themes") -> dict:
    """安全解析 LLM 返回的 JSON，处理未转义换行等常见格式问题"""
    import re as _re
    
    # 尝试直接解析
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    
    # 尝试提取第一个完整 JSON 对象
    try:
        brace_start = raw.index("{")
        brace_end = raw.rindex("}") + 1
        return json.loads(raw[brace_start:brace_end])
    except (ValueError, json.JSONDecodeError):
        pass
    
    # 修复 JSON 字符串值内的未转义换行（LLM 常见输出问题）
    try:
        brace_start = raw.index("{")
        brace_end = raw.rindex("}") + 1
        json_candidate = raw[brace_start:brace_end]
        # 状态机：跟踪是否在 JSON 字符串内，将字符串内的裸换行替换为 \n
        fixed = []
        in_string = False
        escape_next = False
        for ch in json_candidate:
            if escape_next:
                fixed.append(ch)
                escape_next = False
                continue
            if ch == '\\':
                fixed.append(ch)
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                fixed.append(ch)
                continue
            if in_string and ch == '\n':
                fixed.append('\\n')
                continue
            fixed.append(ch)
        return json.loads(''.join(fixed))
    except (ValueError, json.JSONDecodeError):
        pass
    
    # 最后兜底：返回空结果
    logger.warning(f"_safe_json_parse 失败，raw 前 200 字符: {raw[:200]}")
    return {fallback_key: [], "reasoning": raw[:500]}


def _build_angle_context_prompt(angle_context: dict) -> str:
    """根据角度上下文构造 prompt 片段。无角度上下文时返回默认要求。"""
    if not angle_context or not angle_context.get("angle_name"):
        # 无角度上下文：通用默认
        return """请设计 4-8 个内容槽位（slot），每个槽位代表文章的一个逻辑模块。要求：
1. 槽位应有逻辑递进关系（从浅入深/从现象到本质）
2. 每个槽位的名称应简洁（2-6个字）
3. 每个槽位需要有简短描述（10字以内说明这个模块要写什么）

返回 JSON 格式（不要 markdown 代码块）：
{{
  "thinking": "你的分析思考过程（100-200字），请明确提及读取到的素材数量",
  "slots": [
    {{"slot_key": "slot_1", "label": "槽位名称", "description": "简短描述"}}
  ]
}}"""
    
    # 有角度上下文：构造结构化指令
    angle_name = angle_context.get("angle_name", "")
    angle_desc = angle_context.get("angle_desc", "")
    coverage = angle_context.get("coverage")
    gaps = angle_context.get("gaps", [])
    dimensions = angle_context.get("dimensions", [])
    source = angle_context.get("source", "topic")
    
    source_label = {"material": "素材驱动（基于已有文件素材推荐）", "topic": "题目驱动（基于题目语义分析）", "custom": "自定义角度"}.get(source, source)
    
    parts = []
    parts.append(f"""【写作角度约束】
你正在为以下写作角度设计槽位：
- 角度名称：{angle_name}
- 角度描述：{angle_desc}
- 角度来源：{source_label}""")
    
    # 维度信息
    if dimensions:
        dim_str = "\n".join([f"  · {d.get('name', d.get('label', '未知'))}（重要性：{d.get('severity', d.get('importance', '中'))}）" for d in dimensions])
        parts.append(f"""- 写作维度（请围绕以下维度设计槽位）：
{dim_str}""")
    
    # 覆盖度
    if coverage is not None:
        cov_pct = int(coverage * 100) if coverage <= 1 else coverage
        if cov_pct >= 70:
            cov_hint = "素材充足，可以深入设计，槽位可以更细分"
        elif cov_pct >= 40:
            cov_hint = "素材中等，槽位设计应维持适中粒度"
        else:
            cov_hint = "素材不足，槽位应聚焦核心维度，避免过度拆分，缺口相关槽位标注为需补充"
        parts.append(f"- 素材覆盖率：{cov_pct}%（{cov_hint}）")
    
    # 缺口
    if gaps:
        gaps_str = "、".join(gaps)
        parts.append(f"- 素材缺口：{gaps_str}（这些维度的素材不足，相关槽位请标注 information_gap: true）")
    
    parts.append(f"""
请设计 4-8 个内容槽位，每个槽位代表文章的一个逻辑模块。要求：
1. 槽位必须紧扣「{angle_name}」这个角度，不要偏离到泛泛的行业背景
2. 优先围绕写作维度设计槽位结构（每个核心维度对应一个槽位）
3. 素材覆盖好的维度深入拆分，缺素材的维度合并或降级
4. 每个槽位的名称应简洁（2-6个字）
5. 每个槽位需要有简短描述（10字以内）

返回 JSON 格式（不要 markdown 代码块）：
{{
  "thinking": "你的分析思考过程（100-200字），请明确提及读取到的素材数量和角度信息",
  "slots": [
    {{"slot_key": "slot_1", "label": "槽位名称", "description": "简短描述"}}
  ]
}}""")
    
    return "\n".join(parts)


def _match_radar_topic(topics: list, direction_name: str):
    """在雷达话题列表中匹配 direction_name。优先精确匹配，找不到时用编辑距离兜底。"""
    if not topics or not direction_name:
        return None
    
    # 1. 精确匹配优先
    for t in topics:
        if t.get("name") == direction_name:
            return t
    
    # 2. 编辑距离兜底：找最接近的（Levenshtein）
    best = None
    best_dist = float("inf")
    for t in topics:
        name = t.get("name", "")
        if not name:
            continue
        # Levenshtein 距离
        dist = _levenshtein(name, direction_name)
        # 归一化：距离不超过较长字符串长度的 1/2 才认为匹配
        max_len = max(len(name), len(direction_name))
        if dist < best_dist and dist <= max_len // 2:
            best_dist = dist
            best = t
    
    if best:
        logger.info(f"[_match_radar_topic] 模糊匹配: '{direction_name}' → '{best['name']}' (编辑距离={best_dist})")
    return best


def _levenshtein(s1: str, s2: str) -> int:
    """Levenshtein 编辑距离"""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insert = prev_row[j + 1] + 1
            delete = curr_row[j] + 1
            replace = prev_row[j] + (0 if c1 == c2 else 1)
            curr_row.append(min(insert, delete, replace))
        prev_row = curr_row
    return prev_row[-1]


@router.post("/api/workflow/angle/recommend")
async def recommend_angles(request: Dict = Body(...)):
    """写作角度推荐（多步推理：素材扫描 → 覆盖度评分 → 人设匹配）"""
    import time as _time

    session_id = request.get("session_id", "")
    topic = request.get("topic", "")
    mode = request.get("mode", "material")  # "material" | "topic" | "both"
    if not session_id:
        return _error(code=400, msg="缺少 session_id")
    
    session = _get_session(session_id)
    mcp_summary = session.get("mcp_summary", "")
    
    # 收集补充素材
    step2_supplement = session.get("step2", {}).get("supplement_2", {})
    supplement_text_block = ""
    if isinstance(step2_supplement, dict):
        text = step2_supplement.get("text", "")
        if text:
            supplement_text_block += f"\n【用户补充文本】\n{text[:800]}"
    
    llm_config = _get_config("llm")
    api_key = llm_config.get("api_key", "")
    
    if not api_key:
        return _success({
            "angles": [
                {"name": "案例研究型", "description": "深入拆解典型实践案例，提炼可复用经验", "coverage": 0.5},
                {"name": "工具盘点型", "description": "系统梳理工具和方法，提供实用清单", "coverage": 0.5},
                {"name": "方法论型", "description": "提炼系统化的方法框架，给出可操作步骤", "coverage": 0.5},
            ]
        })
    
    # 辅助函数：给最近一条日志替换思考链（覆盖 _call_llm 的默认值）
    def _enrich_last_log(step_num: int, step_name: str, input_summary: str, reasoning: str, output_data):
        logs = session.get("thinking_logs", [])
        if not logs:
            return
        last = logs[-1]
        last["thinking_chain"] = [{
            "step": step_num,
            "step_name": step_name,
            "input": input_summary,
            "reasoning": reasoning,
            "output": output_data,
        }]

    def _get_last_log():
        """获取最近一条 thinking_log，若不存在则返回 None"""
        logs = session.get("thinking_logs", [])
        return logs[-1] if logs else None
    
    if "thinking_logs" not in session:
        session["thinking_logs"] = []
    
    # ═══════════════════════════════════════════════════════
    # 雷达简报：从选题阶段继承信号报告，让角度推荐知道素材家底
    # ═══════════════════════════════════════════════════════
    radar_briefing = ""
    radar_ctx = session.get("radar_context", {})
    radar_topics = radar_ctx.get("topics", [])
    radar_match = _match_radar_topic(radar_topics, topic)
    
    if radar_match:
        sr = radar_match.get("signal_report", {})
        sd = sr.get("signal_details", [])
        good = sr.get("good_count", 0)
        total = sr.get("total_count", 5)
        deficiencies = radar_match.get("deficiency_details", [])
        satisfied = radar_match.get("satisfied_details", [])
        matched_docs = radar_match.get("matched_docs", [])
        doc_count = len(matched_docs)
        
        # 信号灯摘要
        signal_parts = []
        for s in sd:
            icon = "✅" if s.get("ok") else "⚠️"
            signal_parts.append(f"{icon}{s.get('label', '')}")
        signal_line = " ".join(signal_parts)
        
        # 不足项摘要
        if deficiencies:
            deficit_top = deficiencies[0]
            deficit_line = f"{deficit_top.get('item', '')} — {deficit_top.get('explanation', '')}"
        else:
            deficit_line = "无明显短板"
        
        # 匹配文档 Top5（只列文件名 + 一句话亮点）
        doc_lines = []
        for d in matched_docs[:5]:
            doc_name = d.get("name", "")
            doc_snippet = (d.get("text") or d.get("snippet") or "")[:60].replace("\n", " ")
            if doc_name:
                doc_lines.append(f"  - {doc_name} — {doc_snippet}")
        doc_text = "\n".join(doc_lines) if doc_lines else "  暂无匹配文档摘要"
        
        # 写作建议概要（取前 2 条）
        suggestions_cache = session.get("writing_suggestions", {})
        existing_suggestions = suggestions_cache.get(topic, [])
        suggestion_line = "、".join(existing_suggestions[:2]) if existing_suggestions else "案例+数据双轮驱动"
        
        radar_briefing = f"""【雷达简报｜{topic}】
■ 信号灯：{good}/{total}（{signal_line}）
■ 不足项：{deficit_line}
■ 匹配文档（{doc_count}篇，TOP5）：
{doc_text}
■ 写作建议：{suggestion_line}

以上为雷达侦察结论。推荐角度时必须显式引用雷达简报中的优势项和不足项
（如"利用现有案例优势，规避{deficiencies[0].get('item', 'XX') if deficiencies else 'XX'}不足"），
禁止忽略雷达简报凭空推荐。

"""
    
    materials_text = f"{radar_briefing}【创作主题】{topic}\n【MCP素材摘要】{mcp_summary[:2000]}\n{supplement_text_block}"
    
    try:
        # ====== Step 1: 素材扫描 / 题目分析（按 mode 分支）======
        if mode == "topic":
            # 题目驱动：分析题目本身，推荐写作角度（不依赖素材）
            step1_prompt = f"""你是 ArchGen 的「题目分析引擎」。请分析以下选题，推荐最适合的写作角度。

【选题方向】{topic}
【MCP素材摘要（仅供背景参考）】{mcp_summary[:1500] if mcp_summary else "（无）"}

分析维度：
1. 领域分类：这个选题属于什么领域？（技术/管理/商业/个人成长/产业分析等）
2. 题目复杂度：这个选题适合多深的分析？（科普级/中度分析/深度研究）
3. 受众预期：目标读者是谁？他们想看到什么？（C端流量文/B端决策文/学术严谨文）
4. 隐含痛点：读者看到这个题目，真正想解决什么问题？
5. 经典角度：这个领域最常见的写作角度有哪些？

【结果】
返回 JSON（不要 markdown 代码块）：
{{
  "themes": [
    {{"name": "写作角度名称", "description": "一句话描述此角度的切入方式", "complexity": "科普级/中度分析/深度研究", "audience": "目标读者画像",
     "materials_needed": ["需要的素材类型1", "需要的素材类型2", "需要的素材类型3"]}}
  ],
  "reasoning": "你的分析结论（含领域分类、复杂度判断、受众分析）"
}}

注意：
- 推荐的每个角度必须附带 materials_needed 清单，写明该角度需要什么类型的素材
- 角度数量 3-4 个，追求质量而非数量
- 如果题目本身信息量不足，可以让角度偏向"What/Why"而非"How"
"""
        else:
            # 素材驱动（默认）：从素材中提取核心主题域
            step1_prompt = f"""你是 ArchGen 的「素材扫描引擎」。请对以下素材做结构化审查。

素材内容：
{materials_text[:3000]}

审查任务：
逐段扫描素材，识别其中的核心话题，提炼出 3-5 个最适合展开写作的主题方向。

请按以下结构输出（标注为【推理】和【结果】）：

【推理】
1. 话题分布：素材中出现了哪些领域/话题？各自的篇幅和权重如何？
2. 高频关键词：哪些术语/概念反复出现？在什么语境下出现？
3. 上下游延伸：这些话题可以往什么方向延伸？（如：管理 → 决策框架 → 工具落地）
4. 差异化潜力：哪些话题在常见写作中较少被覆盖，有独特的切入点？
5. 信息密度评估（按以下标准）：
   - 0.3：仅提及概念，无任何细节
   - 0.5：提及概念 + 模糊案例/原则
   - 0.8：提及概念 + 2-3个具体案例/原则 + 简单解释
   - 1.0：提及概念 + 3个以上具体案例/原则 + 原理/对比/数据
6. 数据缺口：每个主题素材里明显缺失了什么？

【结果】
返回 JSON（不要 markdown 代码块）：
{{
  "themes": [
    {{"name": "主题名称", "description": "一句话描述", "frequency": "高/中/低", "importance": "核心/次要/边缘",
     "info_density": 0.8, "data_gap": "缺少的具体内容说明"}}
  ],
  "reasoning": "你的审查结论"
}}"""

        step1_result = await _call_llm(
            session_id=session_id,
            call_name="角度推荐 · 素材扫描",
            messages=[{"role": "user", "content": step1_prompt}],
            temperature=0.3, max_tokens=2048, timeout=llm_config.get("timeout", 60),
            phase="素材扫描",
        )
        
        step1_raw = step1_result["choices"][0]["message"]["content"].strip()
        step1_raw = step1_raw.replace("```json", "").replace("```", "").strip()
        if "【结果】" in step1_raw:
            step1_json_str = step1_raw.split("【结果】", 1)[1].strip()
        else:
            step1_json_str = step1_raw
        
        # 加固 JSON 提取：LLM 可能在 JSON 字符串值中嵌入未转义的换行，导致解析失败
        step1_data = _safe_json_parse(step1_json_str, "themes")
        themes = step1_data.get("themes", [])
        step1_reasoning = step1_data.get("reasoning", "") or step1_raw.split("【结果】")[0].replace("【推理】", "").strip()
        
        last = _get_last_log()
        if last:
            chain = [{"step": 1, "action": "素材审查" if mode != "topic" else "题目分析", "reason": "对全文进行结构化审查，识别核心话题、高频关键词、信息密度" if mode != "topic" else f"分析选题「{topic}」，从领域/复杂度/受众/痛点维度推荐角度", "result": f"扫描完成，识别出{len(themes)}个候选主题方向"}]
            for i, t in enumerate(themes):
                if mode == "topic":
                    materials_needed = t.get("materials_needed", [])
                    chain.append({"step": f"1.{i+1}", "action": f"候选角度「{t['name']}」", "reason": f"角度：{t['name']}（{t.get('complexity', 'N/A')}），受众：{t.get('audience', 'N/A')}，需要素材：{', '.join(materials_needed[:3])}", "result": "已纳入候选池"})
                else:
                    freq_text = {"高": "较高", "中": "中等", "低": "较低"}.get(t.get("frequency", ""), t.get("frequency", "未知"))
                    imp_text = {"核心": "核心级", "次要": "次要级", "边缘": "边缘级"}.get(t.get("importance", ""), t.get("importance", "未知"))
                    chain.append({"step": f"1.{i+1}", "action": f"候选主题「{t['name']}」", "reason": f"话题：{t['name']}，出现频率{freq_text}，重要性{imp_text}，信息密度{t.get('info_density', 0)}，缺失内容：{t.get('data_gap', '无')}", "result": "已纳入候选池"})
            last["thinking_chain"] = chain
        
        # ====== Step 2: 覆盖度评分 + 排序标注（合并，Flash 一步到位） ======
        persona_summary = ""
        try:
            persona_summary = _get_persona_summary()
        except:
            pass
        
        step2_prompt = f"""你是 ArchGen 的角度评分排序引擎。对以下候选角度做覆盖度评分 + 排序标注，一步完成。

候选角度：
{json.dumps(themes, ensure_ascii=False)}

素材概况（用于判断覆盖度）：
{materials_text[:1500]}

作者人设：
{persona_summary if persona_summary else '未配置（根据主题自动推断目标读者）'}

创作主题：{topic or '根据素材推断'}

评判规则：
1. 覆盖度 = 素材能在多大程度上支撑这个角度（0-1）
2. 角度之间必须有差异化，高度重复的进入 excluded
3. 与人设完全不兼容的进入 excluded
4. 按综合质量排序（人设匹配 > 差异化价值 > 覆盖度）
5. 覆盖度低不排除，在 material_status 标注即可

返回格式：纯 JSON，无 markdown，无推理文本。一字不多一字不少。
{{"angles":[{{"name":"角度名","description":"1-2句描述","coverage":0.85,"material_status":"充足",
"gap_summary":"缺什么素材","match_reason":"为何推荐"}}],
"excluded":[{{"name":"被排除的角度","reason":"排除原因"}}],"reasoning":"总体排序审计"}}"""

        step2_result = await _call_llm(
            session_id=session_id,
            call_name="角度推荐 · 评分排序",
            messages=[{"role": "user", "content": step2_prompt}],
            temperature=0.1, max_tokens=4096, timeout=llm_config.get("timeout", 60),
            phase="评分排序",
        )
        
        step2_raw = step2_result["choices"][0]["message"]["content"].strip()
        step2_raw = step2_raw.replace("```json", "").replace("```", "").strip()
        if "【结果】" in step2_raw:
            step2_json_str = step2_raw.split("【结果】", 1)[1].strip()
        elif "【推理】" in step2_raw and "【结果】" not in step2_raw:
            # LLM 只输出了推理没输出结果，尝试从全文提取 JSON
            step2_json_str = step2_raw
        else:
            step2_json_str = step2_raw
        step2_data = _safe_json_parse(step2_json_str, "angles")
        angles = step2_data.get("angles", [])
        excluded = step2_data.get("excluded", [])
        step2_reasoning = step2_data.get("reasoning", "") or step2_raw[:500]
        
        last = _get_last_log()
        if last:
            chain = [{"step": 2, "action": "覆盖度评分", "reason": "对每个候选角度评估素材覆盖度", "result": f"评分完成"}]
            for i, t in enumerate(themes):
                chain.append({"step": f"2.{i+1}", "action": f"角度「{t['name']}」评分", "reason": f"候选角度「{t['name']}」进入覆盖度评估", "result": "已完成覆盖度评估"})
            chain.append({"step": 3, "action": "排序标注", "reason": "结合作者人设和素材状态，对所有角度排序并标注", "result": f"入选{len(angles)}个角度，排除{len(excluded)}个"})
            for i, a in enumerate(angles):
                chain.append({"step": f"3.{i+1}", "action": f"入选角度「{a['name']}」", "reason": f"入选：{a['name']}（{a.get('material_status', 'N/A')}），入选理由：{a.get('match_reason', '与作者定位匹配')}", "result": "推荐给用户"})
            for i, e in enumerate(excluded):
                chain.append({"step": f"3.{len(angles)+i+1}", "action": f"排除角度「{e.get('name', str(e))}」", "reason": f"排除：{e.get('name', str(e))}，排除原因：{e.get('reason', '不符合当前定位')}", "result": f"不符合条件，不推荐"})
            last["thinking_chain"] = chain
        
        # 限制日志总数
        if len(session["thinking_logs"]) > 50:
            session["thinking_logs"] = session["thinking_logs"][-50:]

        return _success({"angles": angles})

    except Exception as e:
        if len(session.get("thinking_logs", [])) > 50:
            session["thinking_logs"] = session["thinking_logs"][-50:]
        logger.warning(f"角度推荐失败: {e}")
        return _error_internal(e)


@router.post("/api/workflow/angle/evaluate")
async def evaluate_custom_angle(request: Dict = Body(...)):
    """P1：自定义角度评估（Flash LLM 动态维度 + 素材池匹配）
    
    输入：session_id, angle_name, angle_description(可选)
    输出：{
        feasibility: "green"/"yellow"/"red",
        coverage: 0.0-1.0,
        dimensions: [{name, hit_count, sample_docs}],
        gaps: [{item, severity, origin:"custom"}],
        suggestions: []
    }
    """
    session_id = request.get("session_id", "")
    angle_name = (request.get("angle_name") or "").strip()
    angle_description = (request.get("angle_description") or "").strip()
    
    if not session_id:
        return _error(code=400, msg="缺少 session_id")
    if not angle_name:
        return _error(code=400, msg="缺少 angle_name")
    
    session = _get_session(session_id)
    
    # 获取 topic 和素材池
    topic = ""
    if session.get("step1", {}).get("selected_direction"):
        topic = session["step1"]["selected_direction"]
    
    # 收集素材池文档
    material_pool = session.get("material_pool", [])
    radar_ctx = session.get("radar_context", {})
    radar_topics = radar_ctx.get("topics", [])
    
    # 找到当前选题的匹配文档
    matched_docs = []
    radar_match = _match_radar_topic(radar_topics, topic)
    if radar_match:
        matched_docs = radar_match.get("matched_docs", [])
    
    # 合并素材池：雷达文档 + material_pool
    pool_docs = {}
    for d in matched_docs[:30]:
        path = d.get("abs_path") or d.get("path", "")
        name = d.get("name", "")
        snippet = (d.get("text") or d.get("snippet") or "")[:200]
        if name and name not in pool_docs:
            pool_docs[name] = {"name": name, "snippet": snippet}
    for m in material_pool[:20]:
        name = m.get("name") or m.get("file_name") or ""
        snippet = (m.get("text") or m.get("content") or "")[:200]
        if name and name not in pool_docs:
            pool_docs[name] = {"name": name, "snippet": snippet}
    
    doc_list = list(pool_docs.values())
    doc_summary = "\n".join([f"- {d['name']}: {d['snippet'][:80]}" for d in doc_list[:15]])
    
    # 获取已有的 writing_suggestions 缓存
    suggestions_cache = session.get("writing_suggestions", {})
    existing_suggestions = suggestions_cache.get(topic, [])
    
    # ── Flash LLM：动态维度推断 + 素材匹配 ──
    evaluate_prompt = f"""你是素材匹配评估专家。请根据用户自定义的写作角度，判断需要哪些素材维度，并评估当前素材池的覆盖情况。

【选题方向】{topic}
【自定义角度】{angle_name}
【角度描述】{angle_description or "（无补充描述）"}

【维度种子库（可参考，不必全用）】
案例、ROI/成本、管理者视角、时效、信息密度、竞品对比、方法论框架、实施步骤、数据口径、风险点

【素材池（共{len(doc_list)}篇，展示前15篇）】
{doc_summary if doc_summary else "（素材池为空）"}

【任务】
1. 从维度种子库中选取与此角度最相关的 3-6 个维度（可增删），每个维度给出需求描述和重要性（high/medium/low）
2. 按维度检查素材池中是否有对应文档命中
3. 判断整体可行性（high / medium / low）
4. 给出优化建议

请严格按以下 JSON 格式返回（不要多余文字）：
{{
  "dimensions": [
    {{"name": "维度名", "description": "该角度对此维度的需求", "severity": "high|medium|low", "hit_count": 0, "sample_docs": []}}
  ],
  "feasibility": "high|medium|low",
  "suggestions": ["建议1", "建议2"]
}}"""

    try:
        response = await _call_llm(
            session_id=session_id,
            call_name="自定义角度评估",
            messages=[{"role": "user", "content": evaluate_prompt}],
            temperature=0.3,
            max_tokens=800,
        )
        raw = response["choices"][0]["message"]["content"].strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = _safe_json_parse(raw, fallback_key="dimensions")
    except Exception as e:
        logger.warning(f"自定义角度评估 LLM 调用失败: {e}")
        return _success({
            "feasibility": "yellow",
            "coverage": 0.0,
            "dimensions": [],
            "gaps": [],
            "suggestions": [],
            "note": "评估暂时不可用，请稍后重试或手动判断素材充足度"
        })
    
    dims = result.get("dimensions", [])
    feasibility_str = result.get("feasibility", "medium")
    suggestions = result.get("suggestions", [])
    
    # ── 计算覆盖度和可行性等级 ──
    total_dims = len(dims)
    hit_dims = sum(1 for d in dims if d.get("hit_count", 0) > 0)
    coverage = hit_dims / total_dims if total_dims > 0 else 0.5
    
    if coverage >= 0.7:
        feasibility = "green"
    elif coverage >= 0.4:
        feasibility = "yellow"
    else:
        feasibility = "red"
    
    # ── 构建 gaps 数组（severity 来自 LLM 输出，非硬编码）──
    gaps = []
    for d in dims:
        if d.get("hit_count", 0) == 0:
            gaps.append({
                "item": d.get("name", ""),
                "severity": d.get("severity", "medium"),
                "origin": "custom",
                "suggestion": d.get("description", "")
            })
    
    # ── gap 合并去重（已有的 radar gaps 合并）──
    radar_gaps = []
    radar_gap_topic = _match_radar_topic(radar_topics, topic)
    if radar_gap_topic:
        deficiencies = radar_gap_topic.get("deficiency_details", [])
        for def_item in deficiencies:
            radar_gaps.append({
                "item": def_item.get("item", ""),
                "severity": "high",
                "origin": "radar"
            })
    
    # 合并：同名取高 severity，origins 合并
    merged_gaps = {}
    for g in radar_gaps + gaps:
        key = g["item"]
        if key in merged_gaps:
            existing = merged_gaps[key]
            severity_order = {"high": 3, "medium": 2, "low": 1}
            if severity_order.get(g["severity"], 0) > severity_order.get(existing["severity"], 0):
                existing["severity"] = g["severity"]
            if isinstance(existing.get("origin"), list):
                if g["origin"] not in existing["origin"]:
                    existing["origin"].append(g["origin"])
            else:
                existing["origin"] = [existing["origin"], g["origin"]] if existing["origin"] != g["origin"] else [existing["origin"]]
        else:
            merged_gaps[key] = dict(g)
            merged_gaps[key]["origin"] = [g["origin"]]
    
    all_gaps = list(merged_gaps.values())
    
    return _success({
        "feasibility": feasibility,
        "coverage": round(coverage, 2),
        "dimensions": dims,
        "gaps": all_gaps,
        "suggestions": suggestions,
    })


@router.post("/api/workflow/supplement/1")
async def supplement_1(request: Dict = Body(...)):
    """第1次补充：方向相关信息（粗粒度）+ 后台预拉 AIPULSE 结果"""
    session_id = request.get("session_id", "")
    direction = request.get("direction", "")
    supplement_info = request.get("supplement_info", {})
    
    session = _get_session(session_id)
    session["step1"] = {
        "selected_direction": direction,
        "supplement_1": supplement_info,
    }

    # P3: 后台异步预拉 AIPULSE 结果（不阻塞响应，失败不影响主流程）
    # H2: 写入状态供前端轮询
    s = _get_session(session_id)
    s["aipulse_status"] = "fetching"
    s["aipulse_items_count"] = 0

    async def _prefetch_aipulse():
        try:
            from src.ai_pulse_client import get_ai_pulse_client
            ai_config = _get_config("ai_pulse")
            if not ai_config.get("enabled", False):
                logger.info("[AIPulse-Prefetch] AI-Pulse 未启用，跳过预拉取")
                s["aipulse_status"] = "disabled"
                return
            client = get_ai_pulse_client(ai_config)
            # days=30 → time_filter=month，生产端有 98 条
            cases = await client.fetch_latest_cases(
                keywords=[direction[:50]],
                days=30,
                take=20,
            )
            if cases:
                async with _sessions_lock:
                    s["aipulse_items"] = [
                        {
                            "text": c.get("summary", c.get("title", ""))[:500],
                            "source_type": "aipulse",
                            "filename": c.get("title", f"aipulse_{c.get('id', '')}"),
                            "source_name": c.get("source", "AI-Pulse"),
                            "url": c.get("url", ""),
                            "score": c.get("score", 0),
                            "published_at": c.get("published_at", ""),
                        }
                        for c in cases
                    ]
                    s["aipulse_items_count"] = len(cases)
                    s["aipulse_status"] = "done"
                logger.info(f"[AIPulse-Prefetch] 预拉取成功: {len(cases)}条 → session")
            else:
                async with _sessions_lock:
                    s["aipulse_items_count"] = 0
                    s["aipulse_status"] = "empty"
                logger.info("[AIPulse-Prefetch] 预拉取返回 0 条（关键词可能不匹配）")
        except Exception as e:
            async with _sessions_lock:
                s["aipulse_status"] = "failed"
                s["aipulse_error"] = str(e)[:200]
            logger.warning(f"[AIPulse-Prefetch] 预拉取失败（不影响主流程）: {e}")

    asyncio.create_task(_prefetch_aipulse())

    return _success({"status": "ok", "message": "第1次补充已保存"})


@router.get("/api/workflow/aipulse_status/{session_id}")
async def get_aipulse_status(session_id: str):
    """H2: 查询 AIPULSE 预拉取状态"""
    s = _get_session(session_id)
    return _success({
        "status": s.get("aipulse_status", "idle"),
        "count": s.get("aipulse_items_count", 0),
        "error": s.get("aipulse_error", None),
    })


@router.get("/api/workflow/thinking/logs")
async def get_thinking_logs(session_id: str, since: float = 0.0):
    """
    获取AI思考日志
    
    Args:
        session_id: 会话ID
        since: 可选，时间戳，只返回该时间之后的日志（增量拉取）
    """
    s = _get_session(session_id)
    if not s:
        return _error(code=404, msg="会话不存在")
    
    logs = s.get("thinking_logs", [])
    
    # 增量拉取：只返回since之后的
    if since > 0:
        logs = [log for log in logs if log.get("start_time", 0) > since]
    
    return _success({"logs": logs, "total": len(logs)})


@router.post("/api/workflow/frameworks/match")
async def match_frameworks_v2(request: Dict = Body(...)):
    """推荐分析框架(v2: 双评分+降级兜底+业务化warning)"""
    import time
    start_time = time.time()
    
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
    model = V4_FLASH
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
        result = await _call_llm(
            session_id=session_id,
            call_name="fix_direction",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0,
            seed=42,
            phase="补充修正",
        )
        parsed_content = result["choices"][0]["message"]["content"].strip()
        parsed_content = parsed_content.replace("```json", "").replace("```", "").strip()
        frameworks = json.loads(parsed_content)
        
        if not isinstance(frameworks, list):
            frameworks = [frameworks]
        
        for fw in frameworks:
            fw.setdefault("name", "未知框架")
            fw.setdefault("description", "")
            fw.setdefault("direction_alignment_score", fw.get("match_score", 0.5))
            # ══ 修复：LLM 可能显式返回 0，避免框架被误过滤 ══
            try:
                if float(fw.get("direction_alignment_score", 0)) <= 0:
                    fw["direction_alignment_score"] = fw.get("match_score", 0.5)
            except (TypeError, ValueError):
                fw["direction_alignment_score"] = 0.5
            fw.setdefault("direction_alignment_reason", "")
            fw.setdefault("reason", "")
            fw.setdefault("evidence_quote", "")
            fw.setdefault("source", "user_implied")
            fw.setdefault("framework_origin", "")
            fw.setdefault("usage_hint", "")
            fw.setdefault("warning", "")
            fw.setdefault("needs_supplement", [])
            
            # 添加框架 key（用于前端推导和图片生成）
            NAME_TO_KEY = {
                "SWOT 分析": "swot",
                "商业模式画布": "business_canvas",
                "PESTEL 分析": "pestel",
                "用户旅程图": "user_journey",
                "时间矩阵": "time_matrix",
                "主张论证": "claim",
                "因果分析": "causal",
                "系统思考": "system",
                "对比分析": "comparison",
                "流程步骤": "process",
            }
            fw.setdefault("key", NAME_TO_KEY.get(fw["name"], ""))
            
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
        
        # 记录成功日志
        fw_chain = [{"step": 1, "action": "匹配分析框架", "reason": f"为方向「{direction}」推荐适合的分析框架", "result": f"匹配到{len(frameworks)}个框架"}]
        for i, fw in enumerate(frameworks):
            fw_chain.append({
                "step": i + 2,
                "action": f"框架「{fw.get('name', '未知')}」",
                "reason": f"来源：{fw.get('source', '未知')}，对齐度：{fw.get('direction_alignment_score', 0)}，匹配理由：{fw.get('direction_alignment_reason', fw.get('reason', '未提供'))[:100]}",
                "result": "已纳入推荐列表"
            })
        _log_llm_call_legacy(
            session_id=session_id,
            call_id=f"match_frameworks_{session_id}_{int(time.time())}",
            call_name="框架匹配",
            messages=[{"role": "user", "content": prompt}],
            result=json.dumps(frameworks, ensure_ascii=False),
            model=model,
            temperature=0.0,
            duration=time.time() - start_time,
            thinking_chain=fw_chain
        )

        return _success({
            "frameworks": frameworks,
            "mode": "premium",
            "banner": "",
        })
    except json.JSONDecodeError as e:
        logger.error(f"框架推荐 JSON 解析失败: {e}")
        _log_llm_call_legacy(session_id, "step2_match_frameworks", "框架匹配", messages=[{"role": "user", "content": prompt}], error=str(e), thinking_chain=[
            {"step": 1, "action": "框架匹配失败", "reason": f"为方向「{direction}」匹配分析框架时发生JSON解析错误", "result": "使用兜底框架"},
        ])
        default_frameworks = [
            {
                "name": "SWOT 分析",
                "key": "swot",
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
        _log_llm_call_legacy(session_id, "step2_match_frameworks", "框架匹配", messages=[{"role": "user", "content": prompt}], error=str(e), thinking_chain=[
            {"step": 1, "action": "框架匹配失败", "reason": f"为方向「{direction}」匹配分析框架时发生未知错误", "result": "匹配中断"},
        ])
        return _error_internal(e)


@router.post("/api/workflow/supplement/2")
async def supplement_2(request: Dict = Body(...)):
    """第2次补充：完善分析内容（中粒度）"""
    session_id = request.get("session_id", "")
    framework = request.get("framework", "")  # 可以是字符串或对象
    supplement_info = request.get("supplement_info", {})
    
    # 如果 framework 是字符串，转换为对象格式
    if isinstance(framework, str):
        framework_obj = {"name": framework, "key": ""}
    elif isinstance(framework, dict):
        framework_obj = framework
    else:
        framework_obj = {"name": str(framework), "key": ""}
    
    session = _get_session(session_id)
    step2 = session.get("step2", {})
    # 合并语义：只更新有值的字段，避免空框架覆写已选框架
    if framework_obj.get("name"):
        step2["selected_framework"] = framework_obj
    step2["supplement_2"] = supplement_info
    session["step2"] = step2
    
    return _success({"status": "ok", "message": "第2次补充已保存"})


# ===== AI 补充素材：缺口关键词映射表 =====
GAP_KEYWORD_MAP = {
    "案例": ["案例", "实践", "落地", "复盘", "实例"],
    "ROI": ["ROI", "投入产出", "成本", "收益", "财报", "投资回报"],
    "管理者": ["管理层", "决策", "战略", "CEO", "高管", "领导"],
    "时效": ["2024", "2025", "最新", "趋势", "前沿"],
    "信息密度": ["方法论", "框架", "白皮书", "深度", "体系"],
}


def _match_gap_to_keywords(gap_item: str) -> list:
    """将缺口项映射为搜索关键词列表"""
    for key, keywords in GAP_KEYWORD_MAP.items():
        if key in gap_item:
            return keywords
    # 回退：直接用缺口项本身作为关键词
    return [gap_item]


def _search_kb_by_keywords(keywords: list, kb: KnowledgeBaseReader, top_k: int = 5) -> list:
    """在知识库中按关键词搜索文件，返回匹配的文件列表（按匹配度排序）"""
    scored = []
    # 递归收集所有分类下的文件
    all_files = []
    try:
        categories = kb.list_categories()
        for cat in categories:
            cat_files = kb.list_directory(category=cat["key"])
            all_files.extend(cat_files)
        # 也检查根目录下的文件
        root_files = kb.list_directory()
        all_files.extend(root_files)
    except Exception:
        return []
    
    for f in all_files:
        if f.get("is_dir"):
            continue
        filename = f.get("name", "")
        path = f.get("path", "")
        score = 0
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in filename.lower():
                score += 3  # 文件名匹配权重高
        # 读文件前 1000 字符做内容匹配
        try:
            content = kb.read_file(path)
            if content:
                snippet = content[:1000].lower()
                for kw in keywords:
                    if kw.lower() in snippet:
                        score += 1
        except Exception:
            pass
        if score > 0:
            scored.append({"name": filename, "path": path, "score": score, "content": content or ""})
    
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


@router.post("/api/workflow/supplement/materials")
async def supplement_materials(request: Dict = Body(...)):
    """AI 补充素材：根据雷达缺口自动搜索知识库，补入新文档并重算评分"""
    session_id = request.get("session_id", "")
    direction_name = request.get("direction_name", "")
    
    if not session_id:
        return _error(code=400, msg="缺少 session_id")
    
    session = _get_session(session_id)
    
    # 1. 从雷达上下文找当前方向的 deficiency_details
    radar_ctx = session.get("radar_context", {})
    topics = radar_ctx.get("topics", [])
    current_topic = _match_radar_topic(topics, direction_name)
    
    if not current_topic:
        # 回退：取第一个 topic
        if topics:
            current_topic = topics[0]
            direction_name = current_topic.get("name", "")
        else:
            return _success({
                "added_files": [],
                "new_density": 0,
                "before_density": 0,
                "gap_addressed": "",
                "suggestion": "雷达尚未扫描，请先完成选题步骤",
            })
    
    deficiency_details = current_topic.get("deficiency_details", [])
    if not deficiency_details:
        return _success({
            "added_files": [],
            "new_density": current_topic.get("signal_report", {}).get("good_count", 0) / 5,
            "before_density": current_topic.get("signal_report", {}).get("good_count", 0) / 5,
            "gap_addressed": "",
            "suggestion": "当前方向无素材缺口，无需补充",
        })
    
    # 2. 构建诊断上下文（供 LLM 使用）
    sr = current_topic.get("signal_report", {})
    good_count = sr.get("good_count", 0)
    total_count = sr.get("total_count", 5)
    def_lines = []
    for d in deficiency_details:
        def_lines.append(f"- [{d.get('severity', 'medium')}] {d.get('item', '')}: {d.get('detail', '')}")
    def_text = "\n".join(def_lines)
    
    suggestions = session.get("writing_suggestions", {}).get(direction_name, [])
    sug_text = "\n".join([f"- {s}" for s in suggestions]) if suggestions else "暂无"
    
    material_pool = session.get("material_pool", [])
    mat_lines = []
    for m in material_pool[:5]:
        fn = m.get("filename", "未知文件")
        txt = (m.get("text", "") or "")[:120].replace("\n", " ")
        mat_lines.append(f"- {fn}: {txt}")
    mat_text = "\n".join(mat_lines) if mat_lines else "暂无"
    
    # 3. 阶段二：LLM 语义诊断 + 动态搜索词生成
    diag_text = ""
    keywords = []
    try:
        diag_prompt = f"""请基于以下上下文，诊断当前选题方向最需要补充什么素材，并生成精准搜索词。

选题方向：{direction_name}

【雷达报告】
信号灯：{good_count}/{total_count}
不足项：
{def_text}

【写作建议】
{sug_text}

【已有素材摘要（前 5 篇）】
{mat_text}

请输出纯 JSON（无 markdown，无其他文字）：
{{"diagnosis": "精准诊断（一行中文，具体到内容类型，如'缺AI语音引擎的ROI量化数据'而非'缺ROI'）","keywords": ["搜索词1","搜索词2","搜索词3","搜索词4","搜索词5"]}}

关键词规则：
- 从诊断描述中拆出 5 个精准搜索词
- 优先使用上下文中的特有名词（如选题名称中的核心词）
- 不要用太泛的词（如"案例""方法论"），要指向具体内容类型"""
        
        diag_response = await _call_llm(
            session_id=session_id,
            call_name="AI补充素材·语义诊断",
            messages=[{"role": "user", "content": diag_prompt}],
            temperature=0.3,
            max_tokens=600,
        )
        diag_raw = diag_response["choices"][0]["message"]["content"].strip()
        diag_raw = diag_raw.replace("```json", "").replace("```", "").strip()
        diag_result = _safe_json_parse(diag_raw, fallback_key="diagnosis")
        diag_text = diag_result.get("diagnosis", "")
        keywords = diag_result.get("keywords", [])
    except Exception as e:
        logger.warning(f"[SupplementMaterials] LLM 诊断失败: {e}, 回退到规则驱动")
    
    # 回退：LLM 诊断失败或无结果时，用规则驱动
    if not keywords:
        severity_order = {"high": 0, "medium": 1, "low": 2}
        deficiency_details.sort(key=lambda d: severity_order.get(d.get("severity", "medium"), 1))
        target_gap = deficiency_details[0]
        gap_item = target_gap.get("item", "")
        keywords = _match_gap_to_keywords(gap_item)
    else:
        gap_item = diag_text
    
    logger.info(f"[SupplementMaterials] 诊断: '{gap_item}' → 关键词: {keywords}")
    
    # 4. 搜索知识库（扩大候选池，后续由 LLM 二次筛选）
    kb = KnowledgeBaseReader(_get_config("knowledge_base"))
    matched_files = _search_kb_by_keywords(keywords, kb, top_k=5)
    
    # 5. 阶段二：LLM 对搜索结果逐篇打分，过滤低相关文档
    diag_log = [f"🔍 诊断到缺口：{gap_item}"]
    if matched_files:
        try:
            score_lines = []
            for i, mf in enumerate(matched_files):
                snip = (mf.get("content", "") or "")[:200].replace("\n", " ")
                score_lines.append(f"【{i}】{mf['name']}\n  摘要：{snip}")
            score_prompt = f"""请对以下候选文档进行相关性打分（0-10 分）。

诊断缺口：{gap_item}

候选文档：
{chr(10).join(score_lines)}

只输出纯 JSON 数组（含 score >= 6 的文档）：
[{{"index": 0, "score": 8, "reason": "简短理由"}}, ...]

规则：
- 6 分以下不要输出
- reason 用一句话说明判断依据
- 纯 JSON，无 markdown，无其他文字"""
            
            score_response = await _call_llm(
                session_id=session_id,
                call_name="AI补充素材·结果筛选",
                messages=[{"role": "user", "content": score_prompt}],
                temperature=0.2,
                max_tokens=600,
            )
            score_raw = score_response["choices"][0]["message"]["content"].strip()
            score_raw = score_raw.replace("```json", "").replace("```", "").strip()
            scored = _safe_json_parse(score_raw, fallback_key="index")
            if isinstance(scored, list) and len(scored) > 0:
                # 按 score 排序，取前 2 篇
                scored.sort(key=lambda x: x.get("score", 0), reverse=True)
                scored = scored[:2]
                # 替换 matched_files 为筛选后的结果
                filtered = []
                for s in scored:
                    idx = s.get("index")
                    if isinstance(idx, int) and 0 <= idx < len(matched_files):
                        mf = matched_files[idx]
                        mf["_score"] = s.get("score", 0)
                        mf["_reason"] = s.get("reason", "")
                        filtered.append(mf)
                        diag_log.append(f"📥 {mf['name']}（相关度 {s.get('score', '?')}/10）")
                matched_files = filtered
        except Exception as e:
            logger.warning(f"[SupplementMaterials] LLM 筛选失败: {e}, 使用原始搜索结果")
            matched_files = matched_files[:2]
    else:
        diag_log.append("📥 知识库中未搜到匹配文件")
    
    # 6. 去重（对照 material_pool 中已有的文件名）
    material_pool = session.get("material_pool", [])
    existing_names = set()
    for item in material_pool:
        fn = item.get("filename", "")
        if fn:
            existing_names.add(fn)
    
    new_files = []
    for mf in matched_files:
        if mf["name"] not in existing_names:
            new_files.append(mf)
    
    # 7. 检查上限
    ai_supplement_count = sum(
        1 for item in material_pool
        if item.get("source_type") == "ai_supplement"
    )
    if ai_supplement_count >= 5:
        return _success({
            "added_files": [],
            "new_density": current_topic.get("signal_report", {}).get("good_count", 0) / 5,
            "before_density": current_topic.get("signal_report", {}).get("good_count", 0) / 5,
            "gap_addressed": gap_item,
            "suggestion": "AI 补充素材已达上限（5 篇），请进入下一步",
            "diag_log": diag_log,
        })
    
    # 8. 入库到 material_pool
    added = []
    for mf in new_files:
        material_pool.append({
            "text": mf.get("content", ""),
            "source_type": "ai_supplement",
            "filename": mf["name"],
            "_gap_addressed": gap_item,
            "_added_at": __import__("datetime").datetime.now().isoformat(),
        })
        added.append({"name": mf["name"], "gap": gap_item})
    
    session["material_pool"] = material_pool
    
    # 9. 计算更新前的密度
    sr_before = current_topic.get("signal_report", {})
    before_good = sr_before.get("good_count", 0)
    before_total = sr_before.get("total_count", 5)
    before_density = before_good / max(before_total, 1)
    
    # 10. 重算雷达评分
    try:
        all_docs_map = {}
        for item in material_pool:
            fn = item.get("filename", "")
            text = item.get("text", "")
            if fn and text:
                if fn not in all_docs_map:
                    all_docs_map[fn] = {"_full_content": text, "name": fn}
        
        new_scores = calculate_material_scores(direction_name, all_docs_map)
        new_sr = new_scores.get("signal_report", {})
        new_good = new_sr.get("good_count", 0)
        new_total = new_sr.get("total_count", 5)
        new_density = new_good / max(new_total, 1)
        
        # 更新 radar_context 中该 topic 的评分数据
        current_topic["signal_report"] = new_sr
        current_topic["deficiency_details"] = new_scores.get("deficiency_details", deficiency_details)
        current_topic["matched_docs_count"] = new_scores.get("related_count", 
            current_topic.get("matched_docs_count", 0))
        
    except Exception as e:
        logger.warning(f"[SupplementMaterials] 重算雷达失败: {e}")
        new_density = before_density
    
    # 11. 返回结果
    suggestion = None
    if not added:
        suggestion = f"知识库中未找到与「{gap_item}」相关的补充素材，建议手动上传相关文件"
        diag_log.append(suggestion)
    
    return _success({
        "added_files": added,
        "new_density": round(new_density, 2),
        "before_density": round(before_density, 2),
        "gap_addressed": gap_item,
        "suggestion": suggestion,
        "diag_log": diag_log,
    })


@router.post("/api/workflow/direction/check")
async def check_direction(request: Dict = Body(...)):
    """方向检测：检测分析内容的问题（含前置拦截）"""
    session_id = request.get("session_id", "")
    direction = request.get("direction", "")
    
    if not session_id:
        return _error(code=400, msg="缺少 session_id")
    framework = request.get("framework", "")
    supplement_1 = request.get("supplement_1", {})
    supplement_2 = request.get("supplement_2", {})
    mcp_summary = request.get("mcp_summary", "")
    
    session = _get_session(session_id)
    
    # ═══════════════════════════════════════════════════════
    # 三态状态机：initializing → pending → checking
    # 区分"没开始写"和"写了但没选框架"，避免用 0 分吓用户
    # ═══════════════════════════════════════════════════════
    supplement_text = (supplement_2.get("text") or "").strip()
    supplement_text_len = len(supplement_text)
    
    # 门禁判断：请求参数 framework + session.step2.selected_framework + session.outline 三者任一非空即通过
    framework_from_request = framework.strip() if isinstance(framework, str) and framework else ""
    selected_framework = session.get("step2", {}).get("selected_framework", {})
    has_outline = bool(session.get("outline"))
    has_framework = bool(framework_from_request) or bool(selected_framework and selected_framework.get("name"))
    ready_for_quality_check = has_framework or has_outline
    
    # ─── 读取选题雷达数据（供 initializing / pending 状态复用的公共逻辑）───
    radar_ctx = session.get("radar_context", {})
    radar_topics = radar_ctx.get("topics", [])
    radar_match = _match_radar_topic(radar_topics, direction)
    
    sr = {}
    radar_score = 0
    radar_basis = None
    if radar_match:
        sr = radar_match.get("signal_report", {})
        good = sr.get("good_count", 0)
        total = sr.get("total_count", 5)
        radar_score = round(good / max(total, 1) * 100)
        radar_basis = {
            "signal_report": sr,
            "signal_details": sr.get("signal_details", []),
            "deficiency_details": radar_match.get("deficiency_details", []),
            "satisfied_details": radar_match.get("satisfied_details", []),
            "matched_docs_count": len(radar_match.get("matched_docs", [])),
        }
    
    # ─── 状态判断 ───
    if supplement_text_len < 100 and not ready_for_quality_check:
        # ══ initializing：用户还没开始写分析 ══
        if radar_match:
            sd = sr.get("signal_details", [])
            good = sr.get("good_count", 0)
            total = sr.get("total_count", 5)
            deficiencies = radar_match.get("deficiency_details", [])
            doc_count = len(radar_match.get("matched_docs", []))
            
            signal_lines = []
            for s in sd:
                icon = "✅" if s.get("ok") else "⚠️"
                signal_lines.append(f"{icon} {s.get('label', '')}: {s.get('detail', '')}")
            signal_summary = "\n".join(signal_lines)
            
            deficit_lines = []
            for d in deficiencies:
                deficit_lines.append(f"- {d.get('item', '')}：{d.get('explanation', '')}")
            deficit_summary = "\n".join(deficit_lines) if deficit_lines else "无明显短板"
            
            issue_title = f"选题雷达已扫描（{good}/{total} 就绪）"
            issue_desc = (
                f"## 📡 选题雷达自动分析\n\n"
                f"**方向**：{direction}\n"
                f"**信号灯**：{good}/{total} 项就绪\n"
                f"**匹配文档**：{doc_count} 篇\n\n"
                f"### 信号详情\n{signal_summary}\n\n"
                f"### 待补充项\n{deficit_summary}\n\n"
                f"---\n"
                f"以上为系统自动扫描结果。请在此基础上补充您的分析观点。"
            )
            issue_suggestion = "可在雷达分析基础上，补充个人观点或案例细节"
        else:
            issue_title = "分析内容待补充"
            issue_desc = "系统已扫描您的素材库，请开始撰写分析草稿。"
            issue_suggestion = "输入分析观点或点击「AI 智能补充」快速生成"
        
        # ─── 写作建议（含 session 缓存）───
        writing_suggestions = []
        suggestions_cache = session.get("writing_suggestions", {})
        if direction in suggestions_cache:
            writing_suggestions = suggestions_cache[direction]
        elif radar_match:
            try:
                llm_config = _get_config("llm")
                base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
                api_key = llm_config.get("api_key", "")
                suggestions_model = "deepseek-chat"
                suggestions_url = f"{base_url}/chat/completions"
                
                # 取前 5 篇匹配文档摘要，每篇截 200 字
                matched_docs = radar_match.get("matched_docs", [])[:5]
                doc_summaries = []
                for md in matched_docs:
                    name = md.get("name", "")
                    snippet = (md.get("text") or md.get("snippet") or "")[:200]
                    if name and snippet:
                        doc_summaries.append(f"《{name}》摘要：{snippet}")
                doc_text = "\n".join(doc_summaries) if doc_summaries else "暂无文档摘要"
                doc_text = doc_text[:2000]  # 总输入控制在 2000 字内
                
                deficiency_text = "\n".join([
                    f"- {d.get('item', '')}: {d.get('explanation', '')}"
                    for d in deficiencies
                ]) if deficiencies else "无明显短板"
                
                suggest_prompt = (
                    f"你是一个写作导航助手。根据以下选题方向、素材雷达扫描结果和不足项清单，"
                    f"请生成 3-5 条简短的写作切入建议。每条建议不超过 30 字，不展开具体内容。\n\n"
                    f"选题方向：{direction}\n\n"
                    f"素材雷达信号灯：\n{signal_summary}\n\n"
                    f"不足项清单：\n{deficiency_text}\n\n"
                    f"匹配文档摘要：\n{doc_text}\n\n"
                    f"要求：\n"
                    f"1. 每条建议是一个具体的写作切入点，而非泛泛而谈\n"
                    f"2. 每条建议关联一个雷达不足项\n"
                    f"3. 每条建议不超过 30 字\n"
                    f"4. 返回纯 JSON 数组格式，如：['建议1','建议2','建议3']"
                )
                
                suggestions_resp = await httpx.AsyncClient(timeout=15.0).post(
                    suggestions_url,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                    json={
                        "model": suggestions_model,
                        "messages": [{"role": "user", "content": suggest_prompt}],
                        "max_tokens": 200,
                        "temperature": 0.7,
                    },
                )
                if suggestions_resp.status_code == 200:
                    body = suggestions_resp.json()
                    content = body.get("choices", [{}])[0].get("message", {}).get("content", "[]")
                    import re
                    arr_match = re.search(r'\[[\s\S]*?\]', content)
                    if arr_match:
                        import json
                        parsed = json.loads(arr_match.group(0))
                        if isinstance(parsed, list):
                            writing_suggestions = [s[:30] for s in parsed if isinstance(s, str) and s.strip()]
            except:
                pass
            
            # 写入 session 缓存
            suggestions_cache[direction] = writing_suggestions
            session["writing_suggestions"] = suggestions_cache
        
        return _success({
            "status": "initializing",
            "overall_score": radar_score,
            "score_source": "radar",
            "radar_basis": radar_basis,
            "ready_for_next": False,
            "writing_suggestions": writing_suggestions,
            "issues": [
                {
                    "type": "info",
                    "category": "initializing",
                    "title": issue_title,
                    "description": issue_desc,
                    "suggestion": issue_suggestion,
                    "can_auto_fix": False
                }
            ],
        })
    
    elif not ready_for_quality_check:
        # ══ pending：用户写了内容但还没选框架/提纲 ══
        if radar_match:
            sd = sr.get("signal_details", [])
            good = sr.get("good_count", 0)
            total = sr.get("total_count", 5)
            deficiencies = radar_match.get("deficiency_details", [])
            doc_count = len(radar_match.get("matched_docs", []))
            
            signal_lines = []
            for s in sd:
                icon = "✅" if s.get("ok") else "⚠️"
                signal_lines.append(f"{icon} {s.get('label', '')}: {s.get('detail', '')}")
            signal_summary = "\n".join(signal_lines)
            
            deficit_lines = []
            for d in deficiencies:
                deficit_lines.append(f"- {d.get('item', '')}：{d.get('explanation', '')}")
            deficit_summary = "\n".join(deficit_lines) if deficit_lines else "无明显短板"
            
            issue_title = f"选题雷达已扫描（{good}/{total} 就绪）"
            issue_desc = (
                f"## 📡 选题雷达自动分析\n\n"
                f"**方向**：{direction}\n"
                f"**信号灯**：{good}/{total} 项就绪\n"
                f"**匹配文档**：{doc_count} 篇\n\n"
                f"### 信号详情\n{signal_summary}\n\n"
                f"### 待补充项\n{deficit_summary}"
            )
            issue_suggestion = "可选择写作框架后进行质量评估"
        else:
            issue_title = "分析内容已保存"
            issue_desc = f"已检测到 {supplement_text_len} 字分析内容。"
            issue_suggestion = "选择写作框架后可进行质量评估"
        
        return _success({
            "status": "pending",
            "overall_score": radar_score,
            "score_source": "radar",
            "radar_basis": radar_basis,
            "writing_progress": f"已写 {supplement_text_len} 字分析，选择写作框架后可进行质量评估",
            "ready_for_next": False,
            "issues": [
                {
                    "type": "info",
                    "category": "pending",
                    "title": issue_title,
                    "description": issue_desc,
                    "suggestion": issue_suggestion,
                    "can_auto_fix": False
                }
            ],
        })
    
    # ═══════════════════════════════════════════════════════
    # 内容已有意义，正常调用LLM检测
    # ═══════════════════════════════════════════════════════
    
    llm_config = _get_config("llm")
    base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = llm_config.get("api_key", "")
    model = V4_FLASH
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
    
    prompt = f"""你是 ArchGen 的交付审核员（Gatekeeper）。你的任务不是让文章变得完美，而是判断当前内容是否具备交付的基本条件。

【核心原则】抓大放小。允许内容粗糙，但不允许方向错误。

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

═══════════ 拦截标准（满足任一即拦截，不得放行） ═══════════

1. 方向偏离：
   分析内容的核心论述对象与选定方向的主题不一致。
   例：选了"私域运营策略"，内容讨论的是"公域广告投放"。
   不拦的情况：方向是对的，但角度不够聚焦 → 降级为建议。

2. 实质性空白：
   分析正文（不含标题/框架标签）的有效字数 < 100 字，
   或核心论述段落缺失（有框架壳，没有内容填充）。

3. 事实性冲突：
   分析内容中的关键断言与 MCP 素材摘要中的已知数据直接矛盾。
   不拦的情况：无数据支撑的推断 → 降级为建议（标记[推断]）。

═══════════ 建议标准（不阻塞，仅提示） ═══════════

以下问题属于内容级优化项，不得作为拦截理由：
- 案例不足：案例数量不够多、不够生动
- 数据缺失：缺少具体数字支撑（但推断内容不要求）
- 结构混乱：内容组织不够流畅（如先说结论再补背景）
- 价值标准：写作风格不够"可落地实操"

对于这些，标记为 suggestion，不影响 ready_for_next。

═══════════ 补充内容类型识别规则 ═══════════

补充文本中可能带有以下标记，请根据标记类型调整判断：
- [推断补充]：不要求案例数量/具体数据，检查推导逻辑是否自洽即可
- [增厚补充]：检查是否过度解读（超过原文5倍）或偏离核心观点
- [补全补充]：检查逻辑链是否闭合，是否越界
- 无标记：视为用户手动输入或确认过的内容

═══════════ 输出要求 ═══════════

返回 JSON 格式（不要 markdown 代码块）：
{{
  "issues": [
    {{
      "level": "block | suggest",
      "category": "direction | framework | content_empty | fact_conflict | cases | data | structure | value",
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
- level="block" 表示必须修复才能进入下一步（仅方向偏离、实质性空白、事实性冲突）
- level="suggest" 表示建议优化，不阻塞（案例/数据/结构/风格问题）
- 只要没有 block 级别问题，ready_for_next 必须为 true
- 即使文章写得简陋，只要方向对、有内容、无事实冲突，就放行

请直接返回 JSON：
"""
    
    try:
        result = await _call_llm(
            session_id=session_id,
            call_name="方向检测",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=2048,
            seed=42,
            timeout=timeout,
            phase="选题",
        )
        
        parsed_content = result["choices"][0]["message"]["content"].strip()
        parsed_content = parsed_content.replace("```json", "").replace("```", "").strip()
        check_result = json.loads(parsed_content)
        
        # 丰富最近一条日志的 thinking_chain：方向检测详情
        session = _get_session(session_id)
        if session:
            logs = session.get("thinking_logs", [])
            if logs:
                last = logs[-1]
                passed = check_result.get("ready_for_next", True)
                score = check_result.get("overall_score", 0)
                block_count = len([i for i in check_result.get("issues", []) if i.get("level") == "block"])
                suggest_count = len([i for i in check_result.get("issues", []) if i.get("level") == "suggest"])
                chain = [{
                    "step": 1, "action": "方向检测",
                    "reason": f"检查当前内容与选定方向「{direction}」的匹配程度",
                    "result": f"检测{'通过' if passed else '未通过'}，综合评分{score}分，发现问题{block_count}个拦截项、{suggest_count}个建议项"
                }]
                if not passed:
                    chain.append({"step": 2, "action": "方向偏离警告", "reason": f"检测到{block_count}个需要修复的拦截项", "result": "需要修正后才能继续"})
                last["thinking_chain"] = chain
        
        # 验证返回格式
        check_result.setdefault("issues", [])
        check_result.setdefault("overall_score", 50)
        check_result.setdefault("ready_for_next", True)
        # ══ 修复：LLM 可能显式返回 0，setdefault 无法拦截 ══
        if check_result.get("overall_score", 0) <= 0:
            check_result["overall_score"] = 50
        check_result.setdefault("content_completeness_score", check_result["overall_score"])
        if check_result.get("content_completeness_score", 0) <= 0:
            check_result["content_completeness_score"] = check_result["overall_score"]
        check_result.setdefault("status", "checked")
        
        # 兼容旧字段：将 level 映射为 type（前端可能还在用 type）
        for issue in check_result.get("issues", []):
            # 兜底：如果LLM没返回level，默认为suggest（门卫模式：不阻塞）
            if "level" not in issue:
                issue["level"] = "suggest"
            if "type" not in issue:
                issue["type"] = "error" if issue["level"] == "block" else "warning"
        
        # 检测次数计数 + 3次强制放行逻辑
        session = _get_session(session_id)
        session["check_count"] = session.get("check_count", 0) + 1
        check_count = session["check_count"]
        
        # 超过3次未通过，强制放行
        if check_count >= 3 and not check_result.get("ready_for_next", True):
            logger.warning(f"Session {session_id} 检测 {check_count} 次未通过，强制放行")
            check_result["ready_for_next"] = True
            check_result["force_passed"] = True
            check_result["check_count"] = check_count
        
        return _success(check_result)
    except json.JSONDecodeError as e:
        logger.error(f"方向检测 JSON 解析失败: {e}")
        # 返回默认检测结果（门卫模式：默认放行）
        default_result = {
            "status": "checked",
            "content_completeness_score": 50,
            "issues": [
                {
                    "level": "suggest",
                    "type": "warning",
                    "category": "cases",
                    "title": "建议补充更多案例",
                    "description": "当前内容案例较少",
                    "suggestion": "可补充实战案例增强说服力",
                    "can_auto_fix": False
                }
            ],
            "overall_score": 60,
            "ready_for_next": True
        }
        return _success(default_result)
    except Exception as e:
        logger.error(f"方向检测失败: {e}")
        return _error_internal(e)


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
    model = V4_FLASH
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
        result = await _call_llm(
            session_id=session_id,
            call_name="recommend_structures",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0,
            seed=42,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            phase="结构推荐",
        )
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
        return _error_internal(e)


@router.post("/api/workflow/structures/recommend")
async def recommend_structures(request: Dict = Body(...)):
    """推荐内容结构"""
    import time
    start_time = time.time()
    
    session_id = request.get("session_id", "")
    direction = request.get("direction", "")
    framework = request.get("framework", "")
    supplement_1 = request.get("supplement_1", {})
    supplement_2 = request.get("supplement_2", {})
    mcp_summary = request.get("mcp_summary", "")
    
    llm_config = _get_config("llm")
    base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = llm_config.get("api_key", "")
    model = V4_FLASH
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
        result = await _call_llm(
            session_id=session_id,
            call_name="recommend_structures_v2",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0,
            seed=42,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            phase="结构推荐",
        )
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

        # 记录成功日志
        structures_list = result_data.get("structures", []) if isinstance(result_data, dict) else []
        struct_chain = [{"step": 1, "action": "推荐文章结构", "reason": "基于写作方向和素材特征，评估最适合的文章组织结构", "result": f"共推荐{len(structures_list)}种结构方案"}]
        for i, s in enumerate(structures_list):
            if isinstance(s, dict):
                sections = s.get("sections", s.get("outline", []))
                sec_count = len(sections) if isinstance(sections, list) else 0
                sec_names = []
                if isinstance(sections, list):
                    for sec in sections:
                        if isinstance(sec, dict):
                            sec_names.append(sec.get("name", sec.get("title", "?")))
                sec_preview = "、".join(sec_names[:5]) if sec_names else "未指定"
                struct_chain.append({
                    "step": i + 2,
                    "action": f"结构「{s.get('name', '未知')}」",
                    "reason": f"包含{sec_count}个章节，章节预览：{sec_preview}",
                    "result": "已纳入结构方案"
                })
        _log_llm_call_legacy(
            session_id=session_id,
            call_id=f"recommend_structures_{session_id}_{int(time.time())}",
            call_name="结构推荐",
            messages=[{"role": "user", "content": prompt}],
            result=parsed_content,
            model=model,
            temperature=0.0,
            duration=time.time() - start_time,
            thinking_chain=struct_chain
        )

        return _success(result_data)
    except Exception as e:
        logger.error(f"结构推荐失败: {e}")
        # 记录失败日志
        _log_llm_call_legacy(
            session_id=session_id,
            call_id=f"recommend_structures_{session_id}_{int(time.time())}",
            call_name="结构推荐",
            messages=[{"role": "user", "content": prompt}],
            error=str(e),
            model=model,
            temperature=0.0,
            duration=time.time() - start_time,
            thinking_chain=[
                {"step": 1, "action": "结构推荐失败", "reason": "推荐文章结构时发生错误", "result": "未产出结构方案"},
            ]
        )
        return _error_internal(e)


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


@router.post("/api/workflow/supplement/draft")
async def supplement_draft(request: Dict = Body(...)):
    """起草模式：基于通用知识生成参考草稿（Step 3 专用）
    
    与智能补充（smart_supplement）不同，此接口不走降级链，
    直接调用 LLM 生成参考草稿，用于 Step 3 起草阶段。
    用户确认后，草稿转为正式补充内容。
    """
    session_id = request.get("session_id", "")
    direction = request.get("direction", "")      # 从前端传入（可选）
    framework = request.get("framework", "")      # 从前端传入（可选）
    missing_item = request.get("missing_item", "")  # 缺失项标题
    user_hint = request.get("user_hint", "")      # 用户额外指示
    
    if not session_id:
        return _error(code=400, msg="缺少 session_id")
    if not missing_item:
        return _error(code=400, msg="缺少缺失项信息")
    
    # 从 session 读取 MCP 摘要
    session = _get_session(session_id)
    mcp_summary = session.get("mcp_summary", "")
    
    # LLM 配置
    llm_config = _get_config("llm")
    base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = llm_config.get("api_key", "")
    model = V4_FLASH
    timeout = llm_config.get("timeout", 60)
    
    # 起草 Prompt：不走降级链，直接生成参考草稿
    direction_text = f"\n【写作方向】{direction}" if direction else ""
    framework_text = f"\n【分析框架】{framework}" if framework else ""
    item_text = f"\n【需要补充的内容】{missing_item}"
    hint_text = f"\n用户额外指示：{user_hint}" if user_hint else ""
    
    prompt = f"""你是 ArchGen 的内容起草助手。用户正在准备写作素材，但还没有具体内容。{direction_text}{framework_text}
【MCP素材摘要】{mcp_summary}{item_text}{hint_text}

请基于通用行业知识生成参考草稿。

规则：
1. 不要因为缺少数据而拒绝输出。你的价值就是给用户一个可修改的起点。
2. 涉及具体数据/案例/事实的地方，用 [待核实：xxx] 标记。
3. 输出开头必须加：⚠️ 以下为AI基于通用模式的推导参考，请核实后使用。
4. 保持专业语气，内容可直接用于文章草稿。

请直接输出草稿内容：
"""
    
    try:
        result = await _call_llm(
            session_id=session_id,
            call_name="结构推荐",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.3,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            phase="提纲生成",
        )
        draft_text = result["choices"][0]["message"]["content"].strip()
        
        return _success({
            "text": draft_text,
            "source": "draft",
            "warning": "⚠️ 以下为AI基于通用模式的推导参考，请核实后使用",
        })
    except Exception as e:
        logger.error(f"草稿生成失败: {e}")
        return _error(msg=f"草稿生成失败: {str(e)}")


@router.post("/api/workflow/outline/generate")
async def generate_outline_v2(request: Dict = Body(...)):
    """生成写作提纲（基于所有补充信息）"""
    import time
    start_time = time.time()
    
    session_id = request.get("session_id", "")
    session = _get_session(session_id)
    
    direction = session.get("step1", {}).get("selected_direction", "")
    framework_raw = session.get("step2", {}).get("selected_framework", "")
    # 兼容新旧格式：可能是字符串 "SWOT 分析" 或对象 {name: "SWOT 分析", key: "swot"}
    if isinstance(framework_raw, dict):
        framework = framework_raw.get("name", "")
    else:
        framework = str(framework_raw) if framework_raw else ""
    structure = session.get("step3", {}).get("selected_structure", "")
    supplement_1 = session.get("step1", {}).get("supplement_1", {})
    supplement_2 = session.get("step2", {}).get("supplement_2", {})
    supplement_3 = session.get("step3", {}).get("supplement_3", {})
    mcp_summary = session.get("mcp_summary", "")
    
    llm_config = _get_config("llm")
    base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = llm_config.get("api_key", "")
    model = V4_PRO
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
      "section": "所属section的key（hook/problem/breakdown/solution/action）",
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
        result = await _call_llm(
            session_id=session_id,
            call_name="结构推荐_final",
            messages=[{"role": "user", "content": prompt}],
            model=model,
            max_tokens=4096,
            temperature=0,
            seed=42,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            phase="提纲最终生成",
        )
        
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
            # ══ 修复：LLM 可能显式返回 0，避免误触发风险警告 ══
            if outline_align <= 0:
                outline_align = 0.7
                outline["direction_alignment_score"] = 0.7
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
        
        _log_llm_call_legacy(session_id, "step3_generate_outline", "提纲生成", messages=[{"role": "user", "content": prompt}], result=parsed_content, duration=time.time() - start_time, thinking_chain=[
            {"step": 1, "action": "生成文章提纲", "reason": f"基于选定方向「{direction}」和框架，生成完整文章结构", "result": f"提纲生成完成：共{len(outline.get('sections', {}))}个章节"},
        ])
        
        return _success(outline)
    except Exception as e:
        logger.error(f"提纲生成失败: {e}")
        _log_llm_call_legacy(session_id, "step3_generate_outline", "提纲生成", messages=[{"role": "user", "content": prompt}], error=str(e), thinking_chain=[
            {"step": 1, "action": "提纲生成失败", "reason": "生成文章提纲时发生错误", "result": "未产出提纲"},
        ])
        return _error_internal(e)


@router.post("/api/workflow/article/generate")
async def generate_full_article(request: Dict = Body(...)):
    """
    基于提纲生成完整文章
    """
    import time
    start_time = time.time()
    
    session_id = request.get("session_id", "")
    outline_sections = request.get("outline_sections", [])
    target_word_count = request.get("target_word_count", 2000)
    # 前端携带的补充数据（方案B：前端聚合式）
    step5_supplements = request.get("step5_supplements", "")
    step6_materials = request.get("step6_materials", [])

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
    model = V4_PRO
    timeout = llm_config.get("timeout", 120)

    mcp_summary = session.get("mcp_summary", "")
    persona_summary = session.get("persona_summary", "")
    persona_voice = session.get("persona_voice", {})
    direction = session.get("step1", {}).get("selected_direction", "")
    framework_raw = session.get("step2", {}).get("selected_framework", "")
    # 兼容新旧格式：可能是字符串 "SWOT 分析" 或对象 {name: "SWOT 分析", key: "swot"}
    if isinstance(framework_raw, dict):
        framework = framework_raw.get("name", "")
    else:
        framework = str(framework_raw) if framework_raw else ""

    # 读取 Step 4 补充内容（用户补充的素材）
    supplement_2 = session.get("step2", {}).get("supplement_2", {})
    supplement_2_text = supplement_2.get("text", "") if isinstance(supplement_2, dict) else ""
    supplement_2_display = ""
    if supplement_2_text:
        supplement_2_display = f"\n【用户补充素材】\n{supplement_2_text}\n（写作时请充分引用以上补充内容）"

    # 构建 Step 5 检测页补充内容（优先使用前端传来的热数据）
    step5_display = ""
    if step5_supplements:
        step5_display = f"\n【检测环节补充素材】\n{step5_supplements}\n（写作时请充分引用以上补充内容）"

    # 构建 Step 6 提纲页各版块补充素材
    step6_display = ""
    if step6_materials and isinstance(step6_materials, list):
        step6_parts = []
        for m in step6_materials:
            title = m.get("title", "")
            materials = m.get("materials", [])
            if isinstance(materials, list):
                mat_text = "\n".join([f"  - {item}" for item in materials])
            else:
                mat_text = str(materials)
            step6_parts.append(f"【{title}】的补充素材：\n{mat_text}")
        if step6_parts:
            step6_display = "\n【各版块补充素材】\n" + "\n".join(step6_parts) + "\n（写作时请将以上素材对应融入各版块内容）"

    # 处理 sections：可能是 dict 或 list
    if isinstance(outline_sections, dict):
        sections_list = list(outline_sections.values())
    elif isinstance(outline_sections, list):
        sections_list = outline_sections
    else:
        return _error(code=400, msg="提纲格式不正确")

    logger.info(f"文章生成 - sections类型: {type(outline_sections).__name__}, 数量: {len(sections_list)}")
    logger.info(f"文章生成 - session数据: direction={direction}, framework={framework}")
    logger.info(f"文章生成 - step5_supplements长度: {len(step5_supplements)}, step6_materials数量: {len(step6_materials)}")

    sections_text = "\n".join([
        f"- {s.get('title', s.get('label', ''))}: {s.get('key_points', [])} (素材: {json.dumps(s.get('materials', {}), ensure_ascii=False)})"
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
{supplement_2_display}{step5_display}{step6_display}
【文章提纲】
{sections_text}

要求：
1. 语言风格：专业、实战导向、有洞察力
2. 内容结构：按照提纲的段落顺序撰写
3. 总字数控制在 {target_word_count} 字左右（±10%）
4. 段落字数分配原则（重要！不要平均分配）：
   - 核心论证段落（含案例、数据、分析）：占该段提纲权重的最大篇幅，充分展开
   - 过渡段落、引言、总结：简短有力，不要注水
   - 每个段落根据内容重要性自然决定长短，不要刻意凑字数
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
"""
    # ===== P2: 长素材摘要压缩 =====
    # 对每个提纲段落对应的素材做压缩，避免素材过长稀释注意力
    async def _summarize_long_material(text: str) -> str:
        if len(text) <= 500:
            return text
        summary_prompt = f"""请压缩以下素材内容为 100-150 字的摘要，保留核心事实、数据和结论：

{text[:3000]}

摘要："""
        try:
            result = await _call_llm(
                session_id=None,
                call_name="summarize_material",
                messages=[{"role": "user", "content": summary_prompt}],
                model=V4_PRO,
                max_tokens=300,
                temperature=0.1,
                phase="素材摘要压缩",
            )
            summary = result["choices"][0]["message"]["content"].strip()
            return summary[:500]
        except Exception:
            return text[:500] + "（...截断）"

    # ===== P1 Stage 1: 逐段独立展开成段落草稿 =====
    async def _generate_paragraph_draft(
        section: Dict,
        context: Dict,
    ) -> Dict:
        title = section.get("title", section.get("label", ""))
        key_points = section.get("key_points", [])
        points_text = "\n".join([f"- {p}" for p in key_points]) if key_points else "（无具体要点，请根据标题展开）"

        # 提取该段专属素材
        mats = section.get("materials", {})
        raw_texts = mats if isinstance(mats, list) else mats.get("has", []) if isinstance(mats, dict) else []
        mat_blocks = []
        for i, mt in enumerate(raw_texts[:5]):
            mt_str = str(mt) if not isinstance(mt, str) else mt
            compressed = await _summarize_long_material(mt_str)
            mat_blocks.append(f"【素材{i+1}】{compressed}")
        mat_section = "\n".join(mat_blocks) if mat_blocks else "（无具体素材，请基于知识展开）"

        prompt = f"""你是一位专业内容写手。请根据以下信息，撰写一个完整的文章段落。

【段落主题】{title}
【段落要点】
{points_text}

【该段落可用素材】
{mat_section}

【整体上下文】
- 写作方向：{context['direction']}
- 分析框架：{context['framework']}
- 作者身份：{context['persona_summary']}
{context['supplement_info']}

要求：
1. 专注于本段主题，充分展开论证
2. 必须引用素材中的具体内容（案例、数据、观点），不要自说自话
3. 语言风格：专业、实战导向、有洞察力
4. 理论≤20%，实战≥80%
5. 长度：500-1200 字
6. 段落末尾自然留口，方便下一段衔接
7. 直接输出段落正文，不要标题
8. 段落内按逻辑层次合理分段，不同要点之间使用空行分隔（\\n\\n），每 2-3 个句子换一行，保证阅读舒适度

正文：
"""
        result = await _call_llm(
            session_id=None,
            call_name="generate_paragraph_draft",
            messages=[{"role": "user", "content": prompt}],
            model=V4_PRO,
            max_tokens=2048,
            temperature=0.3,
            seed=42,
            phase="逐段展开",
        )
        content_text = result["choices"][0]["message"]["content"].strip()
        # 统计字数
        import re as _re
        chinese_chars = len(_re.findall(r'[\u4e00-\u9fff]', content_text))
        return {"title": title, "content": content_text, "word_count": chinese_chars}

    # ===== P1 Stage 2: 拼接 + 润色成完整文章 =====
    async def _polish_article(
        drafts: List[Dict],
        context: Dict,
        target_words: int,
    ) -> Dict:
        drafts_text = "\n\n".join([f"### {d['title']}\n\n{d['content']}" for d in drafts])

        prompt = f"""你是一位资深编辑。以下是 AI 按提纲各段落独立生成的草稿，请将它们拼接为一篇完整的、流畅的文章。

【写作方向】{context['direction']}
【分析框架】{context['framework']}
【作者身份】{context['persona_summary']}
【总目标字数】{target_words} 字（±10%）

【各段落草稿】
{drafts_text}

要求：
1. 按现有段落顺序排列
2. 在段落之间添加自然的过渡句或过渡段
3. 为整篇文章添加一个吸引人的标题
4. 在开头添加一段简短的引言（2-3 句），说明文章要解决的问题或价值
5. 在结尾添加一段总结（2-3 句），升华主题
6. 保持各段落的核心内容和素材引用不变，不要删减具体案例和数据
7. 总字数控制在 {target_words} 字左右
8. 语言风格统一：专业、实战导向、有洞察力
9. 每个段落内按逻辑层次合理分段，不同要点之间使用空行分隔（\\n\\n），每 2-3 个句子换一行，保证阅读舒适度

返回 JSON 格式（不要 markdown 代码块）：
{{
  "title": "文章标题",
  "paragraphs": [
    {{
      "title": "段落标题",
      "content": "段落正文内容",
      "word_count": 字数
    }}
  ]
}}

请直接返回 JSON：
"""
        result = await _call_llm(
            session_id=None,
            call_name="polish_article",
            messages=[{"role": "user", "content": prompt}],
            model=V4_PRO,
            max_tokens=8192,
            temperature=0.3,
            seed=42,
            phase="文章润色",
        )
        content_raw = result["choices"][0]["message"]["content"].strip()
        # 使用 _extract_json 智能提取 JSON（兼容 LLM 前后附加说明文字）
        content_raw = _extract_json(content_raw)
        article = json.loads(content_raw)
        return article

    # ===== 执行流水线（串行+重试+SSE流式）=====
    async def _event_generator():
        ctx = {
            "direction": direction,
            "framework": framework,
            "persona_summary": persona_summary,
            "supplement_info": f"{supplement_2_display}{step5_display}{step6_display}",
            "mcp_summary": mcp_summary,
        }

        try:
            # Stage 1: 串行生成各段落草稿（带重试）
            logger.info(f"文章生成 SSE - 开始逐段展开，共 {len(sections_list)} 段")
            drafts = []
            failed_slots = []

            for i, s in enumerate(sections_list):
                title = s.get("title", s.get("label", f"段落{i+1}"))
                yield f"data: {json.dumps({'type': 'paragraph_start', 'data': {'slot_index': i, 'title': title, 'total': len(sections_list)}}, ensure_ascii=False)}\n\n"

                draft = None
                last_err_type = ""
                last_err_msg = ""
                for attempt in range(3):  # 1 次正常 + 2 次重试
                    try:
                        draft = await _generate_paragraph_draft(s, ctx)
                        break
                    except Exception as e:
                        last_err_type = type(e).__name__
                        last_err_msg = str(e)
                        if attempt < 2:
                            wait = 1 if attempt == 0 else 2
                            logger.warning(f"文章生成「{title}」失败(尝试{attempt+1}/3): {last_err_type}: {last_err_msg[:200]}，{wait}s 后重试")
                            yield f"data: {json.dumps({'type': 'paragraph_retry', 'data': {'slot_index': i, 'title': title, 'attempt': attempt + 1, 'reason': f'{last_err_type}: {last_err_msg[:100]}', 'wait': wait}}, ensure_ascii=False)}\n\n"
                            await asyncio.sleep(wait)

                if draft:
                    drafts.append(draft)
                    wc = draft.get("word_count", 0)
                    yield f"data: {json.dumps({'type': 'paragraph_done', 'data': {'slot_index': i, 'title': title, 'content': draft['content'][:200] + '…', 'word_count': wc}}, ensure_ascii=False)}\n\n"
                else:
                    err = f"{last_err_type}: {last_err_msg}" if last_err_msg else "未知错误"
                    failed_slots.append({"slot_index": i, "title": title, "error": err})
                    yield f"data: {json.dumps({'type': 'paragraph_failed', 'data': {'slot_index': i, 'title': title, 'error': err}}, ensure_ascii=False)}\n\n"
                    drafts.append({"title": title, "content": f"[⚠️ 本段生成失败: {err}]", "word_count": 0, "generation_failed": True})

            ok = len(drafts) - len(failed_slots)
            logger.info(f"文章生成 SSE - 阶段1完成: {ok}/{len(sections_list)} 成功, {len(failed_slots)} 失败")

            if ok == 0:
                fail_summary = " | ".join([f"「{f['title']}」{f['error']}" for f in failed_slots])
                yield f"data: {json.dumps({'type': 'error', 'msg': f'所有段落生成失败: {fail_summary}'}, ensure_ascii=False)}\n\n"
                return

            # Stage 2: 拼接润色
            success_drafts = [d for d in drafts if not d.get("generation_failed")]
            yield f"data: {json.dumps({'type': 'polishing', 'data': {}})}\n\n"

            try:
                article = await _polish_article(success_drafts, ctx, target_word_count)
            except Exception as e:
                logger.error(f"润色失败: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'msg': f'润色失败: {type(e).__name__}: {e}'}, ensure_ascii=False)}\n\n"
                return

            if failed_slots:
                article["generation_warnings"] = [f"以下段落生成失败，已用占位文本替代: {f['title']}" for f in failed_slots]

            # 添加框架 key
            framework_key = None
            if framework:
                if isinstance(framework_raw, dict) and framework_raw.get("key"):
                    framework_key = framework_raw["key"]
                else:
                    matcher = FrameworkMatcher()
                    all_frameworks = matcher.get_all_frameworks()
                    for key, fw in all_frameworks.items():
                        if fw.get("name") == framework:
                            framework_key = key
                            break
                    if not framework_key:
                        for key, fw in all_frameworks.items():
                            fw_name = fw.get("name", "")
                            if framework in fw_name or fw_name in framework:
                                framework_key = key
                                break
                    if not framework_key:
                        framework_key = framework.lower().replace(" ", "_").replace(" ", "_")[:30]
            if framework_key:
                article["framework_key"] = framework_key

            _log_llm_call_legacy(session_id, "step4_generate_article", "文章生成", 
                messages=[{"role": "user", "content": f"SSE流水线: {len(sections_list)}段串行+润色, target={target_word_count}字"}], 
                result=json.dumps(article, ensure_ascii=False), 
                duration=time.time() - start_time, thinking_chain=[
                {"step": 1, "action": "生成完整文章", "reason": f"基于{len(sections_list)}段提纲展开成文，目标字数{target_word_count}字", "result": f"文章生成完成（{len(failed_slots)}段失败）" if failed_slots else "文章生成完成"},
            ])

            yield f"data: {json.dumps({'type': 'polished_article', 'data': article}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'data': {}})}\n\n"

        except Exception as e:
            logger.error(f"文章生成 SSE 异常: {e}", exc_info=True)
            _log_llm_call_legacy(session_id, "step4_generate_article", "文章生成", 
                messages=[{"role": "user", "content": f"SSE流水线异常: {len(sections_list)}段, target={target_word_count}字"}], 
                error=str(e), thinking_chain=[
                {"step": 1, "action": "文章生成失败", "reason": f"{type(e).__name__}: {e}", "result": "生成中断"},
            ])
            yield f"data: {json.dumps({'type': 'error', 'msg': f'文章生成失败: {type(e).__name__}: {e}'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


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
        return _error_internal(e)


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
        return _error_internal(e)


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
        return _error_internal(e)


# ===== 知识评估与降级链接口（ArchGen v2.0） =====

@router.post("/api/workflow/supplement/smart")
async def smart_supplement(request: Dict = Body(...)):
    """智能补充：集成知识评估 + 降级链
    
    这是 ArchGen v2.0 的核心补充接口，替代原有的 ai-auto 接口。
    
    工作流程：
    1. 知识评估（L0-L4）
    2. 根据级别生成补充内容（降级链）
    3. 返回补充结果 + 降级提示 + 来源标签
    
    请求体：
    {
        "session_id": "会话 ID",
        "topic": "话题/维度名称",
        "context": "上下文（文章 + 大纲）",
        "missing_items": [],  // 缺失项列表
        "missing_item": {},   // 当前缺失项详情
        "force_level": null   // 强制指定级别（可选，用于降级）
    }
    
    返回：
    {
        "code": 0,
        "data": {
            "knowledge_level": "L0",
            "content": "补充内容",
            "questions": [],        // L2 使用
            "analogy": "",          // L3 使用
            "framework": {},        // L4 使用
            "alert_message": "",    // 降级提示
            "source_tag": {},       // 来源标签 {text, color}
            "reevaluate": true,     // 是否需要重新评估
            "can_degrade": true,    // 是否可以继续降级
            "assessment_reason": "" // 评估理由
        }
    }
    """
    from src.knowledge_assessor import get_knowledge_assessor
    from src.degradation_chain import get_degradation_chain, is_fact_missing_item, generate_refusal_response
    
    session_id = request.get("session_id", "")
    if not session_id:
        return _error(code=400, msg="缺少 session_id 参数")
    
    topic = request.get("topic", "")
    context = request.get("context", "")
    missing_items = request.get("missing_items", [])
    missing_item = request.get("missing_item", {})
    force_level = request.get("force_level")  # 强制级别（降级时使用）
    retrieval_results = request.get("retrieval_results", [])  # 检索结果（可选）
    
    # 详细日志：记录请求参数类型
    logger.info(f"[SmartSupplement] 请求参数: topic={topic}, missing_item类型={type(missing_item).__name__}, missing_item={missing_item}")
    logger.info(f"[SmartSupplement] missing_items类型={[type(item).__name__ for item in missing_items]}")
    
    llm_config = _get_config("llm")
    
    try:
        # 两层策略：事实类缺失项无检索结果时拒补
        is_fact = is_fact_missing_item(missing_item)
        logger.info(f"[SmartSupplement] is_fact_missing_item 结果: {is_fact}")
        
        if is_fact and not retrieval_results:
            logger.info(f"[SmartSupplement] 事实类缺失项无检索结果，拒补: {topic}")
            refusal = generate_refusal_response(topic)
            return _success({
                **refusal,
                "assessment_reason": "事实类缺失项需要外部数据支撑，当前无检索结果",
                "assessment_confidence": "low",
                "assessment_cached": False,
            })
        
        # Step 1: 知识评估（如果不是强制级别）
        if force_level and force_level in ["L0", "L1", "L2", "L3", "L4"]:
            assessment = {
                "knowledge_level": force_level,
                "reason": "用户强制指定",
                "confidence": "high",
                "cached": False,
            }
            logger.info(f"[SmartSupplement] 使用强制级别: {force_level}")
        else:
            assessor = get_knowledge_assessor(llm_config)
            assessment = await assessor.assess(topic, context, missing_items)
            logger.info(f"[SmartSupplement] 知识评估结果: {assessment['knowledge_level']} ({assessment['reason']})")
        
        knowledge_level = assessment["knowledge_level"]
        
        # Step 2: 降级链生成
        logger.info(f"[SmartSupplement] 开始降级链生成: level={knowledge_level}, topic={topic}")
        chain = get_degradation_chain(llm_config)
        supplement = await chain.generate(knowledge_level, topic, context, missing_item, retrieval_results)
        logger.info(f"[SmartSupplement] 降级链生成完成: supplement_keys={list(supplement.keys())}")
        
        # Step 3: 组装返回结果
        result = {
            **supplement,
            "assessment_reason": assessment.get("reason", ""),
            "assessment_confidence": assessment.get("confidence", "medium"),
            "assessment_cached": assessment.get("cached", False),
        }
        
        logger.info(f"[SmartSupplement] 返回结果: knowledge_level={result.get('knowledge_level')}, content_length={len(result.get('content', ''))}")
        return _success(result)
        
    except Exception as e:
        import traceback
        logger.error(f"[SmartSupplement] 智能补充失败: {e}")
        logger.error(f"[SmartSupplement] 错误堆栈: {traceback.format_exc()}")
        return _error_internal(e)


@router.post("/api/workflow/supplement/degrade")
async def degrade_supplement(request: Dict = Body(...)):
    """降级补充：用户对当前级别不满意，降级一级重新生成
    
    请求体：
    {
        "session_id": "会话 ID",
        "current_level": "L0",  // 当前知识级别
        "topic": "话题",
        "context": "上下文",
        "missing_item": {}      // 缺失项详情
    }
    
    返回：
    {
        "code": 0,
        "data": {
            "knowledge_level": "L1",  // 降级后的级别
            "content": "...",
            "alert_message": "...",
            "source_tag": {},
            "can_degrade": true,      // 是否可以继续降级
            "reevaluate": false
        }
    }
    """
    from src.degradation_chain import get_degradation_manager
    
    session_id = request.get("session_id", "")
    if not session_id:
        return _error(code=400, msg="缺少 session_id 参数")
    
    current_level = request.get("current_level", "L0")
    topic = request.get("topic", "")
    context = request.get("context", "")
    missing_item = request.get("missing_item", {})
    
    llm_config = _get_config("llm")
    
    try:
        manager = get_degradation_manager(llm_config)
        result = await manager.degrade(current_level, topic, context, missing_item)
        
        return _success(result)
        
    except Exception as e:
        logger.error(f"[DegradeSupplement] 降级补充失败: {e}")
        return _error_internal(e)


@router.post("/api/workflow/supplement/clear-cache")
async def clear_assessment_cache(request: Dict = Body(...)):
    """清除知识评估缓存
    
    请求体：
    {
        "session_id": "会话 ID",
        "cache_key": null  // 可选，指定清除某个缓存；null = 清除全部
    }
    """
    from src.knowledge_assessor import get_knowledge_assessor
    
    llm_config = _get_config("llm")
    cache_key = request.get("cache_key")
    
    try:
        assessor = get_knowledge_assessor(llm_config)
        assessor.clear_cache(cache_key)
        
        return _success({"message": "缓存已清除"})
        
    except Exception as e:
        logger.error(f"[ClearCache] 清除缓存失败: {e}")
        return _error_internal(e)


# ===== 埋点与数据看板接口（ArchGen v2.0） =====

@router.post("/api/analytics/event")
async def record_analytics_event(request: Dict = Body(...)):
    """记录埋点事件
    
    请求体：
    {
        "session_id": "xxx",
        "event_type": "supplement_complete",
        "topic": "话题",
        "knowledge_level": "L0",
        "assessment_confidence": "high",
        "assessment_cached": false,
        "content_length": 500,
        "has_evidence": true,
        "has_gap_hint": false,
        "questions_count": 0,
        "reevaluate": true,
        "can_degrade": true,
        "user_action": null,
        "degradation_count": 0,
        "metadata": {}
    }
    """
    from src.analytics_tracker import get_analytics_tracker
    
    try:
        tracker = get_analytics_tracker()
        await tracker.record_event(request)
        
        return _success({"message": "事件已记录"})
        
    except Exception as e:
        logger.error(f"[Analytics] 记录事件失败: {e}")
        return _error_internal(e)


@router.get("/api/analytics/events")
async def get_analytics_events(session_id: str = "", limit: int = 100):
    """获取事件列表
    
    参数：
    - session_id: 会话 ID（可选）
    - limit: 返回数量限制
    """
    from src.analytics_tracker import get_analytics_tracker
    
    try:
        tracker = get_analytics_tracker()
        events = await tracker.get_events(session_id if session_id else None, limit)
        
        return _success({"events": events, "count": len(events)})
        
    except Exception as e:
        logger.error(f"[Analytics] 获取事件失败: {e}")
        return _error_internal(e)


@router.get("/api/analytics/session/{session_id}")
async def get_session_summary(session_id: str):
    """获取会话汇总
    
    参数：
    - session_id: 会话 ID
    """
    from src.analytics_tracker import get_analytics_tracker
    
    try:
        tracker = get_analytics_tracker()
        summary = await tracker.get_session_summary(session_id)
        
        if summary:
            return _success(summary)
        else:
            return _error(code=404, msg="会话不存在")
        
    except Exception as e:
        logger.error(f"[Analytics] 获取会话汇总失败: {e}")
        return _error_internal(e)


@router.get("/api/analytics/overview")
async def get_analytics_overview(days: int = 7):
    """获取分析概览
    
    参数：
    - days: 统计天数（默认 7 天）
    
    返回：
    {
        "total_events": 1000,
        "total_sessions": 50,
        "level_distribution": {"L0": 100, "L1": 200, ...},
        "avg_confirm_rate": 0.85,
        "avg_degradation_count": 0.5,
        "cache_hit_rate": 0.3,
        "reevaluate_rate": 0.6
    }
    """
    from src.analytics_tracker import get_analytics_tracker
    
    try:
        tracker = get_analytics_tracker()
        overview = await tracker.get_analytics_overview(days)
        
        return _success(overview)
        
    except Exception as e:
        logger.error(f"[Analytics] 获取分析概览失败: {e}")
        return _error_internal(e)


# ===== A/B 测试接口（ArchGen v2.0） =====

@router.post("/api/ab-test/assign")
async def assign_ab_test(request: Dict = Body(...)):
    """为用户分配 A/B 测试组
    
    请求体：
    {
        "session_id": "xxx",
        "experiment_key": "degradation_alert"  // 可选，默认 degradation_alert
    }
    
    返回：
    {
        "experiment_key": "degradation_alert",
        "group": "A",
        "config": {"show_alert": true},
        "experiment_name": "降级提示 Alert 测试"
    }
    """
    from src.ab_test_manager import get_ab_test_manager
    
    try:
        session_id = request.get("session_id", "")
        if not session_id:
            return _error(code=400, msg="缺少 session_id 参数")
        
        experiment_key = request.get("experiment_key", "degradation_alert")
        manager = get_ab_test_manager()
        result = manager.assign_user(session_id, experiment_key)
        
        return _success(result)
        
    except Exception as e:
        logger.error(f"[ABTest] 分配实验组失败: {e}")
        return _error_internal(e)


@router.get("/api/ab-test/experiments")
async def get_ab_experiments():
    """获取所有实验配置"""
    from src.ab_test_manager import get_ab_test_manager
    
    try:
        manager = get_ab_test_manager()
        experiments = manager.get_all_experiments()
        
        return _success({"experiments": experiments})
        
    except Exception as e:
        logger.error(f"[ABTest] 获取实验配置失败: {e}")
        return _error_internal(e)


@router.post("/api/ab-test/start")
async def start_ab_experiment(request: Dict = Body(...)):
    """启动实验
    
    请求体：
    {
        "experiment_key": "degradation_alert",
        "start_date": "2026-06-22",  // 可选
        "end_date": "2026-07-05"     // 可选
    }
    """
    from src.ab_test_manager import get_ab_test_manager
    
    try:
        experiment_key = request.get("experiment_key", "")
        if not experiment_key:
            return _error(code=400, msg="缺少 experiment_key 参数")
        
        start_date = request.get("start_date")
        end_date = request.get("end_date")
        
        manager = get_ab_test_manager()
        manager.start_experiment(experiment_key, start_date, end_date)
        
        return _success({"message": f"实验 {experiment_key} 已启动"})
        
    except Exception as e:
        logger.error(f"[ABTest] 启动实验失败: {e}")
        return _error_internal(e)


@router.post("/api/ab-test/pause")
async def pause_ab_experiment(request: Dict = Body(...)):
    """暂停实验"""
    from src.ab_test_manager import get_ab_test_manager
    
    try:
        experiment_key = request.get("experiment_key", "")
        if not experiment_key:
            return _error(code=400, msg="缺少 experiment_key 参数")
        
        manager = get_ab_test_manager()
        manager.pause_experiment(experiment_key)
        
        return _success({"message": f"实验 {experiment_key} 已暂停"})
        
    except Exception as e:
        logger.error(f"[ABTest] 暂停实验失败: {e}")
        return _error_internal(e)


@router.post("/api/ab-test/stop")
async def stop_ab_experiment(request: Dict = Body(...)):
    """停止实验"""
    from src.ab_test_manager import get_ab_test_manager
    
    try:
        experiment_key = request.get("experiment_key", "")
        if not experiment_key:
            return _error(code=400, msg="缺少 experiment_key 参数")
        
        manager = get_ab_test_manager()
        manager.stop_experiment(experiment_key)
        
        return _success({"message": f"实验 {experiment_key} 已停止"})
        
    except Exception as e:
        logger.error(f"[ABTest] 停止实验失败: {e}")
        return _error_internal(e)


@router.post("/api/ab-test/significance")
async def calculate_significance(request: Dict = Body(...)):
    """计算统计显著性
    
    请求体：
    {
        "group_a": {"success": 100, "total": 120},
        "group_b": {"success": 90, "total": 115}
    }
    
    返回：
    {
        "p_value": 0.05,
        "significant": true,
        "confidence_level": 0.95,
        "group_a_rate": 0.8333,
        "group_b_rate": 0.7826,
        "recommendation": "保持对照组（A 组表现更好）"
    }
    """
    from src.ab_test_manager import get_ab_test_manager
    
    try:
        group_a = request.get("group_a", {})
        group_b = request.get("group_b", {})
        
        manager = get_ab_test_manager()
        result = manager.calculate_significance(group_a, group_b)
        
        return _success(result)
        
    except Exception as e:
        logger.error(f"[ABTest] 计算显著性失败: {e}")
        return _error_internal(e)


# ==================== V4.0 三列工作台端点 ====================

# === 内部辅助函数 ===

def _ensure_material_pool(session_id: str, mcp_summary: str = "", mcp_files: list = None, aipulse_items: list = None) -> list:
    """
    V4 素材池统一构建函数（已修复 early-return bug + mcp_summary 支持）
    合并 mcp_summary(文本块)、mcp_files(file列表)、supplements 到统一 material_pool
    """
    session = _get_session(session_id)
    pool = session.get("material_pool", [])

    if not pool:
        pool = []

    # 0. 雷达匹配文档优先插入（选题 → 写作桥梁）
    radar_ctx = session.get("radar_context", {})
    radar_topics = radar_ctx.get("topics", [])
    if radar_topics:
        seen = set()
        for rt in radar_topics:
            for doc in rt.get("matched_docs", []):
                doc_path = doc.get("abs_path") or doc.get("path", "")
                if doc_path in seen:
                    continue
                seen.add(doc_path)
                dedup_key = f"radar_{doc_path}"
                if any(p.get("_dedup_key") == dedup_key for p in pool):
                    continue
                # 读取文档内容
                content = ""
                try:
                    if os.path.exists(doc_path):
                        with open(doc_path, "r", encoding="utf-8") as f:
                            content = f.read()[:3000]
                except Exception:
                    pass
                if content.strip():
                    pool.insert(0, {
                        "text": content,
                        "source_type": "radar_matched",
                        "filename": doc.get("name", os.path.basename(doc_path)),
                        "_dedup_key": dedup_key,
                        "_radar_score": doc.get("score", 0),
                    })
        logger.info(f"[MaterialPool] 雷达匹配文档已插入: {len(seen)} 篇（来自 {len(radar_topics)} 个方向）")

    # 1. 追加 MCP summary（作为独立的素材块）
    if mcp_summary and mcp_summary.strip():
        pool.append({
            "text": mcp_summary.strip(),
            "source_type": "mcp_summary",
            "filename": "mcp_summary",
        })

    # 2. 追加 MCP files（从知识库扫描的文件列表）
    if mcp_files:
        for f in mcp_files:
            if isinstance(f, dict):
                pool.append({
                    "text": f.get("text", f.get("content", f.get("summary", ""))),
                    "source_type": "knowledge_base",
                    "filename": f.get("name", f.get("filename", f.get("path", "unknown"))),
                })
            elif isinstance(f, str):
                pool.append({
                    "text": f,
                    "source_type": "knowledge_base",
                    "filename": "unknown",
                })

    # 3. 追加补充内容（supplement_storage 磁盘文件）
    try:
        supplements_dir = Path(__file__).parent / "data" / "supplements"
        supp_file = supplements_dir / f"{session_id}.json"
        if supp_file.exists():
            supplements_data = json.loads(supp_file.read_text(encoding="utf-8"))
            for item_id, item_data in supplements_data.items():
                if isinstance(item_data, dict) and item_data.get("text"):
                    pool.append({
                        "text": item_data["text"],
                        "source_type": item_data.get("source", "user_input"),
                        "filename": f"supplement_{item_id}",
                    })
    except Exception as e:
        logger.warning(f"[MaterialPool] 读取补充内容失败: {e}")

    # 4. 从 session["step2"]["supplement_2"] 读取前端 Step 1 补充的素材
    try:
        step2 = session.get("step2", {})
        supp2 = step2.get("supplement_2", {})
        if isinstance(supp2, dict):
            # 4a. 知识库文件
            files = supp2.get("files", [])
            if isinstance(files, list):
                for f in files:
                    if isinstance(f, dict):
                        pool.append({
                            "text": f.get("content", f.get("text", "")),
                            "source_type": "knowledge_base",
                            "filename": f.get("name", f.get("filename", "unknown")),
                        })
            # 4b. AI 补充素材
            mats = supp2.get("materials", [])
            if isinstance(mats, list):
                for m in mats:
                    if isinstance(m, dict):
                        pool.append({
                            "text": m.get("content", m.get("text", m.get("summary", ""))),
                            "source_type": "ai_inferred",
                            "filename": m.get("title", m.get("name", "ai_supplement")),
                        })
            # 4c. 补充文本
            text = supp2.get("text", "")
            if text and text.strip():
                pool.append({
                    "text": text.strip(),
                    "source_type": "user_input",
                    "filename": "supplement_text",
                })
    except Exception as e:
        logger.warning(f"[MaterialPool] 读取 session step2 素材失败: {e}")

    # 5. P3: 追加 AIPULSE 预拉取结果
    if aipulse_items:
        for ai in aipulse_items:
            if isinstance(ai, dict) and ai.get("text"):
                pool.append({
                    "text": ai.get("text", ""),
                    "source_type": "aipulse",
                    "filename": ai.get("filename", "aipulse_item"),
                    "source_name": ai.get("source_name", "AI-Pulse"),
                })
        logger.info(f"[MaterialPool] 追加 AIPULSE 素材: {len(aipulse_items)}条")

    # 6. 去重（text 前 200 字符 + 标题接近度）
    from difflib import SequenceMatcher

    def _titles_similar(t1: str, t2: str, threshold: float = 0.6) -> bool:
        """判断两个标题是否高度相似（避免 AIPULSE 和本地 KB 重复）"""
        if not t1 or not t2:
            return False
        return SequenceMatcher(None, t1.lower(), t2.lower()).ratio() > threshold

    seen_texts = set()
    deduped = []
    for item in pool:
        text = item.get("text", "")
        key = text[:200]
        if key in seen_texts:
            continue
        # 标题去重：检查是否与已加入的项标题高度相似
        fn = item.get("filename", "")
        is_dup = False
        for existing in deduped:
            ef = existing.get("filename", "")
            if _titles_similar(fn, ef):
                is_dup = True
                break
        if is_dup:
            continue
        seen_texts.add(key)
        deduped.append(item)

    session["material_pool"] = deduped
    logger.info(f"[MaterialPool] session={session_id} 构建完成: {len(deduped)}条素材")
    return deduped


def _match_materials_internal(session_id: str, confirmed_slots: list, search_keywords: dict = None) -> dict:
    """
    V4.1 改进版素材匹配（基于中文特征：整词 + 双字词（bigram）+ 单字重叠度）
    修复：原版仅做整词 in 匹配，中文变体（如"市场规模"vs"市场现状"）全部漏掉
    """
    import re as _re
    session = _get_session(session_id)
    pool = session.get("material_pool", [])
    slot_materials = {}

    for slot in confirmed_slots:
        slot_key = slot.get("slot_key", "")
        label = slot.get("label", "")
        desc = slot.get("description", "")
        combined = label + desc

        # P3: 拼接 LLM 输出的搜索关键词（提高命中率）
        if search_keywords and slot_key in search_keywords:
            extra_kw = search_keywords[slot_key]
            if extra_kw:
                combined += " " + " ".join(extra_kw)

        # ---- 特征1: 完整分词（保留原逻辑） ----
        keywords = set()
        for seg in _re.split(r'[，,、\s：:]+', combined):
            seg = seg.strip()
            if len(seg) >= 2:
                keywords.add(seg)

        # ---- 特征2: 中文双字词（bigram） ----
        bigrams = set()
        for i in range(len(combined) - 1):
            pair = combined[i:i+2]
            # 仅保留两个字都是中文的
            if all('\u4e00' <= c <= '\u9fff' for c in pair):
                bigrams.add(pair)

        # ---- 特征3: 单汉字集合（用于重叠度计算） ----
        label_chars = set(c for c in combined if '\u4e00' <= c <= '\u9fff')

        matched = []
        for item in pool:
            item_text = item.get("text", "")
            if not item_text:
                continue

            score = 0

            # a) 整词匹配（权重: 字数×3）
            for kw in keywords:
                if kw in item_text:
                    score += len(kw) * 3

            # b) 双字词匹配（权重: 每个匹配4分）
            for bg in bigrams:
                if bg in item_text:
                    score += 4

            # c) 单字重叠度
            if label_chars:
                text_chars = set(c for c in item_text if '\u4e00' <= c <= '\u9fff')
                overlap = label_chars & text_chars
                overlap_ratio = len(overlap) / len(label_chars)
                if overlap_ratio >= 0.25:  # 25%以上字相同即加分
                    score += int(overlap_ratio * 15)

            if score > 0:
                # 找匹配片段：第一个命中位置前后取上下文（约 80 字）
                snippet = item_text[:80]  # 默认取前 80
                for kw in keywords:
                    if kw and kw in item_text:
                        pos = item_text.index(kw)
                        start = max(0, pos - 30)
                        end = min(len(item_text), pos + len(kw) + 50)
                        snippet = item_text[start:end]
                        break
                # 如果没找到整词命中，用第一个 bigram 命中位置
                if snippet == item_text[:80]:
                    for bg in bigrams:
                        if bg in item_text:
                            pos = item_text.index(bg)
                            start = max(0, pos - 30)
                            end = min(len(item_text), pos + 50)
                            snippet = item_text[start:end]
                            break

                matched.append({
                    "text": item_text[:300],
                    "source_type": item.get("source_type", "unknown"),
                    "filename": item.get("filename", ""),
                    "score": score,
                    "match_snippet": snippet,  # 匹配片段（供前端预览高亮）
                })

        # 按匹配分排序
        matched.sort(key=lambda x: x["score"], reverse=True)

        # 去重标记：文本相似的 items 加 is_duplicate 标记
        seen_texts = []
        for m in matched:
            t = m.get("text", "")[:200]
            is_dup = False
            for st in seen_texts:
                from difflib import SequenceMatcher
                if SequenceMatcher(None, t, st).ratio() > 0.8:
                    is_dup = True
                    break
            m["is_duplicate"] = is_dup
            if not is_dup:
                seen_texts.append(t)

        slot_materials[slot_key] = matched

    session["slot_materials"] = slot_materials
    logger.info(f"[MaterialPool] 匹配完成: {sum(len(v) for v in slot_materials.values())}条分配")
    return slot_materials


# === W1: AI-Pulse LLM 语义分配 ===

async def _match_aipulse_by_llm(session_id: str, confirmed_slots: list, slot_materials: dict) -> dict:
    """
    W1: 用 LLM 语义将 AIPULSE 素材分配到槽位。
    替代关键词匹配——AIPULSE 新闻标题与槽位 label 通常无关键词重叠。
    返回更新后的 slot_materials。
    """
    session = _get_session(session_id)
    pool = session.get("material_pool", [])

    # 提取所有 aipulse 素材
    aipulse_items = [it for it in pool if it.get("source_type") == "aipulse" and it.get("text")]
    if not aipulse_items:
        return slot_materials

    # 构建槽位信息
    slot_info = []
    for s in confirmed_slots:
        sk = s.get("slot_key", "")
        lb = s.get("label", "")
        ds = s.get("description", "")
        slot_info.append({"slot_key": sk, "label": lb, "desc": ds})

    if not slot_info:
        return slot_materials

    # 构建 LLM 输入
    items_text = ""
    for i, it in enumerate(aipulse_items):
        title = it.get("source_name", it.get("filename", ""))[:80]
        text = it.get("text", "")[:150]
        items_text += f"[{i}] {title}\n    {text}\n\n"

    slots_text = "\n".join(f"- {s['slot_key']}: {s['label']}{'（' + s['desc'] + '）' if s.get('desc') else ''}" for s in slot_info)

    prompt = f"""请将以下素材分配到最相关的槽位（可分配到多个槽位，也可留空）。

【槽位】
{slots_text}

【素材】
{items_text}

返回 JSON（不要 markdown 代码块）：
{{
  "assignments": {{
    "slot_key1": [0, 2, 5],
    "slot_key2": [1, 3]
  }}
}}

规则：
- 只返回真正相关的分配，不相关的不分配
- 如果素材与任何槽位都不相关，跳过
- 数字是素材编号"""

    llm_config = _get_config("llm")
    base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = llm_config.get("api_key", "")
    model = V4_FLASH

    if not api_key:
        logger.warning("[AIPulseMatch] 无 API key，跳过语义分配")
        return slot_materials

    try:
        result = await _call_llm(
            session_id=None,
            call_name="aipulse_match",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0,
            seed=42,
            base_url=base_url,
            api_key=api_key,
            timeout=30,
            phase="素材匹配",
        )
        content = result["choices"][0]["message"]["content"].strip()
        content = content.replace("```json", "").replace("```", "").strip()
        assignments = json.loads(content).get("assignments", {})

        assigned = 0
        for slot_key, item_ids in assignments.items():
            if slot_key not in slot_materials:
                slot_materials[slot_key] = []
            for idx in item_ids:
                if isinstance(idx, int) and 0 <= idx < len(aipulse_items):
                    it = aipulse_items[idx]
                    slot_materials[slot_key].append({
                        "text": it.get("text", "")[:500],
                        "source_type": "aipulse",
                        "filename": it.get("filename", "aipulse_item"),
                        "source_name": it.get("source_name", "AI-Pulse"),
                        "score": 99,  # LLM 分配的优先级最高
                        "match_snippet": it.get("text", "")[:80],
                    })
                    assigned += 1

        logger.info(f"[AIPulseMatch] LLM 语义分配: {assigned}条 → {len(assignments)}个槽位")
        return slot_materials

    except Exception as e:
        logger.warning(f"[AIPulseMatch] 失败（不影响主流程）: {e}")
        return slot_materials


# === V4 端点 ===

@router.post("/api/workflow/slot/build_material_pool")
async def build_material_pool(request: Dict = Body(...)):
    """
    V4 素材池统一构建：进入 Step 3 时调用
    请求体: { session_id, mcp_summary, mcp_files }
    """
    session_id = request.get("session_id", "")
    if not session_id:
        return _error(code=400, msg="缺少 session_id")

    try:
        pool = _ensure_material_pool(
            session_id,
            mcp_summary=request.get("mcp_summary", ""),
            mcp_files=request.get("mcp_files", []),
        )
        return _success({"material_pool": pool, "count": len(pool)})
    except Exception as e:
        logger.error(f"[MaterialPool] 构建失败: {e}")
        return _error_internal(e)


@router.post("/api/workflow/slot/generate_slots")
async def generate_slots(request: Dict = Body(...)):
    """
    V4 SSE 流式槽位生成
    请求体: { session_id, topic, material_pool_summary }
    返回: SSE 流，事件类型: thinking | slot | done | error
    """
    import time
    
    session_id = request.get("session_id", "")
    topic = request.get("topic", "")
    material_pool_summary = request.get("material_pool_summary", "")
    angle_context = request.get("angle_context", {})

    if not session_id:
        return _error(code=400, msg="缺少 session_id")

    async def event_generator():
        _gen_start = time.time()
        try:
            llm_config = _get_config("llm")
            base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
            api_key = llm_config.get("api_key", "")
            model = V4_PRO

            if not api_key:
                yield f"data: {json.dumps({'type': 'error', 'msg': 'LLM 配置缺失'})}\n\n"
                return
            
            # 确保素材池已构建并获取统计
            session = _get_session(session_id)
            pool = _ensure_material_pool(
                session_id,
                mcp_summary=session.get("mcp_summary", ""),
                mcp_files=session.get("mcp_files", [])
            )
            
            # 从 session 获取补充内容统计
            step2 = session.get("step2", {})
            supplement_2 = step2.get("supplement_2", {})
            supplement_files = supplement_2.get("files", [])
            supplement_materials = supplement_2.get("materials", [])
            material_count = len(pool)
            file_count = len(supplement_files)
            ai_material_count = len(supplement_materials)

            prompt = f"""你是一个内容架构师。请根据以下主题和素材信息，设计内容槽位。

【创作主题】
{topic}

【素材统计】
本次共读取到 {material_count} 条素材（其中包含 {file_count} 个文件，{ai_material_count} 条 AI 补充素材）

【素材池概览】
{material_pool_summary if material_pool_summary else '暂无额外素材'}

{_build_angle_context_prompt(angle_context)}"""

            import asyncio as _asyncio

            # 立即发送 started 事件，让浏览器知道连接已建立
            yield f"data: {json.dumps({'type': 'started'})}\n\n"

            # 用 Queue + Task 实现 LLM 调用和心跳并行
            event_queue = _asyncio.Queue()
            llm_result_holder = {}

            async def _do_llm_call():
                # [V4] 有意不迁移到 _call_llm：SSE 心跳模式下 logger 隔离度更高；
                # 且下方有独立的 thinking_logs 手动记录（避免双重日志）
                async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10)) as client:
                    response = await client.post(
                        f"{base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        json={
                            "model": model,
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": 2048,
                            "temperature": 0.7,
                            "stream": False,
                        },
                    )
                    response.raise_for_status()
                    llm_result_holder["result"] = response.json()
                await event_queue.put(("llm_done", None))

            async def _do_heartbeat():
                while True:
                    await _asyncio.sleep(2)
                    await event_queue.put(("heartbeat", None))

            _asyncio.ensure_future(_do_llm_call())
            _heartbeat_task = _asyncio.ensure_future(_do_heartbeat())

            # 主循环：消费心跳和等待 LLM 完成
            while True:
                event_type, _ = await event_queue.get()
                if event_type == "heartbeat":
                    yield f": heartbeat\n\n"
                elif event_type == "llm_done":
                    _heartbeat_task.cancel()
                    break

            llm_result = llm_result_holder.get("result")
            if not llm_result:
                yield f"data: {json.dumps({'type': 'error', 'msg': 'LLM 调用失败'}, ensure_ascii=False)}\n\n"
                return

            content = llm_result["choices"][0]["message"]["content"].strip()
            # 使用 _extract_json 智能提取 JSON（兼容 LLM 前后附加说明文字）
            cleaned = _extract_json(content)
            try:
                result = json.loads(cleaned)
            except (json.JSONDecodeError, ValueError):
                result = _safe_json_parse(cleaned, "slots")

            # 发送 structured thinking
            thinking = result.get("thinking", "")
            if thinking:
                yield f"data: {json.dumps({'type': 'thinking', 'text': thinking}, ensure_ascii=False)}\n\n"

            # 逐槽位发送
            slots = result.get("slots", [])
            
            # 0 个槽位：抛 error，不是静默 done
            if not slots or len(slots) == 0:
                yield f"data: {json.dumps({'type': 'error', 'msg': 'AI 未能识别有效槽位，请重试或手动补充素材'}, ensure_ascii=False)}\n\n"
                return

            yield f"data: {json.dumps({'type': 'done', 'slots': slots}, ensure_ascii=False)}\n\n"

            # 保存到 session
            session = _get_session(session_id)
            session["confirmed_slots"] = slots
            logger.info(f"[GenerateSlots] session={session_id}: {len(slots)}个槽位")

            # 记录思考日志
            if "thinking_logs" not in session:
                session["thinking_logs"] = []
            slots_chain = [{"step": 1, "action": "分析主题与素材库", "reason": f"基于{material_count}条素材（含{file_count}个文件、{ai_material_count}条AI补充），提取核心主题", "result": f"共生成{len(slots)}个内容槽位"}]
            for i, s in enumerate(slots):
                slots_chain.append({
                    "step": i + 2,
                    "action": f"槽位「{s.get('label', s.get('slot_key', '未知'))}」",
                    "reason": f"槽位类型：{s.get('label', '未知')}，描述：{s.get('description', '未指定')}，相关素材来源于素材库",
                    "result": "槽位已生成"
                })
            session["thinking_logs"].append({
                "call_id": "generate_slots",
                "call_name": "槽位生成",
                "phase": "槽位生成",
                "session_id": session_id,
                "start_time": _gen_start,
                "end_time": time.time(),
                "duration": time.time() - _gen_start,
                "model": model,
                "temperature": 0.3,
                "status": "success",
                "full_prompt": prompt[:8000],
                "thinking_chain": slots_chain,
                "final_output": json.dumps(slots, ensure_ascii=False)[:5000],
                "result": f"生成了{len(slots)}个槽位：{'、'.join([s.get('label', s.get('key', '')) for s in slots[:5]])}",
                "log_id": f"log_generate_{int(time.time() * 1000)}"
            })

        except Exception as e:
            logger.error(f"[GenerateSlots] 失败: {e}")
            # 记录错误日志
            session = _get_session(session_id)
            if session:
                if "thinking_logs" not in session:
                    session["thinking_logs"] = []
                session["thinking_logs"].append({
                    "call_id": "generate_slots",
                    "call_name": "槽位生成",
                    "phase": "槽位生成",
                    "session_id": session_id,
                    "start_time": _gen_start,
                    "end_time": time.time(),
                    "duration": time.time() - _gen_start,
                    "status": "failed",
                    "error": str(e),
                    "thinking_chain": [{"step": 1, "action": "槽位生成失败", "reason": f"LLM调用或解析过程中发生错误：{str(e)[:200]}", "result": "生成中断，未产出槽位"}],
                    "log_id": f"log_generate_err_{int(time.time() * 1000)}"
                })
            yield f"data: {json.dumps({'type': 'error', 'msg': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/api/workflow/slot/slot_relations")
async def slot_relations(request: Dict = Body(...)):
    """
    V4 生成槽位间关系图谱
    请求体: { session_id, confirmed_slots }
    """
    session_id = request.get("session_id", "")
    confirmed_slots = request.get("confirmed_slots", [])

    if not session_id:
        return _error(code=400, msg="缺少 session_id")
    if len(confirmed_slots) < 2:
        return _success({"relations": [], "graph_description": "槽位不足2个，无需关系图谱"})

    try:
        llm_config = _get_config("llm")
        base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
        api_key = llm_config.get("api_key", "")
        model = V4_FLASH

        if not api_key:
            return _success({"relations": [], "graph_description": "LLM 未配置"})

        slot_list = "\n".join(
            f"- {s.get('slot_key', '')}: {s.get('label', '')} ({s.get('description', '')})"
            for s in confirmed_slots
        )

        prompt = f"""你是一个内容架构师。请分析以下槽位之间的逻辑关系。

【槽位清单】
{slot_list}

请分析每对相邻槽位之间的逻辑关系（如：因果、递进、对比、并列、总分、举例等），并描述整体的关系图谱。

返回 JSON 格式（不要 markdown 代码块）：
{{
  "graph_description": "整体关系描述（50-100字）",
  "relations": [
    {{"from": "slot_1", "to": "slot_2", "label": "关系类型（如递进/因果/对比）"}}
  ]
}}"""

        result = await _call_llm(
            session_id=session_id,
            call_name="槽位关联分析",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.3,
            seed=42,
            phase="结构组织",
        )
        parsed = result["choices"][0]["message"]["content"].strip()
        parsed = _extract_json(parsed)
        data = json.loads(parsed)

        logger.info(f"[SlotRelations] session={session_id}: {len(data.get('relations', []))}条关系")
        
        # 记录思考日志
        relations = data.get("relations", [])
        graph_desc = data.get("graph_description", "")
        # 统计关系类型
        from collections import Counter
        type_counts = Counter(r.get("relation", "其他") for r in relations)
        type_desc = "、".join(f"{k} {v} 组" for k, v in type_counts.items())
        
        _log_process_step(
            session_id=session_id,
            call_name="槽位关联分析",
            phase="结构组织",
            steps=[
                {"step": 1, "action": "识别槽位间逻辑关系",
                 "reason": f"对 {len(confirmed_slots)} 个槽位进行关联分析，找出逻辑先后顺序",
                 "result": f"发现 {len(relations)} 组关联关系：{type_desc}"},
                {"step": 2, "action": "生成关系图谱描述",
                 "reason": "基于关联关系，生成文章整体逻辑描述，指导后续提纲编排",
                 "result": graph_desc[:200] + ("..." if len(graph_desc) > 200 else "")},
            ],
            output=f"关联分析完成：{len(relations)} 组关联，{type_desc}",
            duration=999,
        )

        return _success(data)

    except Exception as e:
        logger.error(f"[SlotRelations] 失败: {e}")
        return _error_internal(e)


@router.post("/api/workflow/slot/match_materials")
async def match_materials(request: Dict = Body(...)):
    """
    V4 素材匹配：将素材池按关键词分配到槽位
    请求体: { session_id, confirmed_slots }
    """
    session_id = request.get("session_id", "")
    confirmed_slots = request.get("confirmed_slots", [])

    if not session_id:
        return _error(code=400, msg="缺少 session_id")

    try:
        result = _match_materials_internal(session_id, confirmed_slots)
        # 计算每个槽位的匹配数
        stats = {k: len(v) for k, v in result.items()}
        return _success({"slot_materials": result, "stats": stats})
    except Exception as e:
        logger.error(f"[MatchMaterials] 失败: {e}")
        return _error_internal(e)


@router.post("/api/workflow/slot/pre_check_materials")
async def pre_check_materials(request: Dict = Body(...)):
    """
    V4 素材可行性预检：统计每个槽位素材覆盖度 + AI 替换建议
    请求体: { session_id, confirmed_slots }
    返回: { slot_key: { count, level: "full"|"partial"|"empty", alternatives } }
    """
    session_id = request.get("session_id", "")
    confirmed_slots = request.get("confirmed_slots", [])

    if not session_id:
        return _error(code=400, msg="缺少 session_id")

    try:
        # 强制重建素材池（确保包含最新的 step2 补充素材）
        session = _get_session(session_id)
        _ensure_material_pool(session_id,
            mcp_summary=session.get("mcp_summary", ""),
            mcp_files=session.get("mcp_files", []))
        pool = session.get("material_pool", [])
        logger.info(f"[PreCheck] session={session_id} 素材池大小: {len(pool)}条")

        # 先匹配
        slot_mats = _match_materials_internal(session_id, confirmed_slots)

        results = {}
        for slot in confirmed_slots:
            slot_key = slot.get("slot_key", "")
            matches = slot_mats.get(slot_key, [])
            count = len(matches)

            if count >= 3:
                level = "full"
            elif count >= 1:
                level = "partial"
            else:
                level = "empty"

            results[slot_key] = {
                "count": count,
                "level": level,
                "alternatives": [],
                "matched_texts": [m["text"][:100] for m in matches[:3]],
                "matched_files": [{"filename": m.get("filename", ""), "source_type": m.get("source_type", "")} for m in matches[:5]],
            }

        # AI 为 empty/partial 槽位建议替代方案
        empty_or_partial = [
            s for s in confirmed_slots
            if results.get(s.get("slot_key", ""), {}).get("level") in ("empty", "partial")
        ]

        if empty_or_partial:
            llm_config = _get_config("llm")
            api_key = llm_config.get("api_key", "")
            if api_key:
                pool_texts = "\n".join(
                    f"[{item.get('source_type', '')}] {item.get('text', '')[:200]}"
                    for item in pool
                )
                poor_slots = "\n".join(
                    f"- {s.get('slot_key')}: {s.get('label')}({s.get('description')})"
                    for s in empty_or_partial
                )

                prompt = f"""以下槽位的素材覆盖不足或为空，请从素材池中推荐可替换的匹配方案。

【覆盖不足的槽位】
{poor_slots}

【素材池】
{pool_texts}

为每个覆盖不足的槽位推荐 1-2 个可替换素材（从素材池中选择最接近的文本块）。

返回 JSON（不要 markdown 代码块）：
{{
  "suggestions": {{
    "slot_key": [
      {{"label": "推荐的素材标题（10字内）", "text_preview": "素材内容前50字"}}
    ]
  }}
}}"""

                result = await _call_llm(
                    session_id=session_id,
                    call_name="precheck_materials",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1024,
                    temperature=0.3,
                    seed=42,
                    phase="素材检查",
                )
                parsed = result["choices"][0]["message"]["content"].strip()
                parsed = parsed.replace("```json", "").replace("```", "").strip()
                suggestions = json.loads(parsed).get("suggestions", {})
                for sk, alts in suggestions.items():
                    if sk in results:
                        results[sk]["alternatives"] = alts

        logger.info(f"[PreCheck] session={session_id}: "
                    f"full={sum(1 for v in results.values() if v['level']=='full')}, "
                    f"partial={sum(1 for v in results.values() if v['level']=='partial')}, "
                    f"empty={sum(1 for v in results.values() if v['level']=='empty')}")
        # 附带动雷达上下文（选题时雷达扫出的不足）
        radar_ctx = session.get("radar_context", {})
        radar_topics = radar_ctx.get("topics", [])
        current_topic = session.get("step1", {}).get("selected_direction", "")
        radar_baseline = {}
        match = _match_radar_topic(radar_topics, current_topic)
        if match:
            radar_baseline = {
                "deficiency_details": match.get("deficiency_details", []),
                "satisfied_details": match.get("satisfied_details", []),
                "signal_report": match.get("signal_report", {}),
                "topic_name": match.get("name", ""),
            }
        return _success({
            "check_results": results,
            "material_pool_size": len(pool),
            "radar_baseline": radar_baseline,  # 选题雷达的原始分析结果
        })

    except Exception as e:
        logger.error(f"[PreCheck] 失败: {e}")
        return _error_internal(e)


@router.post("/api/workflow/slot/content_preview")
async def slot_content_preview(request: Dict = Body(...)):
    """槽位内容预览：基于素材+方向+主题，展示该槽位预计写成的样子
    
    请求体: { session_id, slot_key, slot_label, slot_description, topic, direction }
    """
    session_id = request.get("session_id", "")
    slot_key = request.get("slot_key", "")
    slot_label = request.get("slot_label", "")
    slot_desc = request.get("slot_description", "")
    topic = request.get("topic", "")
    direction = request.get("direction", "")

    if not session_id or not slot_key:
        return _error(code=400, msg="缺少必要参数")

    session = _get_session(session_id)
    mcp_summary = session.get("mcp_summary", "")

    # 收集匹配素材
    _ensure_material_pool(session_id,
        mcp_summary=mcp_summary,
        mcp_files=session.get("mcp_files", []))
    pool = session.get("material_pool", [])

    # 为这个槽位匹配素材
    slots_for_match = [{"slot_key": slot_key, "label": slot_label, "description": slot_desc}]
    slot_mats = _match_materials_internal(session_id, slots_for_match)
    matches = slot_mats.get(slot_key, [])

    if not matches:
        return _success({"preview": f"【{slot_label}】暂无素材匹配，请先补充相关素材后预览。"})

    mat_texts = "\n".join(
        f"- [{m.get('source_type', '')}] {m.get('text', '')[:300]}"
        for m in matches[:5]
    )

    llm_config = _get_config("llm")
    api_key = llm_config.get("api_key", "")
    if not api_key:
        return _success({
            "preview": f"【{slot_label}】已匹配 {len(matches)} 条素材（含：{', '.join(m.get('filename', '') for m in matches[:3])}），请手动编辑完成此槽位。"
        })

    prompt = f"""你是一个专业内容写手。请基于以下素材，为槽位「{slot_label}」写一段内容预览。

【写作主题】
{topic}

【写作方向】
{direction}

【槽位说明】
{slot_label}: {slot_desc}

【可用素材】
{mat_texts[:2000]}

要求：写 2-4 句内容预览，说明该槽位将涵盖哪些要点、基于哪些素材，用自然的中文段落表达。不要写成大纲列表，要像真正的段落预览一样流畅。

直接返回预览文字，不要JSON、不要markdown代码块。"""

    try:
        result = await _call_llm(
            session_id=session_id,
            call_name="slot_preview",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.5,
            phase="内容预览",
        )
        preview = result["choices"][0]["message"]["content"].strip()
        return _success({"preview": preview})
    except Exception as e:
        logger.warning(f"槽位预览失败: {e}")
        return _success({
            "preview": f"【{slot_label}】已匹配 {len(matches)} 条素材。预览生成失败，请稍后重试。"
        })


@router.post("/api/workflow/slot/batch_fill_v4")
async def batch_fill_v4(request: Dict = Body(...)):
    """
    V4 批量填充（为每个槽位生成提纲 + 匹配素材）
    请求体: { session_id, confirmed_slots, web_search_enabled }
    """
    session_id = request.get("session_id", "")
    confirmed_slots = request.get("confirmed_slots", [])
    web_search_enabled = request.get("web_search_enabled", False)

    if not session_id:
        return _error(code=400, msg="缺少 session_id")
    if not confirmed_slots:
        return _error(code=400, msg="至少需要一个槽位")

    try:
        session = _get_session(session_id)
        mcp_summary = session.get("mcp_summary", "")

        # P3: 确保素材池（含 AIPULSE 预拉取结果）
        pool = session.get("material_pool", [])
        if not pool:
            aipulse_items = session.get("aipulse_items")
            _ensure_material_pool(session_id, mcp_summary=mcp_summary, aipulse_items=aipulse_items)

        # L3: 联网兜底（用户手动开启时，用 DuckDuckGo 搜索补充素材）
        if web_search_enabled:
            try:
                from src.web_search import search_web_batch
                topic = session.get('step1', {}).get('direction', '')
                # 用 topic + 各槽位 label 作为搜索词
                search_queries = [topic[:60]] if topic else []
                for s in confirmed_slots:
                    label = s.get("label", "")
                    if label and len(label) > 2:
                        search_queries.append(f"{topic[:30]} {label[:20]}" if topic else label[:30])
                search_queries = search_queries[:3]  # 最多 3 个搜索词
                web_results = await search_web_batch(search_queries, max_per_query=4)
                if web_results:
                    pool = session.get("material_pool", [])
                    for r in web_results:
                        pool.append({
                            "text": f"{r.get('title', '')}：{r.get('snippet', '')}",
                            "source_type": "web_search",
                            "filename": r.get("title", "web_result")[:100],
                            "source_name": r.get("url", "Web 搜索"),
                        })
                    session["material_pool"] = pool
                    logger.info(f"[WebFallback] 联网搜索成功: {len(web_results)}条 → pool")
                else:
                    logger.info("[WebFallback] 联网搜索 0 条结果")
            except Exception as e:
                logger.warning(f"[WebFallback] 联网搜索失败（不影响主流程）: {e}")

        # 第一轮匹配（用 label+desc 做素材匹配，给提纲生成提供上下文）
        slot_mats = _match_materials_internal(session_id, confirmed_slots)

        # 为每个槽位生成提纲 + 搜索关键词
        llm_config = _get_config("llm")
        base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
        api_key = llm_config.get("api_key", "")
        model = V4_FLASH

        slot_outlines = {}
        slot_search_kw = {}  # P3: 存储每槽位的搜索关键词

        if api_key:
            for slot in confirmed_slots:
                slot_key = slot.get("slot_key", "")
                label = slot.get("label", "")
                desc = slot.get("description", "")
                mats = slot_mats.get(slot_key, [])
                mat_texts = "\n".join(
                    f"- [{m.get('source_type', '')}] {m.get('text', '')[:200]}"
                    for m in mats[:5]
                ) if mats else "暂无匹配素材"

                prompt = f"""请为以下内容槽位生成提纲。

【主题】{session.get('step1', {}).get('direction', '') if session.get('step1') else ''}
【槽位】{label}：{desc}
【匹配素材】
{mat_texts}

请生成 3-5 个提纲要点，每个要点是一句话。
同时生成 3-5 个搜索关键词，用于在知识库中检索更多相关素材（关键词需体现该槽位的核心概念）。

返回 JSON（不要 markdown）：
{{
  "outline": [
    {{"order": 1, "point": "要点内容"}}
  ],
  "search_keywords": ["关键词1", "关键词2", "关键词3"]
}}"""

                try:
                    result = await _call_llm(
                        session_id=session_id,
                        call_name="批量填充",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=1024,
                        temperature=0.5,
                        seed=42,
                        phase="批量填充",
                    )
                    parsed = result["choices"][0]["message"]["content"].strip()
                    parsed = parsed.replace("```json", "").replace("```", "").strip()
                    outline_data = json.loads(parsed)
                    slot_outlines[slot_key] = outline_data.get("outline", [])
                    slot_search_kw[slot_key] = outline_data.get("search_keywords", [])
                except Exception:
                    pass  # 单个槽位 AI 失败不阻塞其余槽位
        # P3: 第二轮匹配（用 label+desc+search_keywords，匹配更准）
        if slot_search_kw:
            slot_mats = _match_materials_internal(session_id, confirmed_slots, search_keywords=slot_search_kw)

        # W1: LLM 语义分配 AIPULSE 素材到槽位
        slot_mats = await _match_aipulse_by_llm(session_id, confirmed_slots, slot_mats)

        session["slot_outlines"] = slot_outlines
        session["slot_materials"] = slot_mats

        logger.info(f"[BatchFillV4] session={session_id}: {len(confirmed_slots)}个槽位填充完成")
        
        # 记录思考日志
        fill_steps = [{
            "step": 1, "action": "素材匹配",
            "reason": f"为 {len(confirmed_slots)} 个槽位在知识库中匹配相关素材",
            "result": f"匹配完成，每槽匹配 1-5 段素材片段"
        }]
        if web_search_enabled:
            fill_steps.append({
                "step": 2, "action": "联网搜索补充",
                "reason": "用户开启了联网搜索，用槽位关键词检索外部资料",
                "result": "联网搜索结果已并入素材池"
            })
        outline_step = 3 if web_search_enabled else 2
        total_outline_points = 0
        total_keywords = 0
        for slot in confirmed_slots:
            slot_key = slot.get("slot_key", "")
            label = slot.get("label", slot_key)
            mats = slot_mats.get(slot_key, [])
            outline = slot_outlines.get(slot_key, [])
            kw = slot_search_kw.get(slot_key, [])
            total_outline_points += len(outline)
            total_keywords += len(kw)
            mat_brief = "、".join([m.get("source_type", "素材") for m in mats[:3]])
            fill_steps.append({
                "step": outline_step,
                "action": f"「{label}」：生成提纲 + 匹配素材",
                "reason": f"匹配到 {len(mats)} 段素材（{mat_brief or '无'}），AI 生成了 {len(outline)} 点提纲、{len(kw)} 个搜索关键词",
                "result": "提纲已就绪，可进入写稿阶段"
            })
            outline_step += 1
        
        _log_process_step(
            session_id=session_id,
            call_name="批量填充",
            phase="写稿准备",
            steps=fill_steps,
            output=f"批量填充完成：{len(confirmed_slots)} 个槽位，共 {total_outline_points} 点提纲，{total_keywords} 个搜索关键词",
            duration=999,  # duration will be set properly
        )
        
        return _success({
            "slot_materials": slot_mats,
            "slot_outlines": slot_outlines,
        })

    except Exception as e:
        logger.error(f"[BatchFillV4] 失败: {e}")
        return _error_internal(e)


# === W2-2: 整合生成端点 ===

@router.post("/api/workflow/slot/integrate_outline")
async def integrate_outline(request: Dict = Body(...)):
    """
    将提纲碎片+素材整合为连贯提纲。
    请求: { session_id, slot_key, slot_label, current_outline, materials, writing_plan }
    """
    session_id = request.get("session_id", "")
    slot_label = request.get("slot_label", "")
    current_outline = request.get("current_outline", [])
    materials = request.get("materials", [])
    writing_plan = request.get("writing_plan", "")

    if not session_id or not current_outline:
        return _error(code=400, msg="缺少必要参数")

    try:
        # 构建提纲文本
        outline_text = "\n".join(
            f"{o.get('order', i+1)}. {o.get('point', '')}"
            for i, o in enumerate(current_outline)
        )
        # 构建素材文本
        mat_texts = "\n".join(
            f"- [{m.get('source_type', '')}] {m.get('text', '')[:200]}"
            for m in materials[:8]
        ) if materials else "无补充素材"

        prompt = f"""你是一个提纲整合器。请分两步完成整合，严格按格式输出。

## 第一步：理解层（必须先完成，不能跳过）
输入：当前提纲、补充素材
任务：
1. 提取当前提纲的核心主题（old_theme）和每条的视角（old_perspectives）
2. 分析补充素材能提供什么新维度（new_dimensions），每条标 relation：
   - complement：异视角互补（如"闭坑经验"+"技术趋势"，同一槽位的不同侧面）
   - extend：同视角扩展（如"闭坑经验"+"新增案例"，同一个方向延伸）
   - conflict：真冲突（结论相反，需[待核实]处理）
3. 输出 analysis JSON

## 第二步：编排层（基于第一步的 analysis 结果）
任务：按 analysis 的 relation 编排提纲，输出 points 数组
- complement → 分层递进排列（先讲旧的视角，再讲新视角，最后融合落地）
- extend → 合并到对应旧条目的视角中
- conflict → 两条都保留，弱势方标注 [待核实]

## 输出格式（严格 JSON，不要 markdown，不要代码块标记）
{{
  "thinking_chain": [
    {{"step": 1, "action": "分析当前提纲", "reason": "基于输入的提纲碎片", "result": "旧提纲核心主题是XX，包含X个视角..."}},
    {{"step": 2, "action": "分析补充素材", "reason": "基于输入的素材", "result": "素材提供了XX个新维度，与旧提纲是XX关系"}},
    {{"step": 3, "action": "编排提纲", "reason": "基于analysis的relation", "result": "最终编排为X条提纲，逻辑递进"}}
  ],
  "points": [
    {{"order": 1, "point": "...", "from": "旧视角A"}},
    {{"order": 2, "point": "...", "from": "新维度B"}}
  ],
  "result": "整合后的完整提纲要点文本"
}}

## 约束
1. thinking_chain 必须输出至少3步
2. 所有输入的提纲条目必须保留核心语义，仅当两条内容完全重复时可合并，禁止丢弃单条
3. points 必须基于 analysis 的 relation 编排
4. 输出条数 3-5 条。若当前提纲≥3条且无新增维度，保持原条数
5. 不要复述素材内容，只整合要点
6. 保持逻辑递进

## 输入
【槽位名称】{slot_label}
【写作方案】{writing_plan if writing_plan else '无特殊要求'}
【当前提纲（可能来自多次分析的不同视角）】
{outline_text}
【关联素材】
{mat_texts}"""

        # 调用统一流式LLM工具
        result = await stream_llm_call(
            session_id=session_id,
            call_id=f"integrate_outline_{slot_label}",
            call_name=f"{slot_label} - 提纲整合生成",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            require_thinking_chain=False  # 上面的Prompt已经包含了思考链要求
        )

        # 丰富最近一条日志的 thinking_chain：提纲整合详情
        session = _get_session(session_id)
        if session:
            logs = session.get("thinking_logs", [])
            if logs:
                last = logs[-1]
                mat_count = len(materials) if materials else 0
                outline_len = len(current_outline) if current_outline else 0
                chain = [{
                    "step": 1, "action": f"槽位「{slot_label}」提纲整合",
                    "reason": f"基于{outline_len}条当前提纲和{mat_count}条关联素材进行整合分析",
                    "result": f"提纲整合完成，当前分析进度：槽位「{slot_label}」"
                }]
                if writing_plan:
                    chain.append({"step": 2, "action": "写作方案约束", "reason": f"应用写作方案：{writing_plan[:100]}", "result": "已纳入方案约束"})
                chain.append({"step": len(chain) + 1, "action": "整合策略", "reason": "分析新旧提纲的互补关系、扩展关系和冲突关系，按分层递进策略重新编排", "result": "整合策略已执行"})
                last["thinking_chain"] = chain

        # 解析 points（兼容两种格式）
        final_output = result.get("final_output", "")
        try:
            # 先尝试直接从result中拿
            if "points" in result:
                points = result["points"]
            else:
                # 尝试解析final_output中的JSON
                parsed = json.loads(final_output.strip())
                points = parsed.get("points", [])
                if not points:
                    # 如果没有points，用result作为单一要点
                    points = [{"order": 1, "point": result.get("result", final_output)}]
            
            logger.info(
                f"[IntegrateOutline] 整合完成 "
                f"points={len(points)}"
            )
            return _success({
                "integrated_outline": points,
                "thinking_chain": result.get("thinking_chain", []),
                "log_id": result.get("log_id", ""),
            })
        except Exception as parse_e:
            logger.warning(f"[IntegrateOutline] 解析points失败: {parse_e}，fallback到原文")
            # fallback：把原文按行拆成points
            lines = [l.strip() for l in final_output.split('\n') if l.strip()]
            points = [{"order": i+1, "point": l} for i, l in enumerate(lines[:5])]
            return _success({
                "integrated_outline": points,
                "thinking_chain": result.get("thinking_chain", []),
                "log_id": result.get("log_id", ""),
            })

    except Exception as e:
        logger.error(f"[IntegrateOutline] 失败: {e}")
        return _error_internal(e)


# === W3: 联网搜索端点（按槽位） ===

@router.post("/api/workflow/slot/web_search")
async def web_search_slot(request: Dict = Body(...)):
    """
    按槽位联网搜索补充素材。
    请求: { session_id, slot_key, slot_label }
    """
    session_id = request.get("session_id", "")
    slot_key = request.get("slot_key", "")
    slot_label = request.get("slot_label", "")

    if not session_id or not slot_label:
        return _error(code=400, msg="缺少必要参数")

    try:
        session = _get_session(session_id)
        direction = session.get("step1", {}).get("direction", "") if session.get("step1") else ""
        topic = direction if direction else slot_label

        from src.web_search import search_web_batch
        queries = [
            f"{topic[:30]} {slot_label[:20]}",
            f"{slot_label} 最新 案例",
        ]
        results = await search_web_batch(queries, max_per_query=4)

        # 格式化返回
        formatted = []
        for r in results:
            formatted.append({
                "title": r.get("title", ""),
                "snippet": r.get("snippet", ""),
                "url": r.get("url", ""),
            })

        # 存储到 session（供后续使用）
        pool = session.get("material_pool", [])
        for r in results:
            pool.append({
                "text": f"{r.get('title', '')}：{r.get('snippet', '')}",
                "source_type": "web_search",
                "filename": r.get("title", "web_result")[:100],
                "source_name": r.get("url", ""),
            })
        session["material_pool"] = pool

        logger.info(f"[WebSearch] 槽位搜索: {slot_label} → {len(formatted)}条")
        return _success({"results": formatted, "count": len(formatted)})

    except Exception as e:
        logger.error(f"[WebSearch] 失败: {e}")
        return _error_internal(e)


@router.post("/api/workflow/slot/generate_outline")
async def generate_slot_outline(request: Dict = Body(...)):
    """
    V4 生成单个槽位提纲
    请求体: { session_id, slot_key, topic, materials, writing_plan }
    """
    session_id = request.get("session_id", "")
    slot_key = request.get("slot_key", "")
    topic = request.get("topic", "")
    materials = request.get("materials", [])
    writing_plan = request.get("writing_plan", "")

    if not session_id or not slot_key:
        return _error(code=400, msg="缺少 session_id 或 slot_key")

    try:
        llm_config = _get_config("llm")
        base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
        api_key = llm_config.get("api_key", "")
        model = V4_PRO

        if not api_key:
            return _error(msg="LLM 未配置")

        mat_texts = "\n".join(
            f"- {m.get('text', '')[:200]}" for m in materials[:5]
        ) if materials else "暂无素材"

        prompt = f"""请为以下内容槽位生成提纲。

【主题】{topic}
【槽位】{slot_key}
【写作方向】{writing_plan if writing_plan else '无特殊要求'}
【参考素材】
{mat_texts}

请生成 3-5 个提纲要点。

返回 JSON（不要 markdown）：
{{
  "outline": [
    {{"order": 1, "point": "要点内容"}}
  ]
}}"""

        result = await _call_llm(
            session_id=session_id,
            call_name="slot_outline",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.5,
            seed=42,
            phase="槽位提纲",
        )
        parsed = result["choices"][0]["message"]["content"].strip()
        parsed = parsed.replace("```json", "").replace("```", "").strip()
        try:
            outline = json.loads(parsed).get("outline", [])
        except (json.JSONDecodeError, ValueError):
            outline = _safe_json_parse(parsed, "outline").get("outline", [])

        # 保存到 session
        session = _get_session(session_id)
        if "slot_outlines" not in session:
            session["slot_outlines"] = {}
        session["slot_outlines"][slot_key] = outline

        return _success({"outline": outline})

    except Exception as e:
        logger.error(f"[GenerateOutline] 失败: {e}")
        return _error_internal(e)


@router.post("/api/workflow/slot/ask_followup")
async def ask_followup(request: Dict = Body(...)):
    """
    V4 追问 AI（支持槽位确认/编辑面板两种场景）
    请求体: { session_id, context, slot_key, question, history }
    """
    session_id = request.get("session_id", "")
    context = request.get("context", "slot_confirmation")
    slot_key = request.get("slot_key", "")
    question = request.get("question", "")
    history = request.get("history", [])

    if not session_id or not question:
        return _error(code=400, msg="缺少 session_id 或 question")

    try:
        llm_config = _get_config("llm")
        base_url = llm_config.get("base_url", "https://api.deepseek.com/v1")
        api_key = llm_config.get("api_key", "")
        model = V4_PRO

        if not api_key:
            return _error(msg="LLM 未配置")

        # 构建上下文
        session = _get_session(session_id)
        mcp_summary = session.get("mcp_summary", "")

        messages = [{
            "role": "system",
            "content": f"""你是内容创作助手，帮助用户完善文章框架。

当前上下文：
- 话题：{session.get('step1', {}).get('direction', '')}
- MCP 素材概览：{mcp_summary[:500] if mcp_summary else '无'}
- 当前槽位：{slot_key if slot_key else '未指定'}
- 场景：{'槽位确认阶段' if context == 'slot_confirmation' else '编辑面板'}

用中文回答，简洁专业。"""
        }]

        # 追加历史对话
        for h in history[-5:]:  # 最多5轮
            if isinstance(h, dict):
                if h.get("q"):
                    messages.append({"role": "user", "content": h["q"]})
                if h.get("a"):
                    messages.append({"role": "assistant", "content": h["a"]})

        messages.append({"role": "user", "content": question})

        result = await _call_llm(
            session_id=session_id,
            call_name="ask_followup",
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
            phase="槽位追问",
        )
        answer = result["choices"][0]["message"]["content"].strip()
        return _success({"answer": answer})

    except Exception as e:
        logger.error(f"[AskFollowup] 失败: {e}")
        return _error_internal(e)


@router.post("/api/workflow/slot/analyze")
async def analyze_slot(request: Dict = Body(...)):
    """
    H3: 槽位素材分析（替代自由追问 AI）
    请求体: { session_id, slot_key, analysis_type, materials, outline }
    analysis_type: core_points | outline_relation | expand_outline | extension_direction
    """
    session_id = request.get("session_id", "")
    slot_key = request.get("slot_key", "")
    analysis_type = request.get("analysis_type", "core_points")
    materials = request.get("materials", [])
    outline = request.get("outline", [])

    if not session_id:
        return _error(msg="缺少 session_id")
    if not slot_key:
        return _error(msg="缺少 slot_key")

    try:
        session = _get_session(session_id)
        direction = session.get("step1", {}).get("selected_direction", {})
        direction_text = direction.get("description", direction.get("title", "")) if isinstance(direction, dict) else str(direction)

        # 构建素材文本摘要
        material_texts = []
        for m in materials[:10]:
            text = (m.get("text", "") or "")[:800]
            name = m.get("source_name", m.get("filename", ""))
            if text.strip():
                material_texts.append(f"--- {name} ---\n{text}")
        materials_block = "\n\n".join(material_texts) if material_texts else "（暂无素材）"

        # 构建提纲文本
        outline_text = "\n".join([f"{i+1}. {o.get('point', o.get('text', ''))}" for i, o in enumerate(outline)]) if outline else "（暂无提纲）"

        # 各分析类型的 system prompt
        type_names = {
            "core_points": "核心观点提炼",
            "outline_relation": "提纲关联分析",
            "expand_outline": "提纲扩写",
            "extension_direction": "延伸方向建议",
        }
        type_prompts = {
            "core_points": "你是一个资深分析助手。请根据下面提供的素材，提炼出最核心的3-5个观点。每个观点用一句话概括，然后给出简短解释。只基于素材内容，不要编造。",
            "outline_relation": "你是一个写作顾问。当前槽位的提纲已经列出，下面提供了与该槽位匹配的素材。请分析：素材内容和当前提纲之间存在怎样的关联？提纲是否需要调整？哪些素材最能支撑哪个提纲点？",
            "expand_outline": "你是一个写作助手。请根据下面提供的素材内容，扩写当前提纲。对每个提纲点补充具体的子要点、数据支撑或案例引用。保持结构清晰，不要改动提纲的原有顺序和核心论点。",
            "extension_direction": "你是一个创意顾问。基于当前槽位的素材和提纲，提出2-3个可以延伸讨论的方向。每个方向包含：方向名称、一句话理由、建议补充什么类型的素材。思考素材中没有覆盖但值得探讨的角度。",
        }
        system_prompt = type_prompts.get(analysis_type, type_prompts["core_points"])
        type_name = type_names.get(analysis_type, "分析")

        user_prompt = f"""[写作方向]
{direction_text or '(未指定)'}

[当前槽位]
{slot_key}

[该槽位的素材]
{materials_block}

[当前提纲]
{outline_text}

请根据上述内容进行分析。

【输出格式要求】
请先输出你的思考过程，再输出最终分析结果，严格按以下JSON格式返回：
{{
  "thinking_chain": [
    {{ "step": 1, "action": "阅读并理解素材", "reason": "素材提供了哪些关键信息", "result": "核心信息是..." }},
    {{ "step": 2, "action": "分析提纲与素材关联", "reason": "素材与提纲的匹配度", "result": "第X条提纲最能被素材Y支撑..." }},
    {{ "step": 3, "action": "提炼最终结果", "reason": "综合所有信息", "result": "..." }}
  ],
  "result": "最终分析结果"
}}"""

        # 调用统一流式LLM工具
        llm_result = await stream_llm_call(
            session_id=session_id,
            call_id=f"analyze_{slot_key}_{analysis_type}",
            call_name=f"{slot_key} - {type_name}",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            require_thinking_chain=False  # 上面的Prompt已经包含了思考链要求
        )

        # 丰富最近一条日志的 thinking_chain：槽位分析详情
        if session:
            logs = session.get("thinking_logs", [])
            if logs:
                last = logs[-1]
                mat_count = len(materials) if materials else 0
                chain = [{
                    "step": 1, "action": f"槽位「{slot_key}」{type_name}",
                    "reason": f"对槽位「{slot_key}」进行{type_name}分析，当前已加载{mat_count}条关联素材",
                    "result": f"{type_name}分析完成"
                }]
                last["thinking_chain"] = chain

        result = llm_result.get("result", llm_result.get("final_output", ""))
        return _success({
            "result": result,
            "analysis_type": analysis_type,
            "slot_key": slot_key,
            "thinking_chain": llm_result.get("thinking_chain", []),
            "log_id": llm_result.get("log_id", ""),
        })

    except Exception as e:
        logger.error(f"[AnalyzeSlot] 失败: {e}")
        return _error_internal(e)
