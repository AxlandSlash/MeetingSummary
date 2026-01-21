"""会议列表组件"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from meet_conclusion.db.models import Meeting
from meet_conclusion.db.repositories import MeetingRepository
from meet_conclusion.utils.logger import get_logger
from meet_conclusion.utils.time_utils import format_timestamp, format_duration

logger = get_logger(__name__)


class MeetingListWidget(QWidget):
    """会议列表组件"""

    meeting_selected = Signal(int)  # 会议ID
    new_meeting_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 标题
        title_label = QLabel("会议列表")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # 新建会议按钮
        self.new_btn = QPushButton("+ 新建会议")
        self.new_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.new_btn.clicked.connect(self.new_meeting_clicked.emit)
        layout.addWidget(self.new_btn)

        # 搜索框
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索会议...")
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # 会议列表
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget)

    def refresh(self):
        """刷新会议列表"""
        self.list_widget.clear()
        meetings = MeetingRepository.get_all(limit=100)
        for meeting in meetings:
            self._add_meeting_item(meeting)
        logger.debug(f"刷新会议列表，共 {len(meetings)} 条")

    def _add_meeting_item(self, meeting: Meeting):
        """添加会议项"""
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, meeting.id)

        # 状态图标
        status_icons = {
            "draft": "📝",
            "recording": "🔴",
            "processing": "⏳",
            "done": "✅",
            "failed": "❌",
        }
        status_icon = status_icons.get(meeting.status, "❓")

        # 时长
        duration_str = ""
        if meeting.duration:
            duration_str = f" ({format_duration(meeting.duration)})"

        # 显示文本
        text = f"{status_icon} {meeting.title}{duration_str}\n"
        text += f"   {format_timestamp(meeting.created_at)}"

        item.setText(text)
        self.list_widget.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem):
        """处理项目点击"""
        meeting_id = item.data(Qt.ItemDataRole.UserRole)
        self.meeting_selected.emit(meeting_id)

    def _on_search(self, text: str):
        """处理搜索"""
        if text:
            meetings = MeetingRepository.search(text)
        else:
            meetings = MeetingRepository.get_all(limit=100)

        self.list_widget.clear()
        for meeting in meetings:
            self._add_meeting_item(meeting)
