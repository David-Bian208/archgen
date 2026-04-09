"""
OpenAI 兼容 LLM 客户端实现
支持 DashScope、DeepSeek 等 OpenAI 兼容 API
"""
import os
import json
import requests
from typing import Optional
from .base import LLMClient


class OpenAIClient(LLMClient):
    """OpenAI 兼容 API 客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        初始化 LLM 客户端

        Args:
            api_key: API 密钥，默认从 LLM_API_KEY 读取（兼容 DASHSCOPE_API_KEY）
            base_url: API 基础 URL，默认从 LLM_BASE_URL 读取（兼容 DASHSCOPE_BASE_URL）
            model: 模型名称，默认从 LLM_MODEL 读取（兼容 DASHSCOPE_MODEL）
        """
        self.api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL") or os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.model = model or os.getenv("LLM_MODEL") or os.getenv("DASHSCOPE_MODEL", "qwen-plus")

        if not self.api_key:
            raise ValueError("API 密钥未设置，请设置 LLM_API_KEY 或 DASHSCOPE_API_KEY 环境变量")

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })

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
            temperature: 温度参数 (0-1)
            max_tokens: 最大 token 数

        Returns:
            生成的文本
        """
        response = self._chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response

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
            max_tokens: 最大 token 数

        Returns:
            解析后的 JSON 字典
        """
        text = self.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        # 提取 markdown 代码块中的 JSON
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析失败：{e}\n原始响应：{text[:500]}")

    def _chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> str:
        """
        调用聊天完成 API

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            API 返回的文本内容
        """
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        response = self.session.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"]
