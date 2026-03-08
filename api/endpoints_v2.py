"""
引导式行为记录员 API 端点 V2.0
支持多轮对话会话模式
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException

from app.agents.guided_recorder_agent import GuidedRecorderAgent
from app.config import get_config
from app.llm.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

router = APIRouter()

# 全局 Agent 实例（延迟初始化）
_guided_agent: GuidedRecorderAgent | None = None


def get_guided_agent() -> GuidedRecorderAgent:
    """获取或创建引导式 Agent 实例（单例模式）"""
    global _guided_agent

    if _guided_agent is None:
        config = get_config()

        # 创建 LLM 客户端
        llm_client = OpenAIClient(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
            model=config.llm_model,
        )

        # 创建引导式 Agent
        _guided_agent = GuidedRecorderAgent(llm_client)
        logger.info("引导式 Agent 实例已创建")

    return _guided_agent


@router.post(
    "/record",
    response_model=dict[str, Any],
    summary="引导式行为记录（V2.0）",
    description="多轮对话模式，Agent 会引导家长完成 ABC 记录",
)
async def record_behavior(request: dict[str, Any]):
    """
    引导式行为记录接口

    Args:
        request: 包含 session_id（可选）和 user_input 的请求体

    Returns:
        对话响应

    Raises:
        HTTPException: 当处理失败时
    """
    session_id = request.get("session_id")
    user_input = request.get("user_input", "").strip()

    if not user_input:
        raise HTTPException(
            status_code=400, detail="user_input 不能为空"
        )

    logger.info(f"收到记录请求：session={session_id}, input={user_input[:50]}...")

    try:
        agent = get_guided_agent()
        response = agent.process_input(session_id, user_input)

        logger.info(f"记录响应：status={response['status']}, type={response['response_type']}")
        return response

    except Exception as e:
        logger.error(f"记录失败：{e}")
        raise HTTPException(
            status_code=500, detail=f"记录失败：{str(e)}"
        )


@router.get(
    "/session/{session_id}",
    response_model=dict[str, Any],
    summary="获取会话状态",
    description="查看指定会话的当前状态和历史",
)
async def get_session(session_id: str):
    """
    获取会话信息

    Args:
        session_id: 会话 ID

    Returns:
        会话信息

    Raises:
        HTTPException: 当会话不存在时
    """
    agent = get_guided_agent()
    session = agent.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    return {
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat(),
        "is_complete": session.is_complete,
        "antecedent": session.antecedent,
        "behavior": session.behavior,
        "consequence": session.consequence,
        "analysis_result": session.analysis_result,
        "conversation_count": len(session.conversation_history),
    }


@router.delete(
    "/session/{session_id}",
    response_model=dict[str, Any],
    summary="清理会话",
    description="删除指定会话",
)
async def delete_session(session_id: str):
    """
    清理会话

    Args:
        session_id: 会话 ID

    Returns:
        操作结果
    """
    agent = get_guided_agent()
    success = agent.cleanup_session(session_id)

    return {
        "success": success,
        "message": "会话已清理" if success else "会话不存在",
    }


@router.get(
    "/analyze",
    response_model=dict[str, Any],
    summary="单次行为分析（V1.1 兼容）",
    description="保留原有的单次分析接口，用于兼容性",
)
async def analyze_behavior(description: str):
    """
    单次行为分析接口（V1.1 兼容）

    Args:
        description: 行为描述

    Returns:
        分析结果
    """
    from app.agents.behavior_recorder_agent import BehaviorRecorderAgent

    if not description or not description.strip():
        raise HTTPException(status_code=400, detail="description 不能为空")

    try:
        config = get_config()
        llm_client = OpenAIClient(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
            model=config.llm_model,
        )
        agent = BehaviorRecorderAgent(llm_client)
        result = agent.analyze(description)

        return {
            "success": True,
            "message": "分析成功",
            "data": result,
        }

    except Exception as e:
        logger.error(f"分析失败：{e}")
        raise HTTPException(
            status_code=500, detail=f"分析失败：{str(e)}"
        )
