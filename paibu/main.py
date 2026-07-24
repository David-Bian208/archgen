"""排布 (PaiBu) — 海报生成服务主入口"""
import logging
import sys
import os
from pathlib import Path

import uvicorn
import yaml
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# ---- 配置加载 ----
PROJECT_DIR = Path(__file__).parent

def _load_config() -> dict:
    yaml_path = PROJECT_DIR / "config.yaml"
    if yaml_path.exists():
        with open(yaml_path) as f:
            return yaml.safe_load(f)
    return {}

_config = _load_config()
APP_CONFIG = _config.get("app", {})
LLM_CONFIG = _config.get("llm", {})

HOST = APP_CONFIG.get("host", os.getenv("PAIBU_HOST", "0.0.0.0"))
PORT = int(APP_CONFIG.get("port", os.getenv("PAIBU_PORT", "8090")))
DEBUG = APP_CONFIG.get("debug", False)
OUTPUT_DIR = PROJECT_DIR / APP_CONFIG.get("output_dir", "output")
LOG_DIR = PROJECT_DIR / APP_CONFIG.get("log_dir", "logs")
CORS_ORIGINS = _config.get("cors", {}).get("allow_origins", ["*"])

# 确保目录存在
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ---- 日志配置 ----
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "paibu.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("paibu")

# ---- FastAPI 应用 ----
app = FastAPI(
    title="排布 PaiBu",
    description="海报生成服务 — 文章拆卡片 + 排版 + 渲染",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
static_dir = PROJECT_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 输出文件
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")

# 注册 API 路由
from api import router as api_router
app.include_router(api_router)

# 根路径 → 海报编辑页面
from fastapi.responses import FileResponse

@app.get("/")
async def serve_index():
    index_path = static_dir / "test_poster.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"service": "排布 PaiBu", "status": "ok"}


@app.get("/health")
async def health():
    return {
        "service": "排布 PaiBu",
        "status": "healthy",
        "version": "1.0.0",
        "llm_model": LLM_CONFIG.get("model", os.getenv("PAIBU_LLM_MODEL", "deepseek-v4-flash")),
    }


if __name__ == "__main__":
    logger.info(f"排布 PaiBu 启动在 http://{HOST}:{PORT}")
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level="debug" if DEBUG else "info",
    )
