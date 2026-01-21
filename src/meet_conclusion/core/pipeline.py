"""会议处理流水线

完整的会议处理流程：ASR转写 -> 结果合并 -> 纪要生成
"""

import json
import threading
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Optional

from meet_conclusion.asr.base import TranscriptResult
from meet_conclusion.asr.doubao_asr import DoubaoASRProvider
from meet_conclusion.asr.transcript_merger import TranscriptMerger
from meet_conclusion.db.models import Meeting
from meet_conclusion.db.repositories import (
    AudioChunkRepository,
    MeetingRepository,
    NoteRepository,
    TranscriptRepository,
)
from meet_conclusion.llm.minutes_generator import MinutesGenerator
from meet_conclusion.utils.logger import get_logger

logger = get_logger(__name__)


class PipelineState(Enum):
    """流水线状态"""
    IDLE = auto()
    TRANSCRIBING = auto()
    MERGING = auto()
    GENERATING = auto()
    DONE = auto()
    FAILED = auto()


class MeetingPipeline:
    """会议处理流水线"""

    def __init__(
        self,
        on_state_changed: Optional[Callable[[PipelineState, str], None]] = None,
        on_progress: Optional[Callable[[float, str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        """初始化

        Args:
            on_state_changed: 状态变更回调 (state, message)
            on_progress: 进度回调 (progress 0-1, message)
            on_error: 错误回调 (error_message)
        """
        self._state = PipelineState.IDLE
        self._on_state_changed = on_state_changed
        self._on_progress = on_progress
        self._on_error = on_error

        self._lock = threading.Lock()
        self._current_meeting_id: Optional[int] = None

    @property
    def state(self) -> PipelineState:
        """获取当前状态"""
        return self._state

    def _set_state(self, state: PipelineState, message: str = "") -> None:
        """设置状态"""
        self._state = state
        logger.info(f"流水线状态: {state.name} - {message}")
        if self._on_state_changed:
            try:
                self._on_state_changed(state, message)
            except Exception as e:
                logger.error(f"状态回调执行失败: {e}")

    def _report_progress(self, progress: float, message: str) -> None:
        """报告进度"""
        if self._on_progress:
            try:
                self._on_progress(progress, message)
            except Exception as e:
                logger.error(f"进度回调执行失败: {e}")

    def _report_error(self, error: str) -> None:
        """报告错误"""
        logger.error(f"流水线错误: {error}")
        if self._on_error:
            try:
                self._on_error(error)
            except Exception as e:
                logger.error(f"错误回调执行失败: {e}")

    def process(self, meeting_id: int, audio_urls: Optional[list[str]] = None) -> bool:
        """处理会议

        Args:
            meeting_id: 会议ID
            audio_urls: 音频URL列表（如果不提供，将从数据库读取切片信息）

        Returns:
            是否成功
        """
        with self._lock:
            if self._state not in (PipelineState.IDLE, PipelineState.DONE, PipelineState.FAILED):
                logger.warning(f"流水线正在处理中，当前状态: {self._state.name}")
                return False

            self._current_meeting_id = meeting_id

        try:
            # 获取会议信息
            meeting = MeetingRepository.get_by_id(meeting_id)
            if not meeting:
                raise ValueError(f"会议不存在: {meeting_id}")

            logger.info(f"开始处理会议: {meeting_id} - {meeting.title}")

            # 更新状态为处理中
            MeetingRepository.update_status(meeting_id, "processing")

            # 1. ASR 转写
            self._set_state(PipelineState.TRANSCRIBING, "正在进行语音识别...")
            transcript_result = self._transcribe(meeting_id, audio_urls)

            # 2. 保存转写结果
            self._set_state(PipelineState.MERGING, "正在合并转写结果...")
            self._save_transcripts(meeting_id, transcript_result)

            # 3. 生成纪要
            self._set_state(PipelineState.GENERATING, "正在生成会议纪要...")
            self._generate_minutes(meeting_id, transcript_result)

            # 4. 完成
            self._set_state(PipelineState.DONE, "处理完成")
            MeetingRepository.update_status(meeting_id, "done")

            logger.info(f"会议处理完成: {meeting_id}")
            return True

        except Exception as e:
            error_msg = str(e)
            self._set_state(PipelineState.FAILED, error_msg)
            self._report_error(error_msg)
            MeetingRepository.update_status(meeting_id, "failed")
            return False

        finally:
            self._current_meeting_id = None

    def process_async(
        self,
        meeting_id: int,
        audio_urls: Optional[list[str]] = None
    ) -> threading.Thread:
        """异步处理会议

        Args:
            meeting_id: 会议ID
            audio_urls: 音频URL列表

        Returns:
            处理线程
        """
        thread = threading.Thread(
            target=self.process,
            args=(meeting_id, audio_urls),
            daemon=True,
        )
        thread.start()
        return thread

    def _transcribe(
        self,
        meeting_id: int,
        audio_urls: Optional[list[str]] = None
    ) -> TranscriptResult:
        """执行 ASR 转写

        Args:
            meeting_id: 会议ID
            audio_urls: 音频URL列表

        Returns:
            合并后的转写结果
        """
        merger = TranscriptMerger()

        # 如果提供了 URL 列表，直接使用
        if audio_urls:
            total = len(audio_urls)
            with DoubaoASRProvider() as asr:
                for i, url in enumerate(audio_urls):
                    self._report_progress(
                        (i + 1) / total * 0.6,
                        f"正在转写音频 {i + 1}/{total}..."
                    )
                    result = asr.transcribe_url(url, t_start=0)
                    merger.add_result(result)

        else:
            # 从数据库获取切片信息
            chunks = AudioChunkRepository.get_by_meeting(meeting_id)
            if not chunks:
                logger.warning(f"会议 {meeting_id} 没有音频切片")
                return TranscriptResult(segments=[], full_text="", duration=0)

            total = len(chunks)
            logger.info(f"找到 {total} 个音频切片")

            # TODO: 实现本地文件上传到对象存储获取 URL
            # 当前版本需要音频 URL，这里暂时跳过
            logger.warning("本地音频转写需要配置文件上传服务，暂时跳过 ASR")

        return merger.get_merged_result()

    def _save_transcripts(
        self,
        meeting_id: int,
        transcript: TranscriptResult
    ) -> None:
        """保存转写结果到数据库

        Args:
            meeting_id: 会议ID
            transcript: 转写结果
        """
        # 先删除旧的转写记录
        TranscriptRepository.delete_by_meeting(meeting_id)

        # 批量创建新记录
        transcripts_data = [
            {
                "meeting_id": meeting_id,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "text": seg.text,
                "speaker_id": seg.speaker_id,
                "confidence": seg.confidence,
            }
            for seg in transcript.segments
        ]

        if transcripts_data:
            TranscriptRepository.create_batch(transcripts_data)
            logger.info(f"保存了 {len(transcripts_data)} 条转写记录")

    def _generate_minutes(
        self,
        meeting_id: int,
        transcript: TranscriptResult
    ) -> None:
        """生成会议纪要

        Args:
            meeting_id: 会议ID
            transcript: 转写结果
        """
        self._report_progress(0.7, "正在生成会议纪要...")

        # 获取会议和笔记
        meeting = MeetingRepository.get_by_id(meeting_id)
        notes = NoteRepository.get_by_meeting(meeting_id)

        # 如果没有转写内容，跳过生成
        if not transcript.segments:
            logger.warning("没有转写内容，跳过纪要生成")
            MeetingRepository.save_minutes(
                meeting_id,
                summary="（无转写内容）",
                decisions_json="[]",
                action_items_json="[]",
                topics_json="[]",
            )
            return

        # 生成纪要
        with MinutesGenerator() as generator:
            result = generator.generate(meeting, transcript, notes)

        self._report_progress(0.9, "正在保存会议纪要...")

        # 保存纪要
        MeetingRepository.save_minutes(
            meeting_id,
            summary=result.summary,
            decisions_json=json.dumps(result.decisions, ensure_ascii=False),
            action_items_json=json.dumps(result.action_items, ensure_ascii=False),
            topics_json=json.dumps(result.topics, ensure_ascii=False),
        )

        self._report_progress(1.0, "会议纪要已生成")
