"""
LLM 客户端抽象基类
定义所有 LLM 提供商必须实现的接口
"""

from abc import ABC, abstractmethod
from typing import Optional


class LLMClient(ABC):
    """LLM 客户端抽象基类"""

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> str:
        """
        生成文本响应

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成 token 数

        Returns:
            生成的文本响应
        """
        pass

    @abstractmethod
    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> dict:
        """
        生成 JSON 响应

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数
            max_tokens: 最大生成 token 数

        Returns:
            解析后的 JSON 字典
        """
        pass
