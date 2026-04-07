"""
行为观察伙伴 V4.11.2
主入口 - FastAPI 应用启动文件

仅使用 V4 API（endpoints_v4.py）
"""

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

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
    title="行为观察伙伴 V4.11.2",
    description="自闭症儿童行为观察与评估工具 - 基于 ABC 行为分析理论",
    version="4.11.2",
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

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "version": "V4.11.2"
    }

# 后台管理页面
@app.get("/admin")
async def admin_panel():
    """后台管理页面"""
    admin_html = Path(__file__).parent / "admin.html"
    if admin_html.exists():
        return FileResponse(str(admin_html))
    return {"error": "后台页面未找到"}

logger.info("FastAPI 应用初始化完成")


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    config = get_config()
    logger.info("=" * 50)
    logger.info("行为观察伙伴 V4.11.2 启动")
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
    import multiprocessing

    config = get_config()
    
    # 性能优化：根据 CPU 核心数设置 worker 数量
    # 公式：worker_num = (2 * cpu_cores) + 1（uvicorn 推荐）
    cpu_count = multiprocessing.cpu_count()
    worker_num = min((2 * cpu_count) + 1, 4)  # 最多 4 个 worker，避免过度占用资源
    
    logger.info(f"CPU 核心数：{cpu_count}, 设置 worker 数量：{worker_num}")
    
    uvicorn.run(
        "main:app",
        host=config.server_host,
        port=config.server_port,
        workers=worker_num,  # 多进程模式
        reload=config.debug,
        loop="uvloop",  # 使用 uvloop 提升性能
        http="httptools",  # 使用 httptools 提升 HTTP 解析性能
    )
