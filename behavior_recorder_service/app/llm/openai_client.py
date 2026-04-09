"""
OpenAI 兼容 LLM 客户端实现
支持 DashScope/DeepSeek 等 OpenAI 兼容 API

V4.11.1 性能优化：使用 httpx 连接池 + LLM 缓存
"""

import os
import json
import httpx  # V4.11.1 性能优化：使用 httpx 连接池
from typing import Optional

from .base import LLMClient
from .llm_cache import get_llm_cache  # V4.11.1 性能优化：LLM 缓存


class OpenAIClient(LLMClient):
    """OpenAI 兼容 API 客户端（httpx 连接池版本）"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        初始化 LLM 客户端
        
        Args:
            api_key: API 密钥，默认从 LLM_API_KEY 读取
            base_url: API 基础 URL，默认从 LLM_BASE_URL 读取
            model: 模型名称，默认从 LLM_MODEL 读取
        """
        self.api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL") or os.getenv("DASHSCOPE_BASE_URL", "https://api.deepseek.com")
        self.model = model or os.getenv("LLM_MODEL") or os.getenv("DASHSCOPE_MODEL", "deepseek-chat")
        
        if not self.api_key:
            raise ValueError("API 密钥未设置，请设置 LLM_API_KEY 环境变量")
        
        # V4.11.1 性能优化：httpx 连接池
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(60.0),  # 60 秒超时
            limits=httpx.Limits(
                max_keepalive_connections=10,  # 保持 10 个长连接
                max_connections=20,  # 最大 20 个连接
            ),
        )
        
        # V4.11.1 性能优化：LLM 缓存
        self.cache = get_llm_cache()
    
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
        # V4.11.1 性能优化：先尝试从缓存获取
        cached_response = self.cache.get(system_prompt, user_prompt)
        if cached_response:
            return cached_response
        
        # 缓存未命中，调用 API
        response = self._chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        # V4.11.1 性能优化：写入缓存
        self.cache.set(system_prompt, user_prompt, response)
        
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
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # V4.11.1 性能优化：使用 httpx 连接池
        response = self.client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        return data["choices"][0]["message"]["content"]
    
    def close(self):
        """关闭连接池"""
        self.client.close()
    
    def __del__(self):
        """析构函数"""
        if hasattr(self, 'client'):
            self.close()
