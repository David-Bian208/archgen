"""
配置加载模块
从 config.yaml 加载配置，支持环境变量覆盖
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


class Config:
    """配置管理类"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置

        Args:
            config_path: 配置文件路径，默认查找 config.yaml
        """
        self.config_path = config_path or self._find_config_file()
        self._config: dict[str, Any] = {}
        self.load()

    def _find_config_file(self) -> str:
        """查找配置文件"""
        # 优先查找当前目录
        candidates = [
            Path("config.yaml"),
            Path(__file__).parent.parent / "config.yaml",
            Path.home() / ".behavior_recorder" / "config.yaml",
        ]

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

        # 如果都没找到，返回默认路径（用于创建示例）
        return "config.yaml"

    def load(self) -> None:
        """加载配置文件"""
        if not Path(self.config_path).exists():
            logger.warning(
                f"配置文件不存在：{self.config_path}，请使用 config.yaml.example 作为模板创建"
            )
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
            logger.info(f"配置加载成功：{self.config_path}")
        except Exception as e:
            logger.error(f"配置加载失败：{e}")
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键（支持点分隔，如 "llm.provider"）
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    @property
    def llm_provider(self) -> str:
        """LLM 提供商"""
        return self.get("llm.provider", "openai")

    @property
    def llm_api_key(self) -> str:
        """LLM API 密钥"""
        # 支持环境变量覆盖
        return os.getenv("LLM_API_KEY", "")

    @property
    def llm_base_url(self) -> str:
        """LLM API 基础 URL"""
        return os.getenv(
            "LLM_BASE_URL", 
            "https://api.deepseek.com"
        )

    @property
    def llm_model(self) -> str:
        """LLM 模型名称"""
        return os.getenv(
            "LLM_MODEL", 
            "deepseek-chat"
        )

    @property
    def server_host(self) -> str:
        """服务器 host"""
        return self.get("server.host", "0.0.0.0")

    @property
    def server_port(self) -> int:
        """服务器端口"""
        return self.get("server.port", 8000)

    @property
    def debug(self) -> bool:
        """调试模式"""
        return self.get("server.debug", False)

    @property
    def test_mode_enabled(self) -> bool:
        """测试模式是否启用"""
        return self.get("test_mode.enabled", False)

    @property
    def test_mode_require_auth(self) -> bool:
        """测试模式是否需要认证"""
        return self.get("test_mode.require_auth", False)

    @property
    def test_mode_save_history(self) -> bool:
        """测试模式是否保存历史记录"""
        return self.get("test_mode.save_history", False)

    @property
    def test_mode_aliyun_deploy(self) -> bool:
        """测试模式是否阿里云部署"""
        return self.get("test_mode.aliyun_deploy", False)

    @property
    def test_mode_public_access(self) -> bool:
        """测试模式是否公开访问"""
        return self.get("test_mode.public_access", False)


# 全局配置实例
_config: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config


def reload_config(config_path: Optional[str] = None) -> Config:
    """重新加载配置"""
    global _config
    _config = Config(config_path)
    return _config
