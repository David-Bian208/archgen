"""
V4.8.0 结构化评估引导器 API 端点（统一入口版）

V4.8.0 核心新增：
- 支持儿童背景信息（出生日期、阶段）
- 发展期待对标（基于年龄和阶段的精准诊断）

V4.3 核心修复（保留）：
- /api/v4/chat 统一指向 StructuredAssessorV4（V4.3 引擎）
- /api/v4/v43/chat 保留但标记为弃用
- 系统版本统一标识为 V4.8.0（稳定版）
"""

import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException

from app.agents.structured_assessor_v4 import StructuredAssessorV4
from app.config import get_config
from app.llm.openai_client import OpenAIClient
from app.utils.test_db import get_database

logger = logging.getLogger(__name__)

router = APIRouter()

_agent_v43: StructuredAssessorV4 | None = None


def get_agent_v43() -> StructuredAssessorV4:
    """
    获取 V4.8.0 结构化评估引导器实例
    
    V4.8.0 统一引擎：StructuredAssessorV4
    - 框架驱动：基于 clinical_assessment_framework.json
    - 工作流推进：BACKGROUND → CORE_ABC → DIFFERENTIAL → REPORT
    - 智能推断：环境、假设自动推断
    - V4.8.0 新增：支持儿童背景信息（出生日期、阶段）
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
        logger.info("V4.8.0 Agent 实例已创建 - 结构化临床评估引导器（带背景信息支持）")

    return _agent_v43


@router.post(
    "/chat",
    response_model=dict[str, Any],
    summary="V4.8.0 结构化临床评估对话（带背景信息）",
    description="V4.8.0 稳定版：基于评估框架表的结构化信息收集，支持儿童背景信息（年龄、阶段）",
)
async def chat_v4(request: dict[str, Any]):
    """
    V4.8.0 对话接口 - 统一官方入口
    
    V4.8.0 核心特性：
    1. 框架驱动：每个问题对应评估框架中的明确字段
    2. 工作流推进：BACKGROUND → CORE_ABC → DIFFERENTIAL → REPORT
    3. 智能推断：根据年龄和情境自动推断环境（幼儿园/家庭/学校）
    4. 高效收敛：必填字段完成后立即触发报告
    5. 无重复追问：已填充字段不再询问
    6. V4.8.0 新增：支持儿童背景信息（出生日期、阶段），用于发展期待对标

    Args:
        request: 包含 session_id（可选）、user_input、child_profile（可选）

    Returns:
        对话响应，包含进度信息、推断环境、假设置信度
    """
    session_id = request.get("session_id")
    user_input = request.get("user_input", "").strip()
    child_profile = request.get("child_profile")  # V4.8.0 新增

    if not user_input:
        raise HTTPException(status_code=400, detail="user_input 不能为空")

    start_time = time.time()
    logger.info(f"V4.8.0 收到对话：session={session_id}, input={user_input[:50]}..., profile={child_profile}")

    try:
        agent = get_agent_v43()
        # V4.8.0 新增：传递 child_profile 参数
        response = agent.process(session_id, user_input, child_profile)
        
        # 计算响应时间
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # 记录测试日志（V4.10.4 新增）
        try:
            db = get_database()
            # 创建/更新会话
            db.create_or_update_session(session_id, child_profile)
            # 记录对话日志
            db.add_test_log(
                session_id=session_id,
                user_input=user_input,
                ai_response=response,
                turn_number=response.get("progress", {}).get("total_turns", 1),
                response_time_ms=response_time_ms,
                stage=response.get("progress", {}).get("current_stage", "")
            )
            # 如果完成，标记会话
            if response.get("status") == "completed":
                db.complete_session(session_id, response.get("data", {}))
            logger.info(f"测试日志已记录：session={session_id}")
        except Exception as db_error:
            logger.warning(f"测试日志记录失败（不影响主功能）: {db_error}")

        progress = response.get("progress", {})
        logger.info(f"V4.8.0 响应：status={response['status']}, turns={progress.get('total_turns', 'N/A')}, env={progress.get('inferred_environment', 'N/A')}")
        return response

    except Exception as e:
        logger.error(f"V4.8.0 对话失败：{e}")
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


# ========== V4.10.4 测试日志与反馈端点 ==========

@router.post(
    "/feedback",
    response_model=dict[str, Any],
    summary="提交用户反馈",
    description="用户对 AI 输出进行评分和反馈",
)
async def submit_feedback(request: dict[str, Any]):
    """
    提交用户反馈
    
    Args:
        request: 包含 session_id, rating(1-5), accuracy(accurate/partial/inaccurate),
                feedback_text, improvement_suggestion
    
    Returns:
        提交结果
    """
    session_id = request.get("session_id")
    rating = request.get("rating")
    accuracy = request.get("accuracy")
    feedback_text = request.get("feedback_text", "")
    improvement_suggestion = request.get("improvement_suggestion", "")
    
    if not session_id or not rating:
        raise HTTPException(status_code=400, detail="session_id 和 rating 是必填项")
    
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="rating 必须在 1-5 之间")
    
    if accuracy and accuracy not in ['accurate', 'partial', 'inaccurate']:
        raise HTTPException(status_code=400, detail="accuracy 必须是 accurate/partial/inaccurate")
    
    try:
        db = get_database()
        db.add_feedback(
            session_id=session_id,
            rating=rating,
            accuracy=accuracy or 'partial',
            feedback_text=feedback_text,
            improvement_suggestion=improvement_suggestion
        )
        logger.info(f"用户反馈已保存：session={session_id}, rating={rating}")
        return {"status": "success", "message": "感谢你的反馈！"}
    
    except Exception as e:
        logger.error(f"保存反馈失败：{e}")
        raise HTTPException(status_code=500, detail=f"保存失败：{str(e)}")


@router.get(
    "/test/logs",
    response_model=dict[str, Any],
    summary="获取测试日志（管理员用）",
    description="查询测试日志数据",
)
async def get_test_logs(session_id: str = None, limit: int = 100):
    """
    获取测试日志
    
    Args:
        session_id: 会话 ID（可选）
        limit: 返回数量限制
    
    Returns:
        测试日志列表
    """
    try:
        db = get_database()
        logs = db.get_test_report(session_id=session_id, limit=limit)
        return {
            "status": "success",
            "count": len(logs),
            "data": logs
        }
    except Exception as e:
        logger.error(f"获取测试日志失败：{e}")
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")


@router.get(
    "/test/feedback-summary",
    response_model=dict[str, Any],
    summary="获取反馈汇总（管理员用）",
    description="查看用户反馈统计信息",
)
async def get_feedback_summary():
    """
    获取反馈汇总统计
    
    Returns:
        反馈统计信息
    """
    try:
        db = get_database()
        summary = db.get_feedback_summary()
        return {
            "status": "success",
            "data": summary
        }
    except Exception as e:
        logger.error(f"获取反馈汇总失败：{e}")
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")


@router.post(
    "/test/export",
    response_model=dict[str, Any],
    summary="导出测试数据为 CSV（管理员用）",
    description="导出所有测试日志到 CSV 文件",
)
async def export_test_data(output_path: str = "test_logs_export.csv"):
    """
    导出测试数据
    
    Args:
        output_path: 输出文件路径
    
    Returns:
        导出结果
    """
    try:
        db = get_database()
        db.export_to_csv(output_path)
        return {
            "status": "success",
            "message": f"数据已导出到：{output_path}",
            "file": output_path
        }
    except Exception as e:
        logger.error(f"导出数据失败：{e}")
        raise HTTPException(status_code=500, detail=f"导出失败：{str(e)}")
