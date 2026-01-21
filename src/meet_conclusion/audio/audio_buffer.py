"""音频缓冲区管理模块"""

import threading
from collections import deque
from typing import Optional

from meet_conclusion.utils.logger import get_logger

logger = get_logger(__name__)


class AudioBuffer:
    """线程安全的音频缓冲区"""

    def __init__(self, max_seconds: float = 120.0, sample_rate: int = 16000, channels: int = 1):
        """初始化缓冲区

        Args:
            max_seconds: 最大缓冲时长（秒）
            sample_rate: 采样率
            channels: 声道数
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.bytes_per_sample = 2  # 16-bit

        # 每秒的字节数
        self.bytes_per_second = sample_rate * channels * self.bytes_per_sample

        # 最大字节数
        self.max_bytes = int(max_seconds * self.bytes_per_second)

        # 使用 deque 存储数据块
        self._buffer: deque[bytes] = deque()
        self._total_bytes = 0
        self._lock = threading.Lock()

        # 累计接收的总字节数（不会被清除影响）
        self._total_received_bytes = 0

    def write(self, data: bytes) -> None:
        """写入数据

        Args:
            data: 音频数据
        """
        with self._lock:
            self._buffer.append(data)
            self._total_bytes += len(data)
            self._total_received_bytes += len(data)

            # 如果超过最大容量，移除旧数据
            while self._total_bytes > self.max_bytes and self._buffer:
                old_data = self._buffer.popleft()
                self._total_bytes -= len(old_data)

    def read(self, num_bytes: Optional[int] = None) -> bytes:
        """读取数据

        Args:
            num_bytes: 要读取的字节数，None 表示读取全部

        Returns:
            音频数据
        """
        with self._lock:
            if not self._buffer:
                return b""

            if num_bytes is None:
                # 读取全部
                data = b"".join(self._buffer)
                self._buffer.clear()
                self._total_bytes = 0
                return data

            # 读取指定字节数
            result = []
            remaining = num_bytes

            while remaining > 0 and self._buffer:
                chunk = self._buffer[0]
                if len(chunk) <= remaining:
                    result.append(chunk)
                    remaining -= len(chunk)
                    self._buffer.popleft()
                    self._total_bytes -= len(chunk)
                else:
                    # 部分读取
                    result.append(chunk[:remaining])
                    self._buffer[0] = chunk[remaining:]
                    self._total_bytes -= remaining
                    remaining = 0

            return b"".join(result)

    def peek(self, num_bytes: Optional[int] = None) -> bytes:
        """查看数据（不移除）

        Args:
            num_bytes: 要查看的字节数，None 表示查看全部

        Returns:
            音频数据
        """
        with self._lock:
            if not self._buffer:
                return b""

            data = b"".join(self._buffer)
            if num_bytes is None:
                return data
            return data[:num_bytes]

    def read_seconds(self, seconds: float) -> bytes:
        """读取指定时长的数据

        Args:
            seconds: 时长（秒）

        Returns:
            音频数据
        """
        num_bytes = int(seconds * self.bytes_per_second)
        return self.read(num_bytes)

    def available_bytes(self) -> int:
        """获取可用字节数"""
        with self._lock:
            return self._total_bytes

    def available_seconds(self) -> float:
        """获取可用时长（秒）"""
        return self.available_bytes() / self.bytes_per_second

    def total_received_seconds(self) -> float:
        """获取累计接收的总时长（秒）"""
        with self._lock:
            return self._total_received_bytes / self.bytes_per_second

    def clear(self) -> None:
        """清空缓冲区"""
        with self._lock:
            self._buffer.clear()
            self._total_bytes = 0

    def reset(self) -> None:
        """完全重置缓冲区"""
        with self._lock:
            self._buffer.clear()
            self._total_bytes = 0
            self._total_received_bytes = 0
