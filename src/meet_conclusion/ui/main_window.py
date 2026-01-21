"""主窗口"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from meet_conclusion.config import get_config
from meet_conclusion.ui.widgets.meeting_list import MeetingListWidget
from meet_conclusion.ui.widgets.meeting_form import MeetingFormWidget
from meet_conclusion.ui.widgets.recording_panel import RecordingPanelWidget
from meet_conclusion.ui.widgets.note_editor import NoteEditorWidget
from meet_conclusion.ui.widgets.minutes_viewer import MinutesViewerWidget
from meet_conclusion.utils.logger import get_logger

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.config = get_config()
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f"{self.config.name} v{self.config.version}")
        self.setMinimumSize(1200, 800)

        # 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 使用分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # 左侧：会议列表
        self.meeting_list = MeetingListWidget()
        self.meeting_list.setMinimumWidth(250)
        self.meeting_list.setMaximumWidth(400)
        splitter.addWidget(self.meeting_list)

        # 右侧：主内容区
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)

        # 会议表单/录制控制区
        self.meeting_form = MeetingFormWidget()
        self.recording_panel = RecordingPanelWidget()
        self.recording_panel.hide()

        right_layout.addWidget(self.meeting_form)
        right_layout.addWidget(self.recording_panel)

        # 下方分割区：笔记编辑 + 纪要查看
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.note_editor = NoteEditorWidget()
        self.note_editor.hide()
        bottom_splitter.addWidget(self.note_editor)

        self.minutes_viewer = MinutesViewerWidget()
        self.minutes_viewer.hide()
        bottom_splitter.addWidget(self.minutes_viewer)

        right_layout.addWidget(bottom_splitter, stretch=1)

        splitter.addWidget(right_widget)

        # 设置分割比例
        splitter.setSizes([280, 920])

        logger.info("主窗口UI初始化完成")

    def _connect_signals(self):
        """连接信号"""
        # 会议列表选中信号
        self.meeting_list.meeting_selected.connect(self._on_meeting_selected)
        self.meeting_list.new_meeting_clicked.connect(self._on_new_meeting)

        # 会议表单信号
        self.meeting_form.start_recording.connect(self._on_start_recording)

        # 录制面板信号
        self.recording_panel.stop_recording.connect(self._on_stop_recording)

    def _on_meeting_selected(self, meeting_id: int):
        """处理会议选中事件"""
        logger.info(f"选中会议: {meeting_id}")
        from meet_conclusion.db.repositories import MeetingRepository
        meeting = MeetingRepository.get_by_id(meeting_id)
        if meeting:
            if meeting.status == "done":
                self.meeting_form.hide()
                self.recording_panel.hide()
                self.note_editor.hide()
                self.minutes_viewer.show()
                self.minutes_viewer.load_meeting(meeting)
            elif meeting.status == "recording":
                self.meeting_form.hide()
                self.recording_panel.show()
                self.recording_panel.set_meeting(meeting)
                self.note_editor.show()
                self.note_editor.set_meeting(meeting)
                self.minutes_viewer.hide()
            else:
                self.meeting_form.show()
                self.meeting_form.load_meeting(meeting)
                self.recording_panel.hide()
                self.note_editor.hide()
                self.minutes_viewer.hide()

    def _on_new_meeting(self):
        """处理新建会议事件"""
        logger.info("新建会议")
        self.meeting_form.show()
        self.meeting_form.reset()
        self.recording_panel.hide()
        self.note_editor.hide()
        self.minutes_viewer.hide()

    def _on_start_recording(self, meeting_id: int):
        """处理开始录制事件"""
        logger.info(f"开始录制会议: {meeting_id}")
        from meet_conclusion.db.repositories import MeetingRepository
        meeting = MeetingRepository.get_by_id(meeting_id)
        if meeting:
            self.meeting_form.hide()
            self.recording_panel.show()
            self.recording_panel.start_recording(meeting)
            self.note_editor.show()
            self.note_editor.set_meeting(meeting)
            self.meeting_list.refresh()

    def _on_stop_recording(self, meeting_id: int):
        """处理停止录制事件"""
        logger.info(f"停止录制会议: {meeting_id}")
        self.recording_panel.stop()
        self.note_editor.hide()
        # 开始处理
        self._process_meeting(meeting_id)

    def _process_meeting(self, meeting_id: int):
        """处理会议（ASR + 纪要生成）"""
        logger.info(f"开始处理会议: {meeting_id}")
        # TODO: 实现会议处理流水线
        self.meeting_list.refresh()
