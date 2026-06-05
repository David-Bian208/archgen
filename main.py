"""ArchGen - 架构生成器主入口"""

import os
import logging
import yaml
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from src.storage import StorageManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logging.info("ArchGen 启动中...")
    app.state.storage = StorageManager(app.state.config["database"]["path"])
    await app.state.storage.init_db()
    logging.info("ArchGen 启动完成")
    yield
    logging.info("ArchGen 关闭中...")


def load_config() -> dict:
    """加载配置文件"""
    config_path = Path(__file__).parent / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    config = load_config()

    # 配置日志
    logging.basicConfig(
        level=getattr(logging, config["logging"]["level"]),
        format=config["logging"]["format"],
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(config["logging"]["file"], encoding="utf-8"),
        ],
    )

    app = FastAPI(
        title=config["app"]["name"],
        version=config["app"]["version"],
        lifespan=lifespan,
    )

    # 保存配置到 app state
    app.state.config = config

    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 挂载静态文件
    output_dir = Path(config["storage"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")

    # 注册路由
    import api
    api.set_app(app)
    app.include_router(api.router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=app.state.config["app"]["host"],
        port=app.state.config["app"]["port"],
        reload=app.state.config["app"]["debug"],
    )
