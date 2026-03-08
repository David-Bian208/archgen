"""
V4.0 确定性状态机 API 端点
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.agents.guided_recorder_v4 import GuidedRecorderV4
from app.config import get_config
from app.llm.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

router = APIRouter()

_agent_v4: GuidedRecorderV4 | None = None


def get_agent_v4() -> GuidedRecorderV4:
    """获取 V4.0 Agent 实例"""
    global _agent_v4

    if _agent_v4 is None:
        config = get_config()
        llm_client = OpenAIClient(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
            model=config.llm_model,
        )
        _agent_v4 = GuidedRecorderV4(llm_client)
        logger.info("V4.0 Agent 实例已创建 - 确定性状态机引擎")

    return _agent_v4


@router.post(
    "/chat",
    response_model=dict[str, Any],
    summary="V4.0 确定性状态机对话",
    description="基于状态机的智能访谈流程，3-5 轮完成信息收集",
)
async def chat_v4(request: dict[str, Any]):
    """
    V4.0 对话接口 - 确定性状态机驱动

    Args:
        request: 包含 session_id（可选）和 user_input

    Returns:
        对话响应
    """
    session_id = request.get("session_id")
    user_input = request.get("user_input", "").strip()

    if not user_input:
        raise HTTPException(status_code=400, detail="user_input 不能为空")

    logger.info(f"V4.0 收到对话：session={session_id}, input={user_input[:50]}...")

    try:
        agent = get_agent_v4()
        response = agent.process(session_id, user_input)

        logger.info(f"V4.0 响应：status={response['status']}, state={response.get('state', 'N/A')}")
        return response

    except Exception as e:
        logger.error(f"V4.0 对话失败：{e}")
        raise HTTPException(status_code=500, detail=f"对话失败：{str(e)}")


@router.get(
    "/session/{session_id}",
    response_model=dict[str, Any],
    summary="获取 V4.0 会话状态",
)
async def get_session_v4(session_id: str):
    """获取会话信息"""
    agent = get_agent_v4()
    session = agent.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    return {
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat(),
        "current_state": session.current_state.value,
        "state_description": session.get_state_description(),
        "state_goal": session.get_state_goal(),
        "turn_count": session.turn_count,
        "is_data_complete": session.is_data_complete(),
        "evidence_count": len(session.evidence_log),
        "collected_data": session.collected_data,
        "is_complete": session.current_state.value == "complete",
    }


@router.delete(
    "/session/{session_id}",
    response_model=dict[str, Any],
    summary="清理 V4.0 会话",
)
async def delete_session_v4(session_id: str):
    """清理会话"""
    agent = get_agent_v4()
    success = agent.cleanup_session(session_id)

    return {
        "success": success,
        "message": "会话已清理" if success else "会话不存在",
    }
