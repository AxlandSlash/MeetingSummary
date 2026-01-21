"""笔记编辑器组件"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from meet_conclusion.db.models import Meeting, Note
from meet_conclusion.db.repositories import NoteRepository
from meet_conclusion.utils.logger import get_logger
from meet_conclusion.utils.time_utils import format_duration

logger = get_logger(__name__)


class NoteEditorWidget(QWidget):
    """笔记编辑器"""

    note_added = Signal(int)  # 笔记ID

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_meeting: Meeting | None = None
        self.get_elapsed_time = None  # 获取已录制时间的回调
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 标题
        title_label = QLabel("会议笔记")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # 笔记列表
        self.note_list = QListWidget()
        self.note_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
        """)
        layout.addWidget(self.note_list, stretch=1)

        # 输入区
        input_layout = QVBoxLayout()

        # 标签选择
        tag_layout = QHBoxLayout()
        tag_label = QLabel("标签：")
        tag_layout.addWidget(tag_label)

        self.tag_combo = QComboBox()
        self.tag_combo.addItem("普通", "general")
        self.tag_combo.addItem("TODO", "todo")
        self.tag_combo.addItem("风险", "risk")
        self.tag_combo.addItem("问题", "question")
        tag_layout.addWidget(self.tag_combo)

        tag_layout.addStretch()
        input_layout.addLayout(tag_layout)

        # 笔记输入框
        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText("输入笔记... (Ctrl+Enter 快速添加)")
        self.note_input.setMaximumHeight(80)
        input_layout.addWidget(self.note_input)

        # 添加按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.add_btn = QPushButton("添加笔记")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.add_btn.clicked.connect(self._add_note)
        btn_layout.addWidget(self.add_btn)

        input_layout.addLayout(btn_layout)
        layout.addLayout(input_layout)

        # 快捷键
        self.note_input.installEventFilter(self)

    def eventFilter(self, obj, event):
        """事件过滤器，处理快捷键"""
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QKeyEvent

        if obj == self.note_input and event.type() == QEvent.Type.KeyPress:
            key_event: QKeyEvent = event
            if key_event.key() == Qt.Key.Key_Return and key_event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self._add_note()
                return True
        return super().eventFilter(obj, event)

    def set_meeting(self, meeting: Meeting):
        """设置当前会议"""
        self.current_meeting = meeting
        self._refresh_notes()

    def set_elapsed_time_callback(self, callback):
        """设置获取已录制时间的回调"""
        self.get_elapsed_time = callback

    def _refresh_notes(self):
        """刷新笔记列表"""
        self.note_list.clear()
        if not self.current_meeting:
            return

        notes = NoteRepository.get_by_meeting(self.current_meeting.id)
        for note in notes:
            self._add_note_item(note)

    def _add_note_item(self, note: Note):
        """添加笔记项到列表"""
        item = QListWidgetItem()

        # 标签图标
        tag_icons = {
            "general": "📝",
            "todo": "✅",
            "risk": "⚠️",
            "question": "❓",
        }
        tag_icon = tag_icons.get(note.tag, "📝")

        # 时间
        time_str = format_duration(note.time_offset)

        # 显示文本
        text = f"{tag_icon} [{time_str}] {note.content}"
        item.setText(text)
        item.setData(Qt.ItemDataRole.UserRole, note.id)

        self.note_list.addItem(item)

    def _add_note(self):
        """添加笔记"""
        if not self.current_meeting:
            return

        content = self.note_input.toPlainText().strip()
        if not content:
            return

        # 获取当前时间偏移
        time_offset = 0.0
        if self.get_elapsed_time:
            time_offset = self.get_elapsed_time()

        # 获取标签
        tag = self.tag_combo.currentData()

        # 保存笔记
        note = NoteRepository.create(
            meeting_id=self.current_meeting.id,
            time_offset=time_offset,
            content=content,
            tag=tag,
        )

        # 添加到列表
        self._add_note_item(note)

        # 清空输入
        self.note_input.clear()

        logger.info(f"添加笔记: {note.id}, 时间: {time_offset}s")
        self.note_added.emit(note.id)
