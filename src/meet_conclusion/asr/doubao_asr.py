"""豆包 ASR 实现

基于豆包大模型语音识别 API 的实现
"""

import json
import time
import uuid
from pathlib import Path
from typing import Optional

import httpx

from meet_conclusion.asr.base import ASRProvider, TranscriptResult, TranscriptSegment
from meet_conclusion.config import get_config
from meet_conclusion.utils.logger import get_logger

logger = get_logger(__name__)


class DoubaoASRProvider(ASRProvider):
    """豆包 ASR 提供者"""

    def __init__(
        self,
        app_id: Optional[str] = None,
        access_token: Optional[str] = None,
    ):
        """初始化

        Args:
            app_id: 应用ID，默认从配置读取
            access_token: 访问令牌，默认从配置读取
        """
        config = get_config()
        self.app_id = app_id or config.doubao_asr.app_id
        self.access_token = access_token or config.doubao_asr.access_token
        self.resource_id = config.doubao_asr.resource_id
        self.submit_url = config.doubao_asr.submit_url
        self.query_url = config.doubao_asr.query_url

        self._client = httpx.Client(timeout=60.0)

    @property
    def name(self) -> str:
        return "doubao"

    @property
    def supports_speaker_diarization(self) -> bool:
        return True

    def _build_headers(self, task_id: str, sequence: str = "-1") -> dict:
        """构建请求头"""
        return {
            "X-Api-App-Key": self.app_id,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-Request-Id": task_id,
            "X-Api-Sequence": sequence,
            "Content-Type": "application/json",
        }

    def _submit_task(self, audio_url: str) -> tuple[str, str]:
        """提交转写任务

        Args:
            audio_url: 音频URL

        Returns:
            (task_id, x_tt_logid)
        """
        task_id = str(uuid.uuid4())
        headers = self._build_headers(task_id)

        request_body = {
            "user": {
                "uid": "meet_conclusion_user"
            },
            "audio": {
                "url": audio_url,
            },
            "request": {
                "model_name": "bigmodel",
                "enable_channel_split": True,
                "enable_ddc": True,
                "enable_speaker_info": True,
                "enable_punc": True,
                "enable_itn": True,
            }
        }

        logger.info(f"提交 ASR 任务: {task_id}")
        response = self._client.post(
            self.submit_url,
            headers=headers,
            content=json.dumps(request_body),
        )

        status_code = response.headers.get("X-Api-Status-Code", "")
        x_tt_logid = response.headers.get("X-Tt-Logid", "")

        if status_code == "20000000":
            logger.info(f"ASR 任务提交成功: {task_id}")
            return task_id, x_tt_logid
        else:
            message = response.headers.get("X-Api-Message", "Unknown error")
            logger.error(f"ASR 任务提交失败: {message}")
            raise RuntimeError(f"提交 ASR 任务失败: {message}")

    def _query_task(self, task_id: str, x_tt_logid: str) -> tuple[str, Optional[dict]]:
        """查询任务状态

        Args:
            task_id: 任务ID
            x_tt_logid: 日志ID

        Returns:
            (status_code, result_data)
        """
        headers = self._build_headers(task_id)
        headers["X-Tt-Logid"] = x_tt_logid

        response = self._client.post(
            self.query_url,
            headers=headers,
            content=json.dumps({}),
        )

        status_code = response.headers.get("X-Api-Status-Code", "")
        message = response.headers.get("X-Api-Message", "")

        if status_code == "20000000":
            # 任务完成
            return status_code, response.json()
        elif status_code in ("20000001", "20000002"):
            # 任务进行中
            logger.debug(f"ASR 任务进行中: {message}")
            return status_code, None
        else:
            logger.error(f"ASR 任务查询失败: {message}")
            raise RuntimeError(f"查询 ASR 任务失败: {message}")

    def _wait_for_result(
        self,
        task_id: str,
        x_tt_logid: str,
        timeout: int = 300,
        poll_interval: int = 2,
    ) -> dict:
        """等待任务完成

        Args:
            task_id: 任务ID
            x_tt_logid: 日志ID
            timeout: 超时时间（秒）
            poll_interval: 轮询间隔（秒）

        Returns:
            识别结果
        """
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"ASR 任务超时: {task_id}")

            status_code, result = self._query_task(task_id, x_tt_logid)

            if status_code == "20000000" and result:
                return result

            time.sleep(poll_interval)

    def _parse_result(self, result: dict, t_start: float) -> TranscriptResult:
        """解析识别结果

        Args:
            result: API 返回的结果
            t_start: 起始时间偏移

        Returns:
            转写结果
        """
        segments = []
        full_text_parts = []

        # 解析 utterances
        utterances = result.get("result", {}).get("utterances", [])

        for utt in utterances:
            text = utt.get("text", "")
            if not text.strip():
                continue

            start_time = utt.get("start_time", 0) / 1000.0 + t_start  # 转换为秒
            end_time = utt.get("end_time", 0) / 1000.0 + t_start
            speaker_id = utt.get("speaker_info", {}).get("speaker_id", None)
            confidence = utt.get("confidence", None)

            segment = TranscriptSegment(
                start_time=start_time,
                end_time=end_time,
                text=text,
                speaker_id=f"S{speaker_id}" if speaker_id is not None else None,
                confidence=confidence,
            )
            segments.append(segment)
            full_text_parts.append(text)

        # 计算总时长
        duration = 0.0
        if segments:
            duration = segments[-1].end_time - segments[0].start_time

        return TranscriptResult(
            segments=segments,
            full_text="".join(full_text_parts),
            duration=duration,
            language="zh-CN",
        )

    def transcribe_url(
        self,
        audio_url: str,
        t_start: float = 0.0,
    ) -> TranscriptResult:
        """转写音频URL

        Args:
            audio_url: 音频URL
            t_start: 起始时间偏移（秒）

        Returns:
            转写结果
        """
        # 提交任务
        task_id, x_tt_logid = self._submit_task(audio_url)

        # 等待结果
        result = self._wait_for_result(task_id, x_tt_logid)

        # 解析结果
        return self._parse_result(result, t_start)

    def transcribe(
        self,
        audio_path: Path,
        t_start: float = 0.0,
    ) -> TranscriptResult:
        """转写本地音频文件

        注意：豆包 API 需要音频 URL，本方法需要先将文件上传

        Args:
            audio_path: 音频文件路径
            t_start: 起始时间偏移（秒）

        Returns:
            转写结果
        """
        # TODO: 实现文件上传到对象存储，然后获取 URL
        # 当前版本需要用户自行提供音频 URL
        raise NotImplementedError(
            "本地文件转写需要先上传到对象存储获取 URL，"
            "请使用 transcribe_url 方法或配置文件上传服务"
        )

    def close(self):
        """关闭客户端"""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
