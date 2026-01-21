"""LLM Provider 抽象接口"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMMessage:
    """LLM 消息"""
    role: str  # system, user, assistant
    content: str


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    usage: Optional[dict] = None  # token 使用情况
    model: Optional[str] = None


class LLMProvider(ABC):
    """LLM 服务提供者抽象基类"""

    @abstractmethod
    def chat(
        self,
        messages: list[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """聊天接口

        Args:
            messages: 消息列表
            temperature: 生成温度
            max_tokens: 最大输出 token 数

        Returns:
            LLM 响应
        """
        pass

    @abstractmethod
    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """简单补全接口

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            temperature: 生成温度
            max_tokens: 最大输出 token 数

        Returns:
            生成的文本
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """提供者名称"""
        pass

    @property
    @abstractmethod
    def max_context_length(self) -> int:
        """最大上下文长度"""
        pass
