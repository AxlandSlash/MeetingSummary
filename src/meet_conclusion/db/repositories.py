"""数据仓库模块 - CRUD操作"""

from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from meet_conclusion.db.database import session_scope
from meet_conclusion.db.models import AudioChunk, Meeting, Note, Transcript
from meet_conclusion.utils.logger import get_logger

logger = get_logger(__name__)


class MeetingRepository:
    """会议数据仓库"""

    @staticmethod
    def create(
        title: str,
        user_perspective: str = "worker",
        output_style: str = "neutral",
        custom_perspective: Optional[str] = None,
        participants: Optional[str] = None,
    ) -> Meeting:
        """创建会议"""
        with session_scope() as session:
            meeting = Meeting(
                title=title,
                user_perspective=user_perspective,
                output_style=output_style,
                custom_perspective=custom_perspective,
                participants=participants,
            )
            session.add(meeting)
            session.commit()
            session.refresh(meeting)
            logger.info(f"创建会议: {meeting.id} - {title}")
            return meeting

    @staticmethod
    def get_by_id(meeting_id: int) -> Optional[Meeting]:
        """根据ID获取会议"""
        with session_scope() as session:
            meeting = session.get(Meeting, meeting_id)
            return meeting

    @staticmethod
    def get_all(
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[Meeting]:
        """获取会议列表"""
        with session_scope() as session:
            query = select(Meeting).order_by(Meeting.created_at.desc())
            if status:
                query = query.where(Meeting.status == status)
            query = query.offset(offset).limit(limit)
            meetings = session.exec(query).all()
            return list(meetings)

    @staticmethod
    def update(meeting_id: int, **kwargs) -> Optional[Meeting]:
        """更新会议"""
        with session_scope() as session:
            meeting = session.get(Meeting, meeting_id)
            if meeting:
                for key, value in kwargs.items():
                    if hasattr(meeting, key):
                        setattr(meeting, key, value)
                meeting.updated_at = datetime.now()
                session.add(meeting)
                session.commit()
                session.refresh(meeting)
                logger.info(f"更新会议: {meeting_id}")
            return meeting

    @staticmethod
    def update_status(meeting_id: int, status: str) -> Optional[Meeting]:
        """更新会议状态"""
        return MeetingRepository.update(meeting_id, status=status)

    @staticmethod
    def start_recording(meeting_id: int, audio_path: str) -> Optional[Meeting]:
        """开始录制"""
        return MeetingRepository.update(
            meeting_id,
            status="recording",
            audio_path=audio_path,
            started_at=datetime.now()
        )

    @staticmethod
    def stop_recording(meeting_id: int, duration: float) -> Optional[Meeting]:
        """停止录制"""
        return MeetingRepository.update(
            meeting_id,
            status="processing",
            duration=duration,
            ended_at=datetime.now()
        )

    @staticmethod
    def save_minutes(
        meeting_id: int,
        summary: str,
        decisions_json: str,
        action_items_json: str,
        topics_json: str
    ) -> Optional[Meeting]:
        """保存会议纪要"""
        return MeetingRepository.update(
            meeting_id,
            status="done",
            summary=summary,
            decisions_json=decisions_json,
            action_items_json=action_items_json,
            topics_json=topics_json
        )

    @staticmethod
    def delete(meeting_id: int) -> bool:
        """删除会议"""
        with session_scope() as session:
            meeting = session.get(Meeting, meeting_id)
            if meeting:
                session.delete(meeting)
                session.commit()
                logger.info(f"删除会议: {meeting_id}")
                return True
            return False

    @staticmethod
    def search(keyword: str, limit: int = 50) -> list[Meeting]:
        """搜索会议"""
        with session_scope() as session:
            query = (
                select(Meeting)
                .where(
                    Meeting.title.contains(keyword)
                    | Meeting.participants.contains(keyword)
                )
                .order_by(Meeting.created_at.desc())
                .limit(limit)
            )
            meetings = session.exec(query).all()
            return list(meetings)


class TranscriptRepository:
    """转写文本数据仓库"""

    @staticmethod
    def create(
        meeting_id: int,
        start_time: float,
        end_time: float,
        text: str,
        speaker_id: Optional[str] = None,
        confidence: Optional[float] = None,
        chunk_index: Optional[int] = None,
    ) -> Transcript:
        """创建转写记录"""
        with session_scope() as session:
            transcript = Transcript(
                meeting_id=meeting_id,
                start_time=start_time,
                end_time=end_time,
                text=text,
                speaker_id=speaker_id,
                confidence=confidence,
                chunk_index=chunk_index,
            )
            session.add(transcript)
            session.commit()
            session.refresh(transcript)
            return transcript

    @staticmethod
    def create_batch(transcripts: list[dict]) -> list[Transcript]:
        """批量创建转写记录"""
        with session_scope() as session:
            result = []
            for data in transcripts:
                transcript = Transcript(**data)
                session.add(transcript)
                result.append(transcript)
            session.commit()
            for t in result:
                session.refresh(t)
            logger.info(f"批量创建转写记录: {len(result)} 条")
            return result

    @staticmethod
    def get_by_meeting(
        meeting_id: int,
        speaker_id: Optional[str] = None
    ) -> list[Transcript]:
        """获取会议的所有转写记录"""
        with session_scope() as session:
            query = (
                select(Transcript)
                .where(Transcript.meeting_id == meeting_id)
                .order_by(Transcript.start_time)
            )
            if speaker_id:
                query = query.where(Transcript.speaker_id == speaker_id)
            transcripts = session.exec(query).all()
            return list(transcripts)

    @staticmethod
    def delete_by_meeting(meeting_id: int) -> int:
        """删除会议的所有转写记录"""
        with session_scope() as session:
            query = select(Transcript).where(Transcript.meeting_id == meeting_id)
            transcripts = session.exec(query).all()
            count = len(transcripts)
            for t in transcripts:
                session.delete(t)
            session.commit()
            logger.info(f"删除会议 {meeting_id} 的转写记录: {count} 条")
            return count


class NoteRepository:
    """用户笔记数据仓库"""

    @staticmethod
    def create(
        meeting_id: int,
        time_offset: float,
        content: str,
        tag: str = "general"
    ) -> Note:
        """创建笔记"""
        with session_scope() as session:
            note = Note(
                meeting_id=meeting_id,
                time_offset=time_offset,
                content=content,
                tag=tag,
            )
            session.add(note)
            session.commit()
            session.refresh(note)
            logger.info(f"创建笔记: 会议{meeting_id}, 时间{time_offset}s")
            return note

    @staticmethod
    def get_by_meeting(meeting_id: int, tag: Optional[str] = None) -> list[Note]:
        """获取会议的所有笔记"""
        with session_scope() as session:
            query = (
                select(Note)
                .where(Note.meeting_id == meeting_id)
                .order_by(Note.time_offset)
            )
            if tag:
                query = query.where(Note.tag == tag)
            notes = session.exec(query).all()
            return list(notes)

    @staticmethod
    def update(note_id: int, content: str, tag: Optional[str] = None) -> Optional[Note]:
        """更新笔记"""
        with session_scope() as session:
            note = session.get(Note, note_id)
            if note:
                note.content = content
                if tag:
                    note.tag = tag
                session.add(note)
                session.commit()
                session.refresh(note)
            return note

    @staticmethod
    def delete(note_id: int) -> bool:
        """删除笔记"""
        with session_scope() as session:
            note = session.get(Note, note_id)
            if note:
                session.delete(note)
                session.commit()
                return True
            return False

    @staticmethod
    def delete_by_meeting(meeting_id: int) -> int:
        """删除会议的所有笔记"""
        with session_scope() as session:
            query = select(Note).where(Note.meeting_id == meeting_id)
            notes = session.exec(query).all()
            count = len(notes)
            for n in notes:
                session.delete(n)
            session.commit()
            logger.info(f"删除会议 {meeting_id} 的笔记: {count} 条")
            return count


class AudioChunkRepository:
    """音频切片数据仓库"""

    @staticmethod
    def create(
        meeting_id: int,
        chunk_index: int,
        file_path: str,
        start_time: float,
        end_time: float,
    ) -> AudioChunk:
        """创建音频切片记录"""
        with session_scope() as session:
            chunk = AudioChunk(
                meeting_id=meeting_id,
                chunk_index=chunk_index,
                file_path=file_path,
                start_time=start_time,
                end_time=end_time,
            )
            session.add(chunk)
            session.commit()
            session.refresh(chunk)
            return chunk

    @staticmethod
    def get_by_meeting(meeting_id: int) -> list[AudioChunk]:
        """获取会议的所有音频切片"""
        with session_scope() as session:
            query = (
                select(AudioChunk)
                .where(AudioChunk.meeting_id == meeting_id)
                .order_by(AudioChunk.chunk_index)
            )
            chunks = session.exec(query).all()
            return list(chunks)

    @staticmethod
    def get_pending(meeting_id: int) -> list[AudioChunk]:
        """获取待处理的音频切片"""
        with session_scope() as session:
            query = (
                select(AudioChunk)
                .where(
                    AudioChunk.meeting_id == meeting_id,
                    AudioChunk.status == "pending"
                )
                .order_by(AudioChunk.chunk_index)
            )
            chunks = session.exec(query).all()
            return list(chunks)

    @staticmethod
    def update_status(chunk_id: int, status: str) -> Optional[AudioChunk]:
        """更新切片状态"""
        with session_scope() as session:
            chunk = session.get(AudioChunk, chunk_id)
            if chunk:
                chunk.status = status
                session.add(chunk)
                session.commit()
                session.refresh(chunk)
            return chunk

    @staticmethod
    def delete_by_meeting(meeting_id: int) -> int:
        """删除会议的所有音频切片记录"""
        with session_scope() as session:
            query = select(AudioChunk).where(AudioChunk.meeting_id == meeting_id)
            chunks = session.exec(query).all()
            count = len(chunks)
            for c in chunks:
                session.delete(c)
            session.commit()
            logger.info(f"删除会议 {meeting_id} 的音频切片记录: {count} 条")
            return count
