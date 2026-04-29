"""
OpenAI 兼容 LLM 客户端
支持百炼、DeepSeek、OpenAI 等兼容 OpenAI API 的服务商
"""

import json
import logging
from typing import Optional

import httpx

from .base import LLMClient

logger = logging.getLogger(__name__)


class OpenAIClient(LLMClient):
    """OpenAI 兼容的 LLM 客户端"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: int = 60,
    ):
        """
        初始化客户端

        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

        # 确保 base_url 以 /chat/completions 结尾或我们手动添加
        if not self.base_url.endswith("/chat/completions"):
            # 移除可能存在的末尾斜杠后添加
            self.base_url = self.base_url.rstrip("/") + "/v1/chat/completions"

        logger.info(
            f"OpenAIClient 初始化：model={model}, base_url={self.base_url}"
        )

    def _call_api(
        self,
        messages: list[dict],
        temperature: float = 0.1,
        max_tokens: int = 1000,
        response_format: Optional[str] = None,
    ) -> str:
        """
        调用 LLM API

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            response_format: 响应格式（如 "json_object"）

        Returns:
            API 响应文本
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # 如果指定 JSON 格式，添加 response_format
        if response_format == "json_object":
            payload["response_format"] = {"type": "json_object"}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                # 提取响应内容
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    logger.debug(f"API 响应：{content[:200]}...")
                    return content.strip()
                else:
                    logger.error(f"API 响应格式异常：{data}")
                    raise ValueError(f"API 响应格式异常：{data}")

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 错误：{e.response.status_code} - {e.response.text}")
            raise RuntimeError(f"LLM API 请求失败：{e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"请求错误：{e}")
            raise RuntimeError(f"LLM API 连接失败：{str(e)}")
        except Exception as e:
            logger.error(f"未知错误：{e}")
            raise RuntimeError(f"LLM API 调用失败：{str(e)}")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> str:
        """生成文本响应"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        return self._call_api(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> dict:
        """生成 JSON 响应"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response_text = self._call_api(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format="json_object",
        )

        # 清理可能的 markdown 标记
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败：{e}, 原始响应：{response_text}")
            raise ValueError(f"LLM 返回的 JSON 格式无效：{str(e)}")
