"""会议纪要查看组件"""

import json
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from meet_conclusion.db.models import Meeting
from meet_conclusion.db.repositories import NoteRepository, TranscriptRepository
from meet_conclusion.utils.logger import get_logger
from meet_conclusion.utils.time_utils import format_duration, format_timestamp

logger = get_logger(__name__)


class MinutesViewerWidget(QWidget):
    """会议纪要查看器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_meeting: Optional[Meeting] = None
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 会议信息头部
        self.header_widget = QWidget()
        header_layout = QVBoxLayout(self.header_widget)
        header_layout.setContentsMargins(0, 0, 0, 10)

        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        header_layout.addWidget(self.title_label)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet("font-size: 12px; color: #666;")
        header_layout.addWidget(self.info_label)

        layout.addWidget(self.header_widget)

        # 标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 摘要页
        self.summary_tab = QWidget()
        summary_layout = QVBoxLayout(self.summary_tab)
        self.summary_browser = QTextBrowser()
        self.summary_browser.setOpenExternalLinks(True)
        summary_layout.addWidget(self.summary_browser)
        self.tab_widget.addTab(self.summary_tab, "摘要")

        # 决策页
        self.decisions_tab = QWidget()
        decisions_layout = QVBoxLayout(self.decisions_tab)
        self.decisions_browser = QTextBrowser()
        decisions_layout.addWidget(self.decisions_browser)
        self.tab_widget.addTab(self.decisions_tab, "决策")

        # 行动项页
        self.actions_tab = QWidget()
        actions_layout = QVBoxLayout(self.actions_tab)
        self.actions_browser = QTextBrowser()
        actions_layout.addWidget(self.actions_browser)
        self.tab_widget.addTab(self.actions_tab, "行动项")

        # 议题详情页
        self.topics_tab = QWidget()
        topics_layout = QVBoxLayout(self.topics_tab)
        self.topics_browser = QTextBrowser()
        topics_layout.addWidget(self.topics_browser)
        self.tab_widget.addTab(self.topics_tab, "议题")

        # 转写文本页
        self.transcript_tab = QWidget()
        transcript_layout = QVBoxLayout(self.transcript_tab)
        self.transcript_browser = QTextBrowser()
        transcript_layout.addWidget(self.transcript_browser)
        self.tab_widget.addTab(self.transcript_tab, "转写")

        # 笔记页
        self.notes_tab = QWidget()
        notes_layout = QVBoxLayout(self.notes_tab)
        self.notes_browser = QTextBrowser()
        notes_layout.addWidget(self.notes_browser)
        self.tab_widget.addTab(self.notes_tab, "笔记")

    def load_meeting(self, meeting: Meeting):
        """加载会议数据"""
        self.current_meeting = meeting

        # 更新头部信息
        self.title_label.setText(meeting.title)

        info_parts = []
        info_parts.append(f"创建时间: {format_timestamp(meeting.created_at)}")
        if meeting.duration:
            info_parts.append(f"时长: {format_duration(meeting.duration)}")
        if meeting.participants:
            info_parts.append(f"参与人: {meeting.participants}")

        perspective_names = {
            "worker": "打工人",
            "manager": "管理者",
            "boss": "老板",
            "custom": "自定义",
        }
        info_parts.append(f"视角: {perspective_names.get(meeting.user_perspective, meeting.user_perspective)}")

        style_names = {
            "neutral": "中立客观",
            "sarcastic": "尖酸刻薄",
            "comforting": "安慰体贴",
        }
        info_parts.append(f"风格: {style_names.get(meeting.output_style, meeting.output_style)}")

        self.info_label.setText(" | ".join(info_parts))

        # 加载摘要
        self._load_summary(meeting)

        # 加载决策
        self._load_decisions(meeting)

        # 加载行动项
        self._load_actions(meeting)

        # 加载议题
        self._load_topics(meeting)

        # 加载转写
        self._load_transcript(meeting)

        # 加载笔记
        self._load_notes(meeting)

    def _load_summary(self, meeting: Meeting):
        """加载摘要"""
        if meeting.summary:
            self.summary_browser.setHtml(f"<div style='font-size: 14px; line-height: 1.8;'>{meeting.summary}</div>")
        else:
            self.summary_browser.setHtml("<p style='color: #999;'>暂无摘要</p>")

    def _load_decisions(self, meeting: Meeting):
        """加载决策"""
        if meeting.decisions_json:
            try:
                decisions = json.loads(meeting.decisions_json)
                html = "<ul style='font-size: 14px; line-height: 1.8;'>"
                for decision in decisions:
                    if isinstance(decision, dict):
                        html += f"<li><b>{decision.get('content', '')}</b>"
                        if decision.get('participants'):
                            html += f"<br><small style='color: #666;'>相关人员: {decision.get('participants')}</small>"
                        html += "</li>"
                    else:
                        html += f"<li>{decision}</li>"
                html += "</ul>"
                self.decisions_browser.setHtml(html)
            except json.JSONDecodeError:
                self.decisions_browser.setHtml(f"<p>{meeting.decisions_json}</p>")
        else:
            self.decisions_browser.setHtml("<p style='color: #999;'>暂无决策</p>")

    def _load_actions(self, meeting: Meeting):
        """加载行动项"""
        if meeting.action_items_json:
            try:
                actions = json.loads(meeting.action_items_json)
                html = "<ul style='font-size: 14px; line-height: 1.8;'>"
                for action in actions:
                    if isinstance(action, dict):
                        html += f"<li><b>{action.get('task', '')}</b>"
                        if action.get('assignee'):
                            html += f"<br><small style='color: #666;'>负责人: {action.get('assignee')}</small>"
                        if action.get('deadline'):
                            html += f"<br><small style='color: #666;'>截止时间: {action.get('deadline')}</small>"
                        html += "</li>"
                    else:
                        html += f"<li>{action}</li>"
                html += "</ul>"
                self.actions_browser.setHtml(html)
            except json.JSONDecodeError:
                self.actions_browser.setHtml(f"<p>{meeting.action_items_json}</p>")
        else:
            self.actions_browser.setHtml("<p style='color: #999;'>暂无行动项</p>")

    def _load_topics(self, meeting: Meeting):
        """加载议题"""
        if meeting.topics_json:
            try:
                topics = json.loads(meeting.topics_json)
                html = "<div style='font-size: 14px; line-height: 1.8;'>"
                for topic in topics:
                    if isinstance(topic, dict):
                        html += f"<h3>{topic.get('title', '议题')}</h3>"
                        html += f"<p>{topic.get('content', '')}</p>"
                    else:
                        html += f"<p>{topic}</p>"
                html += "</div>"
                self.topics_browser.setHtml(html)
            except json.JSONDecodeError:
                self.topics_browser.setHtml(f"<p>{meeting.topics_json}</p>")
        else:
            self.topics_browser.setHtml("<p style='color: #999;'>暂无议题</p>")

    def _load_transcript(self, meeting: Meeting):
        """加载转写文本"""
        transcripts = TranscriptRepository.get_by_meeting(meeting.id)
        if transcripts:
            html = "<div style='font-size: 14px; line-height: 1.8;'>"
            for t in transcripts:
                time_str = format_duration(t.start_time)
                speaker = t.speaker_id or "未知"
                html += f"<p><span style='color: #666;'>[{time_str}]</span> "
                html += f"<span style='color: #2196F3;'>{speaker}:</span> {t.text}</p>"
            html += "</div>"
            self.transcript_browser.setHtml(html)
        else:
            self.transcript_browser.setHtml("<p style='color: #999;'>暂无转写文本</p>")

    def _load_notes(self, meeting: Meeting):
        """加载笔记"""
        notes = NoteRepository.get_by_meeting(meeting.id)
        if notes:
            tag_icons = {
                "general": "📝",
                "todo": "✅",
                "risk": "⚠️",
                "question": "❓",
            }
            html = "<div style='font-size: 14px; line-height: 1.8;'>"
            for note in notes:
                time_str = format_duration(note.time_offset)
                icon = tag_icons.get(note.tag, "📝")
                html += f"<p>{icon} <span style='color: #666;'>[{time_str}]</span> {note.content}</p>"
            html += "</div>"
            self.notes_browser.setHtml(html)
        else:
            self.notes_browser.setHtml("<p style='color: #999;'>暂无笔记</p>")
