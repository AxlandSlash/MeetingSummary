"""日志管理模块

使用loguru实现日志记录，支持文件和控制台输出
"""

import sys
from pathlib import Path

from loguru import logger

from meet_conclusion.config import get_config


def setup_logger() -> None:
    """配置日志系统"""
    config = get_config()

    # 移除默认处理器
    logger.remove()

    # 日志格式
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # 简单格式（用于控制台）
    simple_format = (
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<level>{message}</level>"
    )

    # 控制台输出
    logger.add(
        sys.stderr,
        format=simple_format,
        level="DEBUG" if config.debug else "INFO",
        colorize=True,
    )

    # 文件输出 - 常规日志
    log_file = config.logs_dir / "app_{time:YYYY-MM-DD}.log"
    logger.add(
        str(log_file),
        format=log_format,
        level="DEBUG",
        rotation="00:00",  # 每天轮转
        retention="30 days",  # 保留30天
        encoding="utf-8",
        enqueue=True,  # 异步写入
    )

    # 文件输出 - 错误日志
    error_log_file = config.logs_dir / "error_{time:YYYY-MM-DD}.log"
    logger.add(
        str(error_log_file),
        format=log_format,
        level="ERROR",
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
        enqueue=True,
    )

    logger.info(f"日志系统初始化完成，日志目录: {config.logs_dir}")


def get_logger(name: str = None):
    """获取logger实例

    Args:
        name: 模块名称，用于日志上下文

    Returns:
        logger实例
    """
    if name:
        return logger.bind(name=name)
    return logger
