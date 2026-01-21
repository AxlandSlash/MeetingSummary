"""录制控制面板组件"""

from datetime import datetime

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from meet_conclusion.db.models import Meeting
from meet_conclusion.utils.logger import get_logger
from meet_conclusion.utils.time_utils import format_duration

logger = get_logger(__name__)


class RecordingPanelWidget(QWidget):
    """录制控制面板"""

    stop_recording = Signal(int)  # 会议ID

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_meeting: Meeting | None = None
        self.start_time: datetime | None = None
        self.elapsed_seconds = 0
        self._init_ui()
        self._setup_timer()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # 状态指示
        status_layout = QHBoxLayout()

        self.status_indicator = QLabel("🔴")
        self.status_indicator.setStyleSheet("font-size: 24px;")
        status_layout.addWidget(self.status_indicator)

        self.status_label = QLabel("正在录制...")
        self.status_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        status_layout.addWidget(self.status_label)

        status_layout.addStretch()
        layout.addLayout(status_layout)

        # 会议标题
        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-size: 16px; color: #333; margin-top: 10px;")
        layout.addWidget(self.title_label)

        # 录制时长
        time_layout = QHBoxLayout()
        time_label = QLabel("录制时长：")
        time_label.setStyleSheet("font-size: 14px; color: #666;")
        time_layout.addWidget(time_label)

        self.duration_label = QLabel("00:00")
        self.duration_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #f44336;")
        time_layout.addWidget(self.duration_label)

        time_layout.addStretch()
        layout.addLayout(time_layout)

        layout.addStretch()

        # 停止按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.stop_btn = QPushButton("结束纪要")
        self.stop_btn.setMinimumWidth(150)
        self.stop_btn.setMinimumHeight(50)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.stop_btn.clicked.connect(self._on_stop)
        btn_layout.addWidget(self.stop_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _setup_timer(self):
        """设置定时器"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_duration)

    def _update_duration(self):
        """更新录制时长显示"""
        if self.start_time:
            self.elapsed_seconds = (datetime.now() - self.start_time).total_seconds()
            self.duration_label.setText(format_duration(self.elapsed_seconds))

    def set_meeting(self, meeting: Meeting):
        """设置当前会议"""
        self.current_meeting = meeting
        self.title_label.setText(f"会议：{meeting.title}")

    def start_recording(self, meeting: Meeting):
        """开始录制"""
        self.current_meeting = meeting
        self.title_label.setText(f"会议：{meeting.title}")
        self.start_time = datetime.now()
        self.elapsed_seconds = 0
        self.duration_label.setText("00:00")
        self.timer.start(1000)  # 每秒更新

        # TODO: 启动实际的音频录制
        logger.info(f"开始录制会议: {meeting.id}")

    def stop(self):
        """停止录制"""
        self.timer.stop()
        # TODO: 停止实际的音频录制
        logger.info(f"停止录制，时长: {self.elapsed_seconds}秒")

    def _on_stop(self):
        """处理停止按钮点击"""
        if self.current_meeting:
            self.stop_recording.emit(self.current_meeting.id)

    def get_elapsed_seconds(self) -> float:
        """获取已录制的秒数"""
        return self.elapsed_seconds
