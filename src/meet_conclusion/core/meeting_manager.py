"""会议生命周期管理"""

import threading
from typing import Callable, Optional

from meet_conclusion.audio.chunk_writer import ChunkInfo
from meet_conclusion.core.pipeline import MeetingPipeline, PipelineState
from meet_conclusion.core.recording_engine import RecordingEngine, RecordingState
from meet_conclusion.db.models import Meeting
from meet_conclusion.db.repositories import MeetingRepository
from meet_conclusion.utils.logger import get_logger

logger = get_logger(__name__)


class MeetingManager:
    """会议管理器

    协调录音引擎和处理流水线，管理会议的完整生命周期
    """

    _instance: Optional["MeetingManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        """单例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._recording_engine = RecordingEngine()
        self._pipeline = MeetingPipeline()

        # 回调
        self._on_recording_state_changed: Optional[Callable[[RecordingState], None]] = None
        self._on_pipeline_state_changed: Optional[Callable[[PipelineState, str], None]] = None
        self._on_chunk_ready: Optional[Callable[[ChunkInfo], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None

        # 设置内部回调
        self._recording_engine.set_callbacks(
            on_state_changed=self._handle_recording_state,
            on_chunk_ready=self._handle_chunk_ready,
            on_error=self._handle_error,
        )

        self._initialized = True

    def set_callbacks(
        self,
        on_recording_state_changed: Optional[Callable[[RecordingState], None]] = None,
        on_pipeline_state_changed: Optional[Callable[[PipelineState, str], None]] = None,
        on_chunk_ready: Optional[Callable[[ChunkInfo], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        """设置回调函数"""
        self._on_recording_state_changed = on_recording_state_changed
        self._on_pipeline_state_changed = on_pipeline_state_changed
        self._on_chunk_ready = on_chunk_ready
        self._on_error = on_error

    def _handle_recording_state(self, state: RecordingState) -> None:
        """处理录音状态变更"""
        if self._on_recording_state_changed:
            self._on_recording_state_changed(state)

    def _handle_chunk_ready(self, chunk_info: ChunkInfo) -> None:
        """处理切片就绪"""
        if self._on_chunk_ready:
            self._on_chunk_ready(chunk_info)

    def _handle_error(self, error: str) -> None:
        """处理错误"""
        if self._on_error:
            self._on_error(error)

    def create_meeting(
        self,
        title: str,
        user_perspective: str = "worker",
        output_style: str = "neutral",
        custom_perspective: Optional[str] = None,
        participants: Optional[str] = None,
    ) -> Meeting:
        """创建会议

        Args:
            title: 会议标题
            user_perspective: 用户视角
            output_style: 输出风格
            custom_perspective: 自定义视角描述
            participants: 参与人

        Returns:
            创建的会议对象
        """
        meeting = MeetingRepository.create(
            title=title,
            user_perspective=user_perspective,
            output_style=output_style,
            custom_perspective=custom_perspective,
            participants=participants,
        )
        logger.info(f"创建会议: {meeting.id} - {title}")
        return meeting

    def start_recording(self, meeting_id: int) -> bool:
        """开始录制

        Args:
            meeting_id: 会议ID

        Returns:
            是否成功
        """
        return self._recording_engine.start(meeting_id)

    def stop_recording(self) -> float:
        """停止录制

        Returns:
            录制时长（秒）
        """
        return self._recording_engine.stop()

    def process_meeting(
        self,
        meeting_id: int,
        audio_urls: Optional[list[str]] = None,
        async_mode: bool = True,
    ) -> bool:
        """处理会议

        Args:
            meeting_id: 会议ID
            audio_urls: 音频URL列表
            async_mode: 是否异步处理

        Returns:
            是否成功启动
        """
        if async_mode:
            self._pipeline.process_async(meeting_id, audio_urls)
            return True
        else:
            return self._pipeline.process(meeting_id, audio_urls)

    def get_recording_state(self) -> RecordingState:
        """获取录音状态"""
        return self._recording_engine.state

    def get_pipeline_state(self) -> PipelineState:
        """获取流水线状态"""
        return self._pipeline.state

    def get_elapsed_seconds(self) -> float:
        """获取已录制的秒数"""
        return self._recording_engine.get_elapsed_seconds()

    def is_recording(self) -> bool:
        """是否正在录制"""
        return self._recording_engine.is_recording

    @property
    def current_meeting_id(self) -> Optional[int]:
        """当前会议ID"""
        return self._recording_engine.meeting_id


def get_meeting_manager() -> MeetingManager:
    """获取会议管理器实例"""
    return MeetingManager()
