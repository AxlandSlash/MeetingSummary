"""任务队列模块"""

import queue
import threading
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Optional

from meet_conclusion.utils.logger import get_logger

logger = get_logger(__name__)


class TaskType(Enum):
    """任务类型"""
    ASR = auto()       # ASR 转写
    DIARIZE = auto()   # 说话人分离
    LLM = auto()       # LLM 生成
    GENERAL = auto()   # 通用任务


@dataclass
class Task:
    """任务"""
    task_type: TaskType
    data: Any
    callback: Optional[Callable[[Any], None]] = None
    error_callback: Optional[Callable[[Exception], None]] = None


class TaskQueue:
    """任务队列

    支持多工作线程的任务队列
    """

    def __init__(self, num_workers: int = 2):
        """初始化

        Args:
            num_workers: 工作线程数
        """
        self._queue: queue.Queue[Optional[Task]] = queue.Queue()
        self._workers: list[threading.Thread] = []
        self._running = False
        self._num_workers = num_workers

    def start(self) -> None:
        """启动任务队列"""
        if self._running:
            return

        self._running = True
        for i in range(self._num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"TaskWorker-{i}",
                daemon=True,
            )
            worker.start()
            self._workers.append(worker)

        logger.info(f"任务队列已启动，工作线程数: {self._num_workers}")

    def stop(self, wait: bool = True) -> None:
        """停止任务队列

        Args:
            wait: 是否等待所有任务完成
        """
        self._running = False

        # 发送停止信号
        for _ in self._workers:
            self._queue.put(None)

        if wait:
            for worker in self._workers:
                worker.join(timeout=5.0)

        self._workers.clear()
        logger.info("任务队列已停止")

    def submit(self, task: Task) -> None:
        """提交任务

        Args:
            task: 任务对象
        """
        if not self._running:
            logger.warning("任务队列未启动，无法提交任务")
            return

        self._queue.put(task)
        logger.debug(f"提交任务: {task.task_type.name}")

    def _worker_loop(self) -> None:
        """工作线程循环"""
        while self._running:
            try:
                task = self._queue.get(timeout=1.0)
                if task is None:
                    break

                self._process_task(task)
                self._queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"工作线程异常: {e}")

    def _process_task(self, task: Task) -> None:
        """处理任务

        Args:
            task: 任务对象
        """
        try:
            logger.debug(f"开始处理任务: {task.task_type.name}")

            # 根据任务类型处理
            result = self._execute_task(task)

            # 执行回调
            if task.callback:
                task.callback(result)

            logger.debug(f"任务处理完成: {task.task_type.name}")

        except Exception as e:
            logger.error(f"任务处理失败: {task.task_type.name} - {e}")
            if task.error_callback:
                task.error_callback(e)

    def _execute_task(self, task: Task) -> Any:
        """执行任务

        Args:
            task: 任务对象

        Returns:
            任务结果
        """
        if task.task_type == TaskType.ASR:
            return self._execute_asr_task(task.data)
        elif task.task_type == TaskType.DIARIZE:
            return self._execute_diarize_task(task.data)
        elif task.task_type == TaskType.LLM:
            return self._execute_llm_task(task.data)
        elif task.task_type == TaskType.GENERAL:
            # 通用任务：data 应该是一个可调用对象
            if callable(task.data):
                return task.data()
            return task.data
        else:
            raise ValueError(f"未知的任务类型: {task.task_type}")

    def _execute_asr_task(self, data: dict) -> Any:
        """执行 ASR 任务"""
        from meet_conclusion.asr.doubao_asr import DoubaoASRProvider

        audio_url = data.get("audio_url")
        t_start = data.get("t_start", 0.0)

        with DoubaoASRProvider() as asr:
            return asr.transcribe_url(audio_url, t_start)

    def _execute_diarize_task(self, data: dict) -> Any:
        """执行说话人分离任务"""
        # TODO: 实现说话人分离
        return []

    def _execute_llm_task(self, data: dict) -> Any:
        """执行 LLM 任务"""
        from meet_conclusion.llm.doubao_llm import DoubaoLLMProvider

        prompt = data.get("prompt")
        system_prompt = data.get("system_prompt")

        with DoubaoLLMProvider() as llm:
            return llm.complete(prompt, system_prompt)

    def pending_count(self) -> int:
        """获取待处理任务数"""
        return self._queue.qsize()

    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running


# 全局任务队列实例
_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """获取任务队列实例"""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue
