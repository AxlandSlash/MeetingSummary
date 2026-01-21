"""会议服务层"""

from typing import Optional

from meet_conclusion.core.meeting_manager import MeetingManager, get_meeting_manager
from meet_conclusion.core.recording_engine import RecordingState
from meet_conclusion.db.models import Meeting
from meet_conclusion.db.repositories import MeetingRepository
from meet_conclusion.utils.logger import get_logger

logger = get_logger(__name__)


class MeetingService:
    """会议服务

    为 UI 层提供会议相关的业务逻辑
    """

    def __init__(self):
        self._manager = get_meeting_manager()

    def create_meeting(
        self,
        title: str,
        user_perspective: str = "worker",
        output_style: str = "neutral",
        custom_perspective: Optional[str] = None,
        participants: Optional[str] = None,
    ) -> Meeting:
        """创建会议"""
        return self._manager.create_meeting(
            title=title,
            user_perspective=user_perspective,
            output_style=output_style,
            custom_perspective=custom_perspective,
            participants=participants,
        )

    def get_meeting(self, meeting_id: int) -> Optional[Meeting]:
        """获取会议"""
        return MeetingRepository.get_by_id(meeting_id)

    def get_meetings(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> list[Meeting]:
        """获取会议列表"""
        return MeetingRepository.get_all(status=status, limit=limit)

    def update_meeting(self, meeting_id: int, **kwargs) -> Optional[Meeting]:
        """更新会议"""
        return MeetingRepository.update(meeting_id, **kwargs)

    def delete_meeting(self, meeting_id: int) -> bool:
        """删除会议"""
        return MeetingRepository.delete(meeting_id)

    def search_meetings(self, keyword: str) -> list[Meeting]:
        """搜索会议"""
        return MeetingRepository.search(keyword)

    def start_recording(self, meeting_id: int) -> bool:
        """开始录制"""
        return self._manager.start_recording(meeting_id)

    def stop_recording(self) -> float:
        """停止录制

        Returns:
            录制时长（秒）
        """
        return self._manager.stop_recording()

    def process_meeting(
        self,
        meeting_id: int,
        audio_urls: Optional[list[str]] = None,
    ) -> bool:
        """处理会议"""
        return self._manager.process_meeting(meeting_id, audio_urls)

    def get_recording_state(self) -> RecordingState:
        """获取录音状态"""
        return self._manager.get_recording_state()

    def get_elapsed_seconds(self) -> float:
        """获取已录制的秒数"""
        return self._manager.get_elapsed_seconds()

    def is_recording(self) -> bool:
        """是否正在录制"""
        return self._manager.is_recording()

    @property
    def current_meeting_id(self) -> Optional[int]:
        """当前会议ID"""
        return self._manager.current_meeting_id


# 全局服务实例
_meeting_service: Optional[MeetingService] = None


def get_meeting_service() -> MeetingService:
    """获取会议服务实例"""
    global _meeting_service
    if _meeting_service is None:
        _meeting_service = MeetingService()
    return _meeting_service
