"""时间工具模块"""

from datetime import datetime, timedelta


def format_duration(seconds: float) -> str:
    """格式化时长为可读字符串

    Args:
        seconds: 秒数

    Returns:
        格式化的时长字符串，如 "01:23:45" 或 "23:45"
    """
    td = timedelta(seconds=int(seconds))
    hours, remainder = divmod(td.seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours > 0 or td.days > 0:
        total_hours = td.days * 24 + hours
        return f"{total_hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_timestamp(dt: datetime) -> str:
    """格式化时间戳

    Args:
        dt: datetime对象

    Returns:
        格式化的时间字符串
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_date(dt: datetime) -> str:
    """格式化日期

    Args:
        dt: datetime对象

    Returns:
        格式化的日期字符串
    """
    return dt.strftime("%Y-%m-%d")


def seconds_to_time_str(seconds: float) -> str:
    """将秒数转换为时间字符串

    Args:
        seconds: 秒数

    Returns:
        时间字符串，如 "00:01:23.456"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def time_str_to_seconds(time_str: str) -> float:
    """将时间字符串转换为秒数

    Args:
        time_str: 时间字符串，支持 "HH:MM:SS.mmm" 或 "MM:SS.mmm" 或 "MM:SS"

    Returns:
        秒数
    """
    parts = time_str.split(":")
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    elif len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    else:
        return float(time_str)
