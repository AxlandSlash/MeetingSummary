"""转写结果合并模块

将多个切片的转写结果合并为完整的会议转写
"""

from typing import Optional

from meet_conclusion.asr.base import TranscriptResult, TranscriptSegment
from meet_conclusion.utils.logger import get_logger

logger = get_logger(__name__)


class TranscriptMerger:
    """转写结果合并器"""

    def __init__(self, overlap_threshold: float = 0.5):
        """初始化

        Args:
            overlap_threshold: 重叠检测阈值（秒），用于去重
        """
        self.overlap_threshold = overlap_threshold
        self._segments: list[TranscriptSegment] = []

    def add_result(self, result: TranscriptResult) -> None:
        """添加转写结果

        Args:
            result: 转写结果
        """
        for segment in result.segments:
            self._add_segment(segment)

    def _add_segment(self, new_segment: TranscriptSegment) -> None:
        """添加单个片段，处理重叠去重

        Args:
            new_segment: 新片段
        """
        if not self._segments:
            self._segments.append(new_segment)
            return

        # 检查是否与最后几个片段重叠
        is_duplicate = False
        for i in range(min(5, len(self._segments))):
            existing = self._segments[-(i + 1)]

            # 检查时间重叠
            time_overlap = self._calculate_time_overlap(existing, new_segment)
            if time_overlap > self.overlap_threshold:
                # 检查文本相似度
                text_similarity = self._calculate_text_similarity(
                    existing.text, new_segment.text
                )
                if text_similarity > 0.7:
                    is_duplicate = True
                    logger.debug(
                        f"检测到重复片段: '{new_segment.text[:30]}...' "
                        f"(时间重叠: {time_overlap:.2f}s, 相似度: {text_similarity:.2f})"
                    )
                    break

        if not is_duplicate:
            self._segments.append(new_segment)

    def _calculate_time_overlap(
        self,
        seg1: TranscriptSegment,
        seg2: TranscriptSegment
    ) -> float:
        """计算两个片段的时间重叠

        Returns:
            重叠时长（秒）
        """
        overlap_start = max(seg1.start_time, seg2.start_time)
        overlap_end = min(seg1.end_time, seg2.end_time)
        return max(0, overlap_end - overlap_start)

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算两段文本的相似度

        使用简单的字符级别 Jaccard 相似度

        Returns:
            相似度 (0-1)
        """
        if not text1 or not text2:
            return 0.0

        # 移除空白字符
        text1 = text1.replace(" ", "").replace("\n", "")
        text2 = text2.replace(" ", "").replace("\n", "")

        if not text1 or not text2:
            return 0.0

        # 使用字符集合计算 Jaccard 相似度
        set1 = set(text1)
        set2 = set(text2)

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        if union == 0:
            return 0.0

        return intersection / union

    def get_merged_result(self) -> TranscriptResult:
        """获取合并后的结果

        Returns:
            合并后的转写结果
        """
        # 按时间排序
        sorted_segments = sorted(self._segments, key=lambda s: s.start_time)

        # 构建完整文本
        full_text_parts = [seg.text for seg in sorted_segments]
        full_text = "".join(full_text_parts)

        # 计算总时长
        duration = 0.0
        if sorted_segments:
            duration = sorted_segments[-1].end_time - sorted_segments[0].start_time

        return TranscriptResult(
            segments=sorted_segments,
            full_text=full_text,
            duration=duration,
            language="zh-CN",
        )

    def get_segments(self) -> list[TranscriptSegment]:
        """获取所有片段"""
        return sorted(self._segments, key=lambda s: s.start_time)

    def get_segments_by_speaker(self) -> dict[str, list[TranscriptSegment]]:
        """按说话人分组获取片段

        Returns:
            {speaker_id: [segments]}
        """
        result: dict[str, list[TranscriptSegment]] = {}
        for segment in self._segments:
            speaker = segment.speaker_id or "Unknown"
            if speaker not in result:
                result[speaker] = []
            result[speaker].append(segment)

        # 每个说话人的片段按时间排序
        for speaker in result:
            result[speaker].sort(key=lambda s: s.start_time)

        return result

    def clear(self) -> None:
        """清空所有片段"""
        self._segments.clear()

    def segment_count(self) -> int:
        """获取片段数量"""
        return len(self._segments)


def merge_transcripts(
    results: list[TranscriptResult],
    overlap_threshold: float = 0.5
) -> TranscriptResult:
    """合并多个转写结果

    Args:
        results: 转写结果列表
        overlap_threshold: 重叠检测阈值

    Returns:
        合并后的转写结果
    """
    merger = TranscriptMerger(overlap_threshold)
    for result in results:
        merger.add_result(result)
    return merger.get_merged_result()
