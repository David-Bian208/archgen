"""
V4.3 结构化评估引导器 API 端点（统一入口版）

V4.3 核心修复：
- /api/v4/chat 统一指向 StructuredAssessorV4（V4.3 引擎）
- /api/v4/v43/chat 保留但标记为弃用
- 系统版本统一标识为 V4.3（稳定版）
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.agents.structured_assessor_v4 import StructuredAssessorV4
from app.config import get_config
from app.llm.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

router = APIRouter()

_agent_v43: StructuredAssessorV4 | None = None


def get_agent_v43() -> StructuredAssessorV4:
    """
    获取 V4.3 结构化评估引导器实例
    
    V4.3 统一引擎：StructuredAssessorV4
    - 框架驱动：基于 clinical_assessment_framework.json
    - 工作流推进：BACKGROUND → CORE_ABC → DIFFERENTIAL → REPORT
    - 智能推断：环境、假设自动推断
    """
    global _agent_v43

    if _agent_v43 is None:
        config = get_config()
        llm_client = OpenAIClient(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
            model=config.llm_model,
        )
        framework_path = "app/knowledge/clinical_assessment_framework.json"
        _agent_v43 = StructuredAssessorV4(llm_client, framework_path)
        logger.info("V4.3 Agent 实例已创建 - 结构化临床评估引导器（统一入口版）")

    return _agent_v43


@router.post(
    "/chat",
    response_model=dict[str, Any],
    summary="V4.3 结构化临床评估对话（统一入口）",
    description="V4.3 稳定版：基于评估框架表的结构化信息收集，5 轮内高效收敛，智能环境推断",
)
async def chat_v4(request: dict[str, Any]):
    """
    V4.3 对话接口 - 统一官方入口
    
    V4.3 核心特性：
    1. 框架驱动：每个问题对应评估框架中的明确字段
    2. 工作流推进：BACKGROUND → CORE_ABC → DIFFERENTIAL → REPORT
    3. 智能推断：根据年龄和情境自动推断环境（幼儿园/家庭/学校）
    4. 高效收敛：必填字段完成后立即触发报告
    5. 无重复追问：已填充字段不再询问

    Args:
        request: 包含 session_id（可选）和 user_input

    Returns:
        对话响应，包含进度信息、推断环境、假设置信度
    """
    session_id = request.get("session_id")
    user_input = request.get("user_input", "").strip()

    if not user_input:
        raise HTTPException(status_code=400, detail="user_input 不能为空")

    logger.info(f"V4.3 收到对话：session={session_id}, input={user_input[:50]}...")

    try:
        agent = get_agent_v43()
        response = agent.process(session_id, user_input)

        progress = response.get("progress", {})
        logger.info(f"V4.3 响应：status={response['status']}, turns={progress.get('total_turns', 'N/A')}, env={progress.get('inferred_environment', 'N/A')}")
        return response

    except Exception as e:
        logger.error(f"V4.3 对话失败：{e}")
        raise HTTPException(status_code=500, detail=f"对话失败：{str(e)}")


# ========== V4.3 会话管理端点 ==========

@router.get(
    "/session/{session_id}",
    response_model=dict[str, Any],
    summary="获取 V4.3 会话状态",
)
async def get_session_v43(session_id: str):
    """获取 V4.3 会话信息"""
    agent = get_agent_v43()
    session = agent.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    return {
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat(),
        "current_stage": session.current_stage,
        "turn_count": session.turn_count,
        "is_complete": session.is_complete,
        "completion_rate": session.get_overall_completion_rate(agent.framework.data),
        "filled_fields": {k: v.value for k, v in session.filled_data.items() if v.value},
        "inferred_hypotheses": session.inferred_hypotheses,
    }


@router.delete(
    "/session/{session_id}",
    response_model=dict[str, Any],
    summary="清理 V4.3 会话",
)
async def delete_session_v43(session_id: str):
    """清理 V4.3 会话"""
    agent = get_agent_v43()
    success = agent.cleanup_session(session_id)

    return {
        "success": success,
        "message": "会话已清理" if success else "会话不存在",
    }


# ========== 弃用端点（保留向后兼容）==========

@router.post(
    "/v43/chat",
    response_model=dict[str, Any],
    summary="V4.3 对话（弃用，请使用 /chat）",
    description="⚠️ 此端点已弃用，请使用 /api/v4/chat",
    deprecated=True,
)
async def chat_v43_deprecated(request: dict[str, Any]):
    """V4.3 对话接口（弃用）"""
    # 重定向到主端点
    return await chat_v4(request)
