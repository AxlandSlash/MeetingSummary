"""录音状态机模块

管理录音的完整生命周期：开始 -> 录制中 -> 停止 -> 处理
"""

import threading
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Optional

from meet_conclusion.audio.chunk_writer import ChunkInfo, ChunkWriter
from meet_conclusion.audio.wasapi_capture import WASAPICapture
from meet_conclusion.config import get_config
from meet_conclusion.db.repositories import AudioChunkRepository, MeetingRepository
from meet_conclusion.utils.logger import get_logger

logger = get_logger(__name__)


class RecordingState(Enum):
    """录音状态"""
    IDLE = auto()       # 空闲
    STARTING = auto()   # 正在启动
    RECORDING = auto()  # 录制中
    STOPPING = auto()   # 正在停止
    STOPPED = auto()    # 已停止


class RecordingEngine:
    """录音引擎

    管理 WASAPI 音频采集和切片写入的完整流程
    """

    def __init__(self):
        self.config = get_config()
        self._state = RecordingState.IDLE
        self._lock = threading.Lock()

        # 组件
        self._capture: Optional[WASAPICapture] = None
        self._chunk_writer: Optional[ChunkWriter] = None

        # 当前会议
        self._meeting_id: Optional[int] = None
        self._start_time: Optional[datetime] = None

        # 回调
        self._on_state_changed: Optional[Callable[[RecordingState], None]] = None
        self._on_chunk_ready: Optional[Callable[[ChunkInfo], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None

    @property
    def state(self) -> RecordingState:
        """获取当前状态"""
        return self._state

    @property
    def is_recording(self) -> bool:
        """是否正在录制"""
        return self._state == RecordingState.RECORDING

    @property
    def meeting_id(self) -> Optional[int]:
        """获取当前会议ID"""
        return self._meeting_id

    def set_callbacks(
        self,
        on_state_changed: Optional[Callable[[RecordingState], None]] = None,
        on_chunk_ready: Optional[Callable[[ChunkInfo], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        """设置回调函数"""
        self._on_state_changed = on_state_changed
        self._on_chunk_ready = on_chunk_ready
        self._on_error = on_error

    def _set_state(self, new_state: RecordingState) -> None:
        """设置状态并触发回调"""
        old_state = self._state
        self._state = new_state
        logger.info(f"录音状态变更: {old_state.name} -> {new_state.name}")

        if self._on_state_changed:
            try:
                self._on_state_changed(new_state)
            except Exception as e:
                logger.error(f"状态变更回调执行失败: {e}")

    def _handle_chunk_ready(self, chunk_info: ChunkInfo) -> None:
        """处理切片就绪事件"""
        if self._meeting_id:
            # 保存到数据库
            AudioChunkRepository.create(
                meeting_id=self._meeting_id,
                chunk_index=chunk_info.index,
                file_path=str(chunk_info.file_path),
                start_time=chunk_info.start_time,
                end_time=chunk_info.end_time,
            )

        # 触发外部回调
        if self._on_chunk_ready:
            try:
                self._on_chunk_ready(chunk_info)
            except Exception as e:
                logger.error(f"切片就绪回调执行失败: {e}")

    def _handle_audio_data(self, data: bytes) -> None:
        """处理音频数据"""
        if self._chunk_writer and self._state == RecordingState.RECORDING:
            self._chunk_writer.write(data)

    def start(self, meeting_id: int) -> bool:
        """开始录音

        Args:
            meeting_id: 会议ID

        Returns:
            是否成功启动
        """
        with self._lock:
            if self._state != RecordingState.IDLE:
                logger.warning(f"无法启动录音，当前状态: {self._state.name}")
                return False

            self._set_state(RecordingState.STARTING)
            self._meeting_id = meeting_id

        try:
            # 创建切片写入器
            self._chunk_writer = ChunkWriter(
                meeting_id=meeting_id,
                on_chunk_ready=self._handle_chunk_ready,
            )
            self._chunk_writer.start()

            # 创建音频采集器
            self._capture = WASAPICapture(on_data=self._handle_audio_data)

            # 启动采集
            if not self._capture.start():
                raise RuntimeError("无法启动音频采集")

            self._start_time = datetime.now()

            # 更新会议状态
            audio_path = str(self._chunk_writer.get_output_dir())
            MeetingRepository.start_recording(meeting_id, audio_path)

            with self._lock:
                self._set_state(RecordingState.RECORDING)

            logger.info(f"录音已启动，会议ID: {meeting_id}")
            return True

        except Exception as e:
            logger.error(f"启动录音失败: {e}")
            self._cleanup()

            with self._lock:
                self._set_state(RecordingState.IDLE)

            if self._on_error:
                self._on_error(str(e))

            return False

    def stop(self) -> float:
        """停止录音

        Returns:
            录制时长（秒）
        """
        with self._lock:
            if self._state != RecordingState.RECORDING:
                logger.warning(f"无法停止录音，当前状态: {self._state.name}")
                return 0.0

            self._set_state(RecordingState.STOPPING)

        duration = 0.0

        try:
            # 停止采集
            if self._capture:
                self._capture.stop()

            # 停止切片写入
            if self._chunk_writer:
                self._chunk_writer.stop()
                duration = self._chunk_writer.get_total_duration()

            # 更新会议状态
            if self._meeting_id:
                MeetingRepository.stop_recording(self._meeting_id, duration)

            logger.info(f"录音已停止，时长: {duration:.1f}秒")

        except Exception as e:
            logger.error(f"停止录音时出错: {e}")
            if self._on_error:
                self._on_error(str(e))

        finally:
            self._cleanup()
            with self._lock:
                self._set_state(RecordingState.STOPPED)

        return duration

    def _cleanup(self) -> None:
        """清理资源"""
        if self._capture:
            try:
                self._capture.stop()
            except Exception:
                pass
            self._capture = None

        self._chunk_writer = None

    def reset(self) -> None:
        """重置状态"""
        with self._lock:
            if self._state == RecordingState.RECORDING:
                logger.warning("录音正在进行中，请先停止")
                return

            self._cleanup()
            self._meeting_id = None
            self._start_time = None
            self._set_state(RecordingState.IDLE)

    def get_elapsed_seconds(self) -> float:
        """获取已录制的秒数"""
        if self._start_time and self._state == RecordingState.RECORDING:
            return (datetime.now() - self._start_time).total_seconds()
        elif self._chunk_writer:
            return self._chunk_writer.get_total_duration()
        return 0.0

    def get_chunk_count(self) -> int:
        """获取已生成的切片数"""
        if self._chunk_writer:
            return self._chunk_writer.get_chunk_count()
        return 0
