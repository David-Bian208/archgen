"""
V6.2 API 端点 - LLM 驱动临床推理优化版

核心特性：
- 4 次 LLM 调用（V6.2 合并 Step 2+3）
- SSE 流式输出（5 步展示，用户体验不变）
- 质量底线验证

版本历史：
V6.1 - 2026-04-22: 首次 LLM 驱动版（5 次 LLM 调用）
V6.2 - 2026-04-22: 效率优化版（4 次 LLM 调用，合并 Step 2+3）
"""

import json
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Body
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from app.agents.clinical_reasoning_engine import ClinicalReasoningEngine
from app.llm.openai_client import OpenAIClient
from app.config import get_config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["V6.1 LLM 驱动推理"])  # 移除 prefix，由 main.py 统一添加


def get_v6_engine() -> ClinicalReasoningEngine:
    """获取 V6.1 临床推理引擎实例"""
    config = get_config()
    llm_client = OpenAIClient(
        api_key=config.llm_api_key,
        base_url=config.llm_base_url,
        model=config.llm_model,
        timeout=60,
    )
    return ClinicalReasoningEngine(llm_client)


@router.post("/analyze", summary="V6.1 临床推理分析")
async def analyze_v6(
    user_input: str = Body(..., embed=True, description="用户输入的行为描述"),
    child_age: Optional[int] = Body(None, embed=True, description="孩子年龄"),
):
    """
    V6.1 LLM 驱动临床推理
    
    核心流程：
    1. 场景识别（LLM 分类）
    2. 假设生成（LLM 动态生成）
    3. 证据检验（引用用户原话）
    4. 机制解释（含新颖比喻）
    5. 干预策略（从机制推导）
    
    Args:
        user_input: 用户输入的行为描述
        child_age: 孩子年龄（可选）
    
    Returns:
        V6.1 推理结果（JSON）
    """
    try:
        engine = get_v6_engine()
        
        # 执行完整 5 步推理（同步方法，不用 await）
        result = engine.run_full_reasoning(user_input)
        
        return {
            "status": "success",
            "version": "V6.1.0",
            "data": result,
        }
        
    except Exception as e:
        logger.error(f"V6.1 分析失败：{e}")
        raise HTTPException(status_code=500, detail=f"V6.1 分析失败：{str(e)}")


@router.get("/analyze/stream", summary="V6.1 临床推理 SSE 流式输出")
async def analyze_stream_v6(
    input: str,
    session_id: Optional[str] = None,
):
    """
    V6.1 SSE 流式输出 - 5 步推理过程可视化
    
    每完成一步就推送给前端，实现思考过程实时展示
    
    Args:
        input: 用户输入
        session_id: 会话 ID（可选）
    
    Returns:
        SSE 流式响应
    """
    engine = get_v6_engine()
    
    async def event_generator():
        try:
            # Step 1: 场景识别
            logger.info(f"🔍 Step 1: 场景识别")
            step1 = await engine.step1_scene_recognition(input)
            yield {
                "event": "step",
                "data": json.dumps({
                    "stepIndex": 0,
                    "name": "场景识别",
                    "output": step1,
                }, ensure_ascii=False),
            }
            
            # Step 2: 假设生成
            logger.info(f"🧠 Step 2: 假设生成")
            step2 = await engine.step2_hypothesis_generation(input, step1)
            yield {
                "event": "step",
                "data": json.dumps({
                    "stepIndex": 1,
                    "name": "假设生成",
                    "output": step2,
                }, ensure_ascii=False),
            }
            
            # Step 3: 证据检验
            logger.info(f"🔬 Step 3: 证据检验")
            step3 = await engine.step3_evidence_examination(input, step2)
            yield {
                "event": "step",
                "data": json.dumps({
                    "stepIndex": 2,
                    "name": "证据检验",
                    "output": step3,
                }, ensure_ascii=False),
            }
            
            # Step 4: 机制解释
            logger.info(f"💡 Step 4: 机制解释")
            step4 = await engine.step4_mechanism_explanation(input, step1, step3)
            yield {
                "event": "step",
                "data": json.dumps({
                    "stepIndex": 3,
                    "name": "机制解释",
                    "output": step4,
                }, ensure_ascii=False),
            }
            
            # Step 5: 干预策略
            logger.info(f"🎯 Step 5: 干预策略")
            step5 = await engine.step5_intervention_planning(input, step4)
            yield {
                "event": "step",
                "data": json.dumps({
                    "stepIndex": 4,
                    "name": "干预策略",
                    "output": step5,
                }, ensure_ascii=False),
            }
            
            # 最终报告
            logger.info(f"📊 生成最终报告")
            report = engine.generate_report({
                "step1": step1,
                "step2": step2,
                "step3": step3,
                "step4": step4,
                "step5": step5,
            })
            yield {
                "event": "report",
                "data": json.dumps({
                    "html": report,
                }, ensure_ascii=False),
            }
            
        except Exception as e:
            logger.error(f"SSE 流式输出失败：{e}")
            yield {
                "event": "error",
                "data": json.dumps({
                    "message": f"推理过程出错：{str(e)}",
                }, ensure_ascii=False),
            }
    
    return EventSourceResponse(event_generator())


@router.get("/health", summary="V6.1 健康检查")
async def health_check_v6():
    """V6.1 健康检查"""
    return {
        "status": "ok",
        "version": "V6.1.0",
        "engine": "LLM-driven",
        "maintenance_cost": "minimal",
    }
