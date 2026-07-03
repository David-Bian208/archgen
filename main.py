"""ArchGen - 架构生成器主入口"""

import os
import logging
import yaml
import asyncio
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
    
    # 初始化埋点数据库
    from src.analytics_tracker import get_analytics_tracker
    tracker = get_analytics_tracker()
    await tracker.init_db()
    logging.info("埋点数据库初始化完成")
    
    # 启动后自动解析身份定位文件（六维模型）
    try:
        from api import auto_parse_persona
        # 在后台任务中解析，不阻塞启动
        asyncio.create_task(auto_parse_persona(app))
        logging.info("已启动身份定位自动解析任务")
    except Exception as e:
        logging.warning(f"身份定位自动解析启动失败: {e}")
    
    logging.info("ArchGen 启动完成")
    yield
    logging.info("ArchGen 关闭中...")


def load_config() -> dict:
    """加载配置文件"""
    config_path = Path(__file__).parent / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    # 递归替换 ${ENV_VAR} 占位符为环境变量值
    config = _resolve_env_vars(config)
    # 将相对路径转换为绝对路径，避免因工作目录不同导致路径错误
    base_dir = Path(__file__).parent
    if 'knowledge_base' in config:
        root_path = config.get('knowledge_base', {}).get('root_path', '')
        if root_path and not os.path.isabs(root_path):
            config['knowledge_base']['root_path'] = str(base_dir / root_path)
    if 'logging' in config:
        log_file = config.get('logging', {}).get('file', '')
        if log_file and not os.path.isabs(log_file):
            config['logging']['file'] = str(base_dir / log_file)
    if 'storage' in config:
        output_dir = config.get('storage', {}).get('output_dir', '')
        if output_dir and not os.path.isabs(output_dir):
            config['storage']['output_dir'] = str(base_dir / output_dir)
        temp_dir = config.get('storage', {}).get('temp_dir', '')
        if temp_dir and not os.path.isabs(temp_dir):
            config['storage']['temp_dir'] = str(base_dir / temp_dir)
    if 'database' in config:
        db_path = config.get('database', {}).get('path', '')
        if db_path and not os.path.isabs(db_path):
            config['database']['path'] = str(base_dir / db_path)
    return config


def _resolve_env_vars(value):
    """递归替换配置中的 ${ENV_VAR} 为环境变量值"""
    # 尝试加载 .env 文件（如果环境变量未设置）
    import os
    env_path = Path(__file__).parent / "config" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip("'\"")
                if k not in os.environ:
                    os.environ[k] = v
    import re
    if isinstance(value, str):
        def replace_match(m):
            var_name = m.group(1)
            default = m.group(2)
            env_val = os.environ.get(var_name)
            if env_val is not None:
                return env_val
            if default is not None:
                return default
            return m.group(0)
        return re.sub(r'\$\{([^}:]+)(?::([^}]*))?\}', replace_match, value)
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    config = load_config()

    # 安全检查：确保 .env 文件已正确排除
    env_path = Path(__file__).parent / "config" / ".env"
    if env_path.exists():
        gitignore_path = Path(__file__).parent / ".." / ".gitignore"
        gitignore_content = ""
        if gitignore_path.exists():
            gitignore_content = gitignore_path.read_text()
        if "config/.env" not in gitignore_content and ".env" not in gitignore_content:
            print("\033[33m⚠️  警告: config/.env 存在但未在 .gitignore 中排除\033[0m")
        # 检查 API Key 是否仅通过文件提供（建议用环境变量）
        api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if api_key:
            source = "环境变量" if "DEEPSEEK_API_KEY" in str(os.environ.keys()) else "config/.env"
            print(f"\033[36mℹ️  API Key 来源: {source}\033[0m")

    # 配置日志（带轮转，防止写满磁盘）
    from logging.handlers import RotatingFileHandler
    log_file = config["logging"]["file"]
    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    logging.basicConfig(
        level=getattr(logging, config["logging"]["level"]),
        format=config["logging"]["format"],
        handlers=[
            logging.StreamHandler(),
            file_handler,
        ],
    )

    app = FastAPI(
        title=config["app"]["name"],
        version=config["app"]["version"],
        lifespan=lifespan,
    )

    # 保存配置到 app state
    app.state.config = config

    # 配置 CORS（从配置文件读取）
    cors_origins = config.get("cors", {}).get("allow_origins", [
        "http://localhost:3018",
    ])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
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
