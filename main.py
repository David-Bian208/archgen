"""
行为观察伙伴 V4.10.4
主入口 - FastAPI 应用启动文件

仅使用 V4 API（endpoints_v4.py）
"""

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.endpoints_v4 import router as api_v4_router
from app.config import get_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="行为观察伙伴 V4.10.4",
    description="自闭症儿童行为观察与评估工具 - 基于 ABC 行为分析理论",
    version="4.10.4",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(api_v4_router, prefix="/api/v4")

logger.info("FastAPI 应用初始化完成")


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    config = get_config()
    logger.info("=" * 50)
    logger.info("行为观察伙伴 V4.10.4 启动")
    logger.info(f"LLM Provider: {config.llm_provider}")
    logger.info(f"LLM Model: {config.llm_model}")
    logger.info(f"Server: {config.server_host}:{config.server_port}")
    logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("行为观察伙伴 关闭")


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    uvicorn.run(
        "main:app",
        host=config.server_host,
        port=config.server_port,
        reload=config.debug,
    )
