"""ASR Provider 抽象接口"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class TranscriptSegment:
    """转写片段"""

    start_time: float  # 开始时间（秒）
    end_time: float    # 结束时间（秒）
    text: str          # 转写文本
    speaker_id: Optional[str] = None  # 说话人ID
    confidence: Optional[float] = None  # 置信度


@dataclass
class TranscriptResult:
    """转写结果"""

    segments: list[TranscriptSegment]  # 转写片段列表
    full_text: str  # 完整文本
    duration: float  # 音频时长（秒）
    language: Optional[str] = None  # 语言


class ASRProvider(ABC):
    """ASR 服务提供者抽象基类"""

    @abstractmethod
    def transcribe(
        self,
        audio_path: Path,
        t_start: float = 0.0,
    ) -> TranscriptResult:
        """转写音频文件

        Args:
            audio_path: 音频文件路径
            t_start: 音频在整场会议中的起始时间（秒）

        Returns:
            转写结果
        """
        pass

    @abstractmethod
    def transcribe_url(
        self,
        audio_url: str,
        t_start: float = 0.0,
    ) -> TranscriptResult:
        """转写音频URL

        Args:
            audio_url: 音频URL
            t_start: 音频在整场会议中的起始时间（秒）

        Returns:
            转写结果
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """提供者名称"""
        pass

    @property
    @abstractmethod
    def supports_speaker_diarization(self) -> bool:
        """是否支持说话人分离"""
        pass
