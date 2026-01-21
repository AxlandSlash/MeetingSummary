"""音频切片写入模块

将音频数据按固定时长切片并保存为 WAV 文件
"""

import wave
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from meet_conclusion.audio.audio_buffer import AudioBuffer
from meet_conclusion.config import get_config
from meet_conclusion.utils.logger import get_logger

logger = get_logger(__name__)


class ChunkInfo:
    """切片信息"""

    def __init__(
        self,
        index: int,
        file_path: Path,
        start_time: float,
        end_time: float,
        start_datetime: datetime,
    ):
        self.index = index
        self.file_path = file_path
        self.start_time = start_time  # 相对于录制开始的秒数
        self.end_time = end_time
        self.start_datetime = start_datetime  # 绝对时间
        self.duration = end_time - start_time


class ChunkWriter:
    """音频切片写入器"""

    def __init__(
        self,
        meeting_id: int,
        sample_rate: int = None,
        channels: int = None,
        chunk_duration: float = None,
        overlap_duration: float = None,
        on_chunk_ready: Optional[Callable[[ChunkInfo], None]] = None,
    ):
        """初始化切片写入器

        Args:
            meeting_id: 会议ID
            sample_rate: 采样率
            channels: 声道数
            chunk_duration: 切片时长（秒）
            overlap_duration: 重叠时长（秒）
            on_chunk_ready: 切片就绪回调
        """
        config = get_config()
        self.meeting_id = meeting_id
        self.sample_rate = sample_rate or config.audio.sample_rate
        self.channels = channels or config.audio.channels
        self.chunk_duration = chunk_duration or config.audio.chunk_duration
        self.overlap_duration = overlap_duration or config.audio.overlap_duration

        self.on_chunk_ready = on_chunk_ready

        # 创建会议专用目录
        self.output_dir = config.chunks_dir / str(meeting_id)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 缓冲区
        self._buffer = AudioBuffer(
            max_seconds=self.chunk_duration * 2,
            sample_rate=self.sample_rate,
            channels=self.channels,
        )

        # 状态
        self._chunk_index = 0
        self._start_datetime: Optional[datetime] = None
        self._is_running = False
        self._lock = threading.Lock()

        # 重叠缓冲（保存上一个切片末尾的数据）
        self._overlap_data: bytes = b""

        # 字节相关计算
        self.bytes_per_second = self.sample_rate * self.channels * 2  # 16-bit

    def start(self) -> None:
        """开始切片"""
        with self._lock:
            self._is_running = True
            self._start_datetime = datetime.now()
            self._chunk_index = 0
            self._overlap_data = b""
            self._buffer.reset()
            logger.info(f"切片写入器已启动，会议ID: {self.meeting_id}")

    def write(self, data: bytes) -> None:
        """写入音频数据

        Args:
            data: 音频数据
        """
        if not self._is_running:
            return

        self._buffer.write(data)

        # 检查是否达到切片时长
        if self._buffer.available_seconds() >= self.chunk_duration:
            self._save_chunk()

    def _save_chunk(self) -> None:
        """保存当前切片"""
        with self._lock:
            if not self._is_running:
                return

            # 读取一个切片时长的数据
            chunk_bytes = int(self.chunk_duration * self.bytes_per_second)
            data = self._buffer.read(chunk_bytes)

            if not data:
                return

            # 在数据前加上重叠部分
            if self._overlap_data:
                data = self._overlap_data + data

            # 保存重叠数据
            overlap_bytes = int(self.overlap_duration * self.bytes_per_second)
            if len(data) > overlap_bytes:
                self._overlap_data = data[-overlap_bytes:]
            else:
                self._overlap_data = data

            # 计算时间
            start_time = self._chunk_index * self.chunk_duration
            if self._chunk_index > 0:
                start_time -= self.overlap_duration  # 考虑重叠

            end_time = start_time + len(data) / self.bytes_per_second

            # 生成文件名
            file_path = self.output_dir / f"chunk_{self._chunk_index:04d}.wav"

            # 保存 WAV 文件
            self._save_wav(file_path, data)

            # 创建切片信息
            chunk_info = ChunkInfo(
                index=self._chunk_index,
                file_path=file_path,
                start_time=max(0, start_time),
                end_time=end_time,
                start_datetime=self._start_datetime,
            )

            logger.info(f"保存切片 {self._chunk_index}: {file_path.name}, "
                       f"时长: {chunk_info.duration:.1f}s")

            self._chunk_index += 1

            # 触发回调
            if self.on_chunk_ready:
                try:
                    self.on_chunk_ready(chunk_info)
                except Exception as e:
                    logger.error(f"切片回调执行失败: {e}")

    def _save_wav(self, file_path: Path, data: bytes) -> None:
        """保存 WAV 文件

        Args:
            file_path: 文件路径
            data: 音频数据
        """
        try:
            with wave.open(str(file_path), "wb") as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.sample_rate)
                wf.writeframes(data)
        except Exception as e:
            logger.error(f"保存 WAV 文件失败: {e}")
            raise

    def stop(self) -> Optional[ChunkInfo]:
        """停止切片并保存剩余数据

        Returns:
            最后一个切片信息，如果没有剩余数据则返回 None
        """
        with self._lock:
            if not self._is_running:
                return None

            self._is_running = False

            # 保存剩余数据
            remaining_data = self._buffer.read()
            if remaining_data:
                # 加上重叠数据
                if self._overlap_data:
                    remaining_data = self._overlap_data + remaining_data

                start_time = self._chunk_index * self.chunk_duration
                if self._chunk_index > 0:
                    start_time -= self.overlap_duration

                end_time = start_time + len(remaining_data) / self.bytes_per_second

                file_path = self.output_dir / f"chunk_{self._chunk_index:04d}.wav"
                self._save_wav(file_path, remaining_data)

                chunk_info = ChunkInfo(
                    index=self._chunk_index,
                    file_path=file_path,
                    start_time=max(0, start_time),
                    end_time=end_time,
                    start_datetime=self._start_datetime,
                )

                logger.info(f"保存最后切片 {self._chunk_index}: {file_path.name}, "
                           f"时长: {chunk_info.duration:.1f}s")

                if self.on_chunk_ready:
                    try:
                        self.on_chunk_ready(chunk_info)
                    except Exception as e:
                        logger.error(f"切片回调执行失败: {e}")

                return chunk_info

            logger.info("切片写入器已停止")
            return None

    def get_chunk_count(self) -> int:
        """获取已生成的切片数"""
        return self._chunk_index

    def get_total_duration(self) -> float:
        """获取已录制的总时长（秒）"""
        return self._buffer.total_received_seconds()

    def get_output_dir(self) -> Path:
        """获取输出目录"""
        return self.output_dir
