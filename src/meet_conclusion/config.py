"""配置管理模块

使用pydantic-settings管理应用配置，支持环境变量和.env文件
"""

import os
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_app_data_dir() -> Path:
    """获取应用数据目录"""
    if os.name == "nt":  # Windows
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path.home() / ".local" / "share"

    app_dir = base / "MeetConclusion"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


class DoubaoASRConfig(BaseSettings):
    """豆包ASR配置"""

    model_config = SettingsConfigDict(env_prefix="DOUBAO_ASR_")

    app_id: str = Field(default="", description="豆包ASR App ID")
    access_token: str = Field(default="", description="豆包ASR Access Token")
    resource_id: str = Field(default="volc.bigasr.auc", description="资源ID")
    submit_url: str = Field(
        default="https://openspeech-direct.zijieapi.com/api/v3/auc/bigmodel/submit",
        description="提交任务URL"
    )
    query_url: str = Field(
        default="https://openspeech-direct.zijieapi.com/api/v3/auc/bigmodel/query",
        description="查询任务URL"
    )


class DoubaoLLMConfig(BaseSettings):
    """豆包LLM配置"""

    model_config = SettingsConfigDict(env_prefix="DOUBAO_LLM_")

    api_key: str = Field(default="", description="豆包LLM API Key")
    api_base: str = Field(
        default="https://ark.cn-beijing.volces.com/api/v3",
        description="API基础URL"
    )
    model: str = Field(default="doubao-pro-32k", description="模型名称")
    max_tokens: int = Field(default=4096, description="最大输出token数")
    temperature: float = Field(default=0.7, description="生成温度")


class AudioConfig(BaseSettings):
    """音频配置"""

    model_config = SettingsConfigDict(env_prefix="AUDIO_")

    sample_rate: int = Field(default=16000, description="采样率")
    channels: int = Field(default=1, description="声道数")
    chunk_duration: int = Field(default=60, description="切片时长(秒)")
    overlap_duration: float = Field(default=0.5, description="切片重叠时长(秒)")
    buffer_size: int = Field(default=1024, description="缓冲区大小")


class AppConfig(BaseSettings):
    """应用主配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        extra="ignore"
    )

    # 应用信息
    name: str = Field(default="会议纪要AI", description="应用名称")
    version: str = Field(default="0.1.0", description="应用版本")
    debug: bool = Field(default=False, description="调试模式")

    # 路径配置
    data_dir: Path = Field(default_factory=get_app_data_dir, description="数据目录")

    # 子配置
    doubao_asr: DoubaoASRConfig = Field(default_factory=DoubaoASRConfig)
    doubao_llm: DoubaoLLMConfig = Field(default_factory=DoubaoLLMConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)

    @property
    def db_path(self) -> Path:
        """数据库文件路径"""
        db_dir = self.data_dir / "db"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / "meet_conclusion.db"

    @property
    def audio_dir(self) -> Path:
        """音频文件目录"""
        audio_dir = self.data_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        return audio_dir

    @property
    def chunks_dir(self) -> Path:
        """音频切片目录"""
        chunks_dir = self.audio_dir / "chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        return chunks_dir

    @property
    def logs_dir(self) -> Path:
        """日志目录"""
        logs_dir = self.data_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir


# 用户视角类型
UserPerspective = Literal["worker", "manager", "boss", "custom"]

# 输出风格类型
OutputStyle = Literal["sarcastic", "neutral", "comforting"]

# 会议状态类型
MeetingStatus = Literal["draft", "recording", "processing", "done", "failed"]

# 笔记标签类型
NoteTag = Literal["todo", "risk", "question", "general"]


# 全局配置实例
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


def reload_config() -> AppConfig:
    """重新加载配置"""
    global _config
    _config = AppConfig()
    return _config
