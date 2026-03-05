"""
Behavior Recorder Service 主入口
FastAPI 应用启动文件
"""

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.endpoints import router as api_router
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
    title="Behavior Recorder Service",
    description="自闭症干预辅助系统 - 行为记录员微服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置 CORS（允许前端访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载前端静态文件（如果存在）
frontend_dist = Path(__file__).parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
    logger.info(f"前端静态文件已挂载：{frontend_dist}")
else:
    logger.info("前端静态文件未找到，仅 API 可用")

# 注册 API 路由
app.include_router(api_router, prefix="/api")

logger.info("FastAPI 应用初始化完成")


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    config = get_config()
    logger.info("=" * 50)
    logger.info("Behavior Recorder Service 启动")
    logger.info(f"LLM Provider: {config.llm_provider}")
    logger.info(f"LLM Model: {config.llm_model}")
    logger.info(f"Server: {config.server_host}:{config.server_port}")
    logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("Behavior Recorder Service 关闭")


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    uvicorn.run(
        "main:app",
        host=config.server_host,
        port=config.server_port,
        reload=config.debug,
    )
