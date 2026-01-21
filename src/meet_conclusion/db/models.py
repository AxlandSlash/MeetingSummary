"""数据库模型定义

使用SQLModel定义数据库表结构
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class Meeting(SQLModel, table=True):
    """会议表"""

    __tablename__ = "meetings"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True, description="会议标题")
    status: str = Field(
        default="draft",
        description="会议状态: draft/recording/processing/done/failed"
    )
    user_perspective: str = Field(
        default="worker",
        description="用户视角: worker/manager/boss/custom"
    )
    custom_perspective: Optional[str] = Field(
        default=None, description="自定义视角描述"
    )
    output_style: str = Field(
        default="neutral",
        description="输出风格: sarcastic/neutral/comforting"
    )
    participants: Optional[str] = Field(default=None, description="参与人员")
    audio_path: Optional[str] = Field(default=None, description="音频文件路径")
    duration: Optional[float] = Field(default=None, description="会议时长(秒)")

    # 纪要内容
    summary: Optional[str] = Field(default=None, description="会议摘要")
    decisions_json: Optional[str] = Field(default=None, description="决策列表JSON")
    action_items_json: Optional[str] = Field(default=None, description="行动项JSON")
    topics_json: Optional[str] = Field(default=None, description="议题详情JSON")

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    started_at: Optional[datetime] = Field(default=None, description="开始录制时间")
    ended_at: Optional[datetime] = Field(default=None, description="结束录制时间")

    # 关联
    transcripts: list["Transcript"] = Relationship(back_populates="meeting")
    notes: list["Note"] = Relationship(back_populates="meeting")


class Transcript(SQLModel, table=True):
    """转写文本表"""

    __tablename__ = "transcripts"

    id: Optional[int] = Field(default=None, primary_key=True)
    meeting_id: int = Field(foreign_key="meetings.id", index=True)
    start_time: float = Field(description="开始时间(秒)")
    end_time: float = Field(description="结束时间(秒)")
    speaker_id: Optional[str] = Field(default=None, description="说话人标识")
    text: str = Field(description="转写文本")
    confidence: Optional[float] = Field(default=None, description="置信度")
    chunk_index: Optional[int] = Field(default=None, description="所属切片索引")

    # 关联
    meeting: Optional[Meeting] = Relationship(back_populates="transcripts")


class Note(SQLModel, table=True):
    """用户笔记表"""

    __tablename__ = "notes"

    id: Optional[int] = Field(default=None, primary_key=True)
    meeting_id: int = Field(foreign_key="meetings.id", index=True)
    time_offset: float = Field(description="时间偏移(秒)")
    content: str = Field(description="笔记内容")
    tag: str = Field(default="general", description="标签: todo/risk/question/general")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

    # 关联
    meeting: Optional[Meeting] = Relationship(back_populates="notes")


class AudioChunk(SQLModel, table=True):
    """音频切片表"""

    __tablename__ = "audio_chunks"

    id: Optional[int] = Field(default=None, primary_key=True)
    meeting_id: int = Field(foreign_key="meetings.id", index=True)
    chunk_index: int = Field(description="切片索引")
    file_path: str = Field(description="文件路径")
    start_time: float = Field(description="开始时间(秒)")
    end_time: float = Field(description="结束时间(秒)")
    status: str = Field(
        default="pending",
        description="处理状态: pending/transcribing/done/failed"
    )
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
