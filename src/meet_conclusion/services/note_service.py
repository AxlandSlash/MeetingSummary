"""笔记服务层"""

from typing import Optional

from meet_conclusion.db.models import Note
from meet_conclusion.db.repositories import NoteRepository
from meet_conclusion.utils.logger import get_logger

logger = get_logger(__name__)


class NoteService:
    """笔记服务"""

    def create_note(
        self,
        meeting_id: int,
        time_offset: float,
        content: str,
        tag: str = "general",
    ) -> Note:
        """创建笔记"""
        return NoteRepository.create(
            meeting_id=meeting_id,
            time_offset=time_offset,
            content=content,
            tag=tag,
        )

    def get_notes_by_meeting(
        self,
        meeting_id: int,
        tag: Optional[str] = None
    ) -> list[Note]:
        """获取会议的笔记"""
        return NoteRepository.get_by_meeting(meeting_id, tag)

    def update_note(
        self,
        note_id: int,
        content: str,
        tag: Optional[str] = None
    ) -> Optional[Note]:
        """更新笔记"""
        return NoteRepository.update(note_id, content, tag)

    def delete_note(self, note_id: int) -> bool:
        """删除笔记"""
        return NoteRepository.delete(note_id)

    def delete_notes_by_meeting(self, meeting_id: int) -> int:
        """删除会议的所有笔记"""
        return NoteRepository.delete_by_meeting(meeting_id)


# 全局服务实例
_note_service: Optional[NoteService] = None


def get_note_service() -> NoteService:
    """获取笔记服务实例"""
    global _note_service
    if _note_service is None:
        _note_service = NoteService()
    return _note_service
