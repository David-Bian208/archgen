"""
V3.0 共情访谈模式 API 端点
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.agents.guided_recorder_agent_v3 import GuidedRecorderAgentV3
from app.config import get_config
from app.llm.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

router = APIRouter()

_agent_v3: GuidedRecorderAgentV3 | None = None


def get_agent_v3() -> GuidedRecorderAgentV3:
    """获取 V3.0 Agent 实例"""
    global _agent_v3

    if _agent_v3 is None:
        config = get_config()
        llm_client = OpenAIClient(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
            model=config.llm_model,
        )
        _agent_v3 = GuidedRecorderAgentV3(llm_client)
        logger.info("V3.0 Agent 实例已创建")

    return _agent_v3


@router.post(
    "/chat",
    response_model=dict[str, Any],
    summary="V3.0 共情访谈",
    description="自然对话模式，像与治疗师交谈",
)
async def chat_v3(request: dict[str, Any]):
    """
    V3.0 对话接口

    Args:
        request: 包含 session_id（可选）和 user_input

    Returns:
        对话响应
    """
    session_id = request.get("session_id")
    user_input = request.get("user_input", "").strip()

    if not user_input:
        raise HTTPException(status_code=400, detail="user_input 不能为空")

    logger.info(f"V3.0 收到对话：session={session_id}, input={user_input[:50]}...")

    try:
        agent = get_agent_v3()
        response = agent.process_input(session_id, user_input)

        logger.info(f"V3.0 响应：status={response['status']}")
        return response

    except Exception as e:
        logger.error(f"V3.0 对话失败：{e}")
        raise HTTPException(status_code=500, detail=f"对话失败：{str(e)}")


@router.get(
    "/session/{session_id}",
    response_model=dict[str, Any],
    summary="获取 V3.0 会话状态",
)
async def get_session_v3(session_id: str):
    """获取会话信息"""
    agent = get_agent_v3()
    session = agent.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    return {
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat(),
        "is_complete": session.is_complete,
        "context": session.context,
        "child_behavior": session.child_behavior,
        "others_response": session.others_response,
        "insight_result": session.insight_result,
        "conversation_count": len(session.conversation_history),
    }


@router.delete(
    "/session/{session_id}",
    response_model=dict[str, Any],
    summary="清理 V3.0 会话",
)
async def delete_session_v3(session_id: str):
    """清理会话"""
    agent = get_agent_v3()
    success = agent.cleanup_session(session_id)

    return {
        "success": success,
        "message": "会话已清理" if success else "会话不存在",
    }
