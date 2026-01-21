"""设置对话框"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from meet_conclusion.config import get_config
from meet_conclusion.utils.logger import get_logger

logger = get_logger(__name__)


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumSize(500, 400)
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 标签页
        tab_widget = QTabWidget()

        # 豆包 ASR 设置
        asr_tab = QWidget()
        asr_layout = QFormLayout(asr_tab)

        self.asr_app_id = QLineEdit()
        self.asr_app_id.setPlaceholderText("请输入豆包 ASR App ID")
        asr_layout.addRow("App ID:", self.asr_app_id)

        self.asr_token = QLineEdit()
        self.asr_token.setPlaceholderText("请输入豆包 ASR Access Token")
        self.asr_token.setEchoMode(QLineEdit.EchoMode.Password)
        asr_layout.addRow("Access Token:", self.asr_token)

        tab_widget.addTab(asr_tab, "语音识别")

        # 豆包 LLM 设置
        llm_tab = QWidget()
        llm_layout = QFormLayout(llm_tab)

        self.llm_api_key = QLineEdit()
        self.llm_api_key.setPlaceholderText("请输入豆包 LLM API Key")
        self.llm_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        llm_layout.addRow("API Key:", self.llm_api_key)

        self.llm_model = QLineEdit()
        self.llm_model.setPlaceholderText("例如: doubao-pro-32k")
        llm_layout.addRow("模型:", self.llm_model)

        tab_widget.addTab(llm_tab, "大模型")

        # 音频设置
        audio_tab = QWidget()
        audio_layout = QFormLayout(audio_tab)

        self.chunk_duration = QLineEdit()
        self.chunk_duration.setPlaceholderText("默认 60 秒")
        audio_layout.addRow("切片时长(秒):", self.chunk_duration)

        tab_widget.addTab(audio_tab, "音频")

        layout.addWidget(tab_widget)

        # 说明
        hint_label = QLabel(
            "<p style='color: #666; font-size: 12px;'>"
            "提示：设置将保存到 .env 文件中。部分设置需要重启应用生效。"
            "</p>"
        )
        layout.addWidget(hint_label)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _load_settings(self):
        """加载当前设置"""
        config = get_config()

        self.asr_app_id.setText(config.doubao_asr.app_id)
        self.asr_token.setText(config.doubao_asr.access_token)

        self.llm_api_key.setText(config.doubao_llm.api_key)
        self.llm_model.setText(config.doubao_llm.model)

        self.chunk_duration.setText(str(config.audio.chunk_duration))

    def _save_settings(self):
        """保存设置"""
        # TODO: 实际保存到 .env 文件
        logger.info("保存设置")
        self.accept()
