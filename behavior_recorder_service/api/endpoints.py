"""
FastAPI 路由端点
提供行为分析和干预策略的 API 接口
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.agents.behavior_recorder_agent import BehaviorRecorderAgent
from app.agents.intervention_planner import InterventionPlannerAgent
from app.config import get_config
from app.llm.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

router = APIRouter()

# 全局 Agent 实例（延迟初始化）
_recorder_agent: BehaviorRecorderAgent | None = None
_planner_agent: InterventionPlannerAgent | None = None


def get_recorder_agent() -> BehaviorRecorderAgent:
    """获取或创建行为记录员 Agent 实例（单例模式）"""
    global _recorder_agent

    if _recorder_agent is None:
        config = get_config()

        # 创建 LLM 客户端
        llm_client = OpenAIClient(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
            model=config.llm_model,
        )

        # 创建 Agent
        _recorder_agent = BehaviorRecorderAgent(llm_client)
        logger.info("BehaviorRecorderAgent 实例已创建")

    return _recorder_agent


def get_planner_agent() -> InterventionPlannerAgent:
    """获取或创建干预策略分析师 Agent 实例（单例模式）"""
    global _planner_agent

    if _planner_agent is None:
        config = get_config()

        # 创建 LLM 客户端
        llm_client = OpenAIClient(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
            model=config.llm_model,
        )

        # 创建 Agent
        _planner_agent = InterventionPlannerAgent(llm_client)
        logger.info("InterventionPlannerAgent 实例已创建")

    return _planner_agent


class AnalyzeRequest:
    """分析请求模型"""

    description: str


class AnalyzeResponse:
    """分析响应模型"""

    antecedent: str
    behavior: str
    consequence: str
    hypothesized_function: str
    success: bool
    message: str


@router.post(
    "/analyze",
    response_model=dict[str, Any],
    summary="行为分析",
    description="对家长描述的行为进行 ABC 分析和功能假设",
)
async def analyze_behavior(request: dict[str, str]):
    """
    行为分析接口

    Args:
        request: 包含 description 字段的请求体

    Returns:
        ABC 分析结果

    Raises:
        HTTPException: 当分析失败时
    """
    description = request.get("description", "").strip()

    if not description:
        raise HTTPException(
            status_code=400, detail="description 字段不能为空"
        )

    logger.info(f"收到分析请求：{description[:100]}...")

    try:
        agent = get_agent()
        result = agent.analyze(description)

        response = {
            "success": True,
            "message": "分析成功",
            "data": result,
        }

        logger.info(f"分析完成：{result}")
        return response

    except Exception as e:
        logger.error(f"分析失败：{e}")
        raise HTTPException(
            status_code=500, detail=f"分析失败：{str(e)}"
        )


@router.get(
    "/health",
    response_model=dict[str, Any],
    summary="健康检查",
    description="检查服务健康状态",
)
async def health_check():
    """健康检查接口"""
    config = get_config()
    return {
        "status": "healthy",
        "llm_provider": config.llm_provider,
        "llm_model": config.llm_model,
    }


@router.post(
    "/plan",
    response_model=dict[str, Any],
    summary="干预策略规划",
    description="基于 ABC 分析结果生成干预策略计划",
)
async def plan_intervention(request: dict[str, Any]):
    """
    干预策略规划接口

    Args:
        request: 包含 abc_result 字段的请求体（可选 description）

    Returns:
        干预策略计划

    Raises:
        HTTPException: 当规划失败时
    """
    abc_result = request.get("abc_result", {})
    description = request.get("description", "")

    if not abc_result:
        raise HTTPException(
            status_code=400, detail="abc_result 字段不能为空"
        )

    logger.info(f"收到规划请求：功能={abc_result.get('hypothesized_function')}")

    try:
        agent = get_planner_agent()
        result = agent.analyze_and_plan(description, abc_result)

        response = {
            "success": True,
            "message": "规划成功",
            "data": result,
        }

        logger.info(f"规划完成：status={result.get('status')}")
        return response

    except Exception as e:
        logger.error(f"规划失败：{e}")
        raise HTTPException(
            status_code=500, detail=f"规划失败：{str(e)}"
        )


@router.get(
    "/",
    response_model=dict[str, Any],
    summary="服务信息",
    description="获取服务基本信息",
)
async def service_info():
    """服务信息接口"""
    return {
        "name": "Behavior Recorder Service",
        "version": "1.1.0",
        "description": "自闭症干预辅助系统 - 行为记录员 + 干预策略分析师",
        "endpoints": {
            "analyze": "POST /analyze",
            "plan": "POST /plan",
            "health": "GET /health",
        },
    }
