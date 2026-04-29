"""
行为观察伙伴 V6.1.0
主入口 - FastAPI 应用启动文件

核心特性：
- LLM 驱动的临床推理引擎
- 5 步推理过程可视化（SSE 流式输出）
- 质量底线验证
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
from api.endpoints_v6 import router as api_v6_router
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
    title="行为观察伙伴 V6.1.0",
    description="自闭症儿童行为观察与评估工具 - LLM 驱动临床推理",
    version="6.1.0",
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
app.include_router(api_v6_router, prefix="/api/v6")  # V6.1 LLM 驱动推理

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "version": "V6.1.0"
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
    logger.info("行为观察伙伴 V6.1.0 启动")
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
    
    # V4.11.1 性能优化：多 worker 配置
    uvicorn.run(
        "main:app",
        host=config.server_host,
        port=config.server_port,
        workers=4,  # 4 个 worker 进程，提升并发能力
        reload=False,  # 生产环境关闭 reload
        access_log=True,
    )
