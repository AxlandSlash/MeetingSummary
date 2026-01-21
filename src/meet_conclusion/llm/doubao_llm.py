"""豆包 LLM 实现

基于豆包大模型 API (兼容 OpenAI 格式) 的实现
"""

import json
from typing import Optional

import httpx

from meet_conclusion.config import get_config
from meet_conclusion.llm.base import LLMMessage, LLMProvider, LLMResponse
from meet_conclusion.utils.logger import get_logger

logger = get_logger(__name__)


class DoubaoLLMProvider(LLMProvider):
    """豆包 LLM 提供者"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """初始化

        Args:
            api_key: API 密钥，默认从配置读取
            api_base: API 基础 URL，默认从配置读取
            model: 模型名称，默认从配置读取
        """
        config = get_config()
        self.api_key = api_key or config.doubao_llm.api_key
        self.api_base = api_base or config.doubao_llm.api_base
        self.model = model or config.doubao_llm.model
        self.default_max_tokens = config.doubao_llm.max_tokens
        self.default_temperature = config.doubao_llm.temperature

        self._client = httpx.Client(timeout=120.0)

    @property
    def name(self) -> str:
        return "doubao"

    @property
    def max_context_length(self) -> int:
        # 根据模型不同有所区别
        if "32k" in self.model:
            return 32000
        elif "128k" in self.model:
            return 128000
        return 8000

    def _build_headers(self) -> dict:
        """构建请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat(
        self,
        messages: list[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """聊天接口"""
        url = f"{self.api_base}/chat/completions"

        request_body = {
            "model": self.model,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ],
            "temperature": temperature or self.default_temperature,
            "max_tokens": max_tokens or self.default_max_tokens,
        }

        logger.debug(f"发送 LLM 请求: model={self.model}")

        try:
            response = self._client.post(
                url,
                headers=self._build_headers(),
                content=json.dumps(request_body),
            )
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage")

            logger.debug(f"LLM 响应成功: {len(content)} 字符")

            return LLMResponse(
                content=content,
                usage=usage,
                model=data.get("model"),
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"LLM 请求失败: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"LLM 请求异常: {e}")
            raise

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """简单补全接口"""
        messages = []

        if system_prompt:
            messages.append(LLMMessage(role="system", content=system_prompt))

        messages.append(LLMMessage(role="user", content=prompt))

        response = self.chat(messages, temperature, max_tokens)
        return response.content

    def close(self):
        """关闭客户端"""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
