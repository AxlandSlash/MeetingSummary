"""会议纪要生成器"""

import json
import re
from dataclasses import dataclass
from typing import Optional

from meet_conclusion.asr.base import TranscriptResult, TranscriptSegment
from meet_conclusion.db.models import Meeting, Note
from meet_conclusion.llm.base import LLMProvider
from meet_conclusion.llm.doubao_llm import DoubaoLLMProvider
from meet_conclusion.llm.prompt_templates import build_system_prompt, build_user_prompt
from meet_conclusion.utils.logger import get_logger
from meet_conclusion.utils.time_utils import format_duration

logger = get_logger(__name__)


@dataclass
class MinutesResult:
    """纪要生成结果"""

    summary: str
    decisions: list[dict]
    action_items: list[dict]
    topics: list[dict]
    raw_response: str


class MinutesGenerator:
    """会议纪要生成器"""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        """初始化

        Args:
            llm_provider: LLM 提供者，默认使用豆包
        """
        self._llm = llm_provider or DoubaoLLMProvider()

    def generate(
        self,
        meeting: Meeting,
        transcript: TranscriptResult,
        notes: list[Note],
    ) -> MinutesResult:
        """生成会议纪要

        Args:
            meeting: 会议对象
            transcript: 转写结果
            notes: 用户笔记列表

        Returns:
            纪要生成结果
        """
        logger.info(f"开始生成会议纪要: {meeting.id} - {meeting.title}")

        # 构建转写文本
        transcript_text = self._format_transcript(transcript)

        # 构建笔记列表
        notes_data = [
            {
                "time_offset": note.time_offset,
                "content": note.content,
                "tag": note.tag,
            }
            for note in notes
        ]

        # 构建会议信息
        meeting_info = {
            "title": meeting.title,
            "participants": meeting.participants,
        }

        # 构建 Prompt
        system_prompt = build_system_prompt(
            perspective=meeting.user_perspective,
            style=meeting.output_style,
            custom_perspective=meeting.custom_perspective,
        )

        user_prompt = build_user_prompt(
            transcript_text=transcript_text,
            notes=notes_data,
            meeting_info=meeting_info,
        )

        # 调用 LLM
        logger.info("调用 LLM 生成纪要...")
        response = self._llm.complete(
            prompt=user_prompt,
            system_prompt=system_prompt,
        )

        # 解析结果
        result = self._parse_response(response)
        logger.info(f"会议纪要生成完成: {len(result.summary)} 字摘要, "
                   f"{len(result.decisions)} 项决策, {len(result.action_items)} 项行动项")

        return result

    def _format_transcript(self, transcript: TranscriptResult) -> str:
        """格式化转写文本

        Args:
            transcript: 转写结果

        Returns:
            格式化的转写文本
        """
        lines = []
        for segment in transcript.segments:
            time_str = format_duration(segment.start_time)
            speaker = segment.speaker_id or "未知"
            lines.append(f"[{time_str}] {speaker}: {segment.text}")

        return "\n".join(lines)

    def _parse_response(self, response: str) -> MinutesResult:
        """解析 LLM 响应

        Args:
            response: LLM 响应文本

        Returns:
            解析后的纪要结果
        """
        # 尝试提取 JSON
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return MinutesResult(
                    summary=data.get("summary", ""),
                    decisions=data.get("decisions", []),
                    action_items=data.get("action_items", []),
                    topics=data.get("topics", []),
                    raw_response=response,
                )
            except json.JSONDecodeError as e:
                logger.warning(f"JSON 解析失败: {e}")

        # 如果 JSON 解析失败，将整个响应作为摘要
        logger.warning("未能解析 JSON 格式，将响应作为纯文本摘要")
        return MinutesResult(
            summary=response,
            decisions=[],
            action_items=[],
            topics=[],
            raw_response=response,
        )

    def close(self):
        """关闭资源"""
        if hasattr(self._llm, 'close'):
            self._llm.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
