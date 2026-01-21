"""会议创建表单组件"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from meet_conclusion.db.models import Meeting
from meet_conclusion.db.repositories import MeetingRepository
from meet_conclusion.utils.logger import get_logger

logger = get_logger(__name__)


class MeetingFormWidget(QWidget):
    """会议创建/编辑表单"""

    start_recording = Signal(int)  # 会议ID

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_meeting_id = None
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title_label = QLabel("新建会议")
        title_label.setObjectName("form_title")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(title_label)
        self.title_label = title_label

        # 表单
        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        # 会议标题
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("请输入会议标题")
        self.title_input.setMinimumHeight(36)
        form_layout.addRow("会议标题 *", self.title_input)

        # 参与人
        self.participants_input = QLineEdit()
        self.participants_input.setPlaceholderText("参与人（可选，用逗号分隔）")
        self.participants_input.setMinimumHeight(36)
        form_layout.addRow("参与人", self.participants_input)

        # 用户视角
        self.perspective_combo = QComboBox()
        self.perspective_combo.addItem("打工人", "worker")
        self.perspective_combo.addItem("管理者", "manager")
        self.perspective_combo.addItem("老板", "boss")
        self.perspective_combo.addItem("自定义", "custom")
        self.perspective_combo.setMinimumHeight(36)
        self.perspective_combo.currentIndexChanged.connect(self._on_perspective_changed)
        form_layout.addRow("您的视角", self.perspective_combo)

        # 自定义视角（默认隐藏）
        self.custom_perspective_input = QTextEdit()
        self.custom_perspective_input.setPlaceholderText("请描述您关注的重点...")
        self.custom_perspective_input.setMaximumHeight(80)
        self.custom_perspective_input.hide()
        form_layout.addRow("视角描述", self.custom_perspective_input)

        # 输出风格
        self.style_combo = QComboBox()
        self.style_combo.addItem("中立客观", "neutral")
        self.style_combo.addItem("尖酸刻薄", "sarcastic")
        self.style_combo.addItem("安慰体贴", "comforting")
        self.style_combo.setMinimumHeight(36)
        form_layout.addRow("输出风格", self.style_combo)

        layout.addLayout(form_layout)

        # 风格说明
        style_hints = QLabel("""
        <p style="color: #666; font-size: 12px;">
        <b>中立客观</b>：报告体风格，尽量不带情绪<br>
        <b>尖酸刻薄</b>：直指问题与风险，语言简洁冷辣<br>
        <b>安慰体贴</b>：适度缓冲负面内容，强调进展与建议
        </p>
        """)
        layout.addWidget(style_hints)

        layout.addStretch()

        # 按钮区
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.save_btn = QPushButton("保存")
        self.save_btn.setMinimumWidth(100)
        self.save_btn.setMinimumHeight(40)
        self.save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self.save_btn)

        self.start_btn = QPushButton("开始纪要")
        self.start_btn.setMinimumWidth(120)
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.start_btn.clicked.connect(self._on_start)
        btn_layout.addWidget(self.start_btn)

        layout.addLayout(btn_layout)

    def _on_perspective_changed(self, index: int):
        """处理视角选择变化"""
        perspective = self.perspective_combo.currentData()
        if perspective == "custom":
            self.custom_perspective_input.show()
        else:
            self.custom_perspective_input.hide()

    def _on_save(self):
        """保存会议"""
        title = self.title_input.text().strip()
        if not title:
            # TODO: 显示错误提示
            return

        participants = self.participants_input.text().strip() or None
        perspective = self.perspective_combo.currentData()
        custom_perspective = None
        if perspective == "custom":
            custom_perspective = self.custom_perspective_input.toPlainText().strip() or None
        style = self.style_combo.currentData()

        if self.current_meeting_id:
            # 更新
            MeetingRepository.update(
                self.current_meeting_id,
                title=title,
                participants=participants,
                user_perspective=perspective,
                custom_perspective=custom_perspective,
                output_style=style,
            )
        else:
            # 创建
            meeting = MeetingRepository.create(
                title=title,
                participants=participants,
                user_perspective=perspective,
                custom_perspective=custom_perspective,
                output_style=style,
            )
            self.current_meeting_id = meeting.id

        logger.info(f"保存会议: {self.current_meeting_id}")

    def _on_start(self):
        """开始录制"""
        # 先保存
        self._on_save()
        if self.current_meeting_id:
            self.start_recording.emit(self.current_meeting_id)

    def reset(self):
        """重置表单"""
        self.current_meeting_id = None
        self.title_label.setText("新建会议")
        self.title_input.clear()
        self.participants_input.clear()
        self.perspective_combo.setCurrentIndex(0)
        self.custom_perspective_input.clear()
        self.custom_perspective_input.hide()
        self.style_combo.setCurrentIndex(0)

    def load_meeting(self, meeting: Meeting):
        """加载会议数据"""
        self.current_meeting_id = meeting.id
        self.title_label.setText("编辑会议")
        self.title_input.setText(meeting.title)
        self.participants_input.setText(meeting.participants or "")

        # 设置视角
        index = self.perspective_combo.findData(meeting.user_perspective)
        if index >= 0:
            self.perspective_combo.setCurrentIndex(index)
        if meeting.user_perspective == "custom" and meeting.custom_perspective:
            self.custom_perspective_input.setPlainText(meeting.custom_perspective)
            self.custom_perspective_input.show()

        # 设置风格
        index = self.style_combo.findData(meeting.output_style)
        if index >= 0:
            self.style_combo.setCurrentIndex(index)
