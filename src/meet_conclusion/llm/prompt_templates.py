"""Prompt 模板模块

定义不同视角和风格的 Prompt 模板
"""

from typing import Optional

# 系统基础 Prompt
SYSTEM_BASE = """你是一位专业的会议纪要助手。你需要根据会议转写文本和用户笔记，生成结构化的会议纪要。

你的输出必须包含以下部分：
1. 会议摘要：1-3段文字，概括会议的核心内容和结论
2. 决策列表：列出会议中做出的重要决策
3. 行动项列表：列出需要跟进的任务，包括负责人和截止时间（如果有）
4. 议题详情：按主题分块的详细纪要

输出格式要求：
- 使用 JSON 格式输出
- 结构如下：
{
  "summary": "会议摘要文本",
  "decisions": [
    {"content": "决策内容", "participants": "相关人员"}
  ],
  "action_items": [
    {"task": "任务描述", "assignee": "负责人", "deadline": "截止时间"}
  ],
  "topics": [
    {"title": "议题标题", "content": "议题详细内容"}
  ]
}
"""

# 视角 Prompt 模板
PERSPECTIVE_PROMPTS = {
    "worker": """
你需要从打工人的视角来分析和总结这场会议。请特别关注：
- 具体需要完成的任务和交付物
- 时间节点和deadline
- 潜在的背锅风险和推诿情况
- 上级的明确要求和隐含期望
- 加班信号和工作量预估
- 需要跨部门协调的事项
- 可能影响自己绩效的关键点
""",

    "manager": """
你需要从管理者的视角来分析和总结这场会议。请特别关注：
- 项目整体推进状态和风险
- 资源分配和人员调度
- 跨部门协同和依赖关系
- 向上汇报的关键信息
- 团队成员的任务分配
- 潜在的问题和风险预警
- 需要做出的管理决策
""",

    "boss": """
你需要从老板/高管的视角来分析和总结这场会议。请特别关注：
- ROI 和投资回报
- 关键业务决策和战略影响
- 成本 vs 收益分析
- 重要的商业机会或风险
- 需要高层关注的问题
- 长期战略一致性
- 组织和人才方面的观察
""",

    "custom": """
你需要根据用户自定义的视角来分析和总结这场会议。

用户自定义的关注点：
{custom_perspective}

请根据上述关注点，有针对性地分析会议内容。
"""
}

# 风格 Prompt 模板
STYLE_PROMPTS = {
    "neutral": """
输出风格要求：中立客观
- 使用报告体风格，语言正式、准确
- 客观陈述事实，避免主观评价
- 保持专业和中性的语气
- 重点突出、条理清晰
""",

    "sarcastic": """
输出风格要求：尖酸刻薄
- 直接指出问题和风险，不打太极
- 语言简洁犀利，一针见血
- 可以适度吐槽，但要有理有据
- 暴露会议中的低效和扯皮
- 对"画饼"和"打官腔"的内容不客气
- 保持专业，吐槽有度
""",

    "comforting": """
输出风格要求：安慰体贴
- 语气温和、有同理心
- 适度缓冲负面内容
- 强调积极面和已取得的进展
- 给出建设性的建议
- 对压力和挑战表示理解
- 鼓励团队并提供支持性观点
"""
}


def build_system_prompt(
    perspective: str = "worker",
    style: str = "neutral",
    custom_perspective: Optional[str] = None,
) -> str:
    """构建系统 Prompt

    Args:
        perspective: 视角 (worker/manager/boss/custom)
        style: 风格 (neutral/sarcastic/comforting)
        custom_perspective: 自定义视角描述

    Returns:
        完整的系统 Prompt
    """
    parts = [SYSTEM_BASE]

    # 添加视角 Prompt
    perspective_prompt = PERSPECTIVE_PROMPTS.get(perspective, PERSPECTIVE_PROMPTS["worker"])
    if perspective == "custom" and custom_perspective:
        perspective_prompt = perspective_prompt.format(custom_perspective=custom_perspective)
    parts.append(perspective_prompt)

    # 添加风格 Prompt
    style_prompt = STYLE_PROMPTS.get(style, STYLE_PROMPTS["neutral"])
    parts.append(style_prompt)

    return "\n".join(parts)


def build_user_prompt(
    transcript_text: str,
    notes: list[dict],
    meeting_info: Optional[dict] = None,
) -> str:
    """构建用户 Prompt

    Args:
        transcript_text: 转写文本
        notes: 用户笔记列表，每项包含 time_offset, content, tag
        meeting_info: 会议信息，包含 title, participants 等

    Returns:
        用户 Prompt
    """
    parts = []

    # 会议信息
    if meeting_info:
        parts.append("## 会议信息")
        if meeting_info.get("title"):
            parts.append(f"标题：{meeting_info['title']}")
        if meeting_info.get("participants"):
            parts.append(f"参与人：{meeting_info['participants']}")
        parts.append("")

    # 转写文本
    parts.append("## 会议转写文本")
    parts.append(transcript_text)
    parts.append("")

    # 用户笔记
    if notes:
        parts.append("## 用户笔记")
        parts.append("（以下是用户在会议中标记的重要内容，请在纪要中重点体现）")
        parts.append("")

        tag_names = {
            "todo": "TODO",
            "risk": "风险",
            "question": "问题",
            "general": "笔记",
        }

        for note in notes:
            time_offset = note.get("time_offset", 0)
            minutes = int(time_offset // 60)
            seconds = int(time_offset % 60)
            tag = tag_names.get(note.get("tag", "general"), "笔记")
            content = note.get("content", "")
            parts.append(f"- [{minutes:02d}:{seconds:02d}] [{tag}] {content}")

        parts.append("")

    # 请求
    parts.append("请根据以上内容生成会议纪要，以 JSON 格式输出。")

    return "\n".join(parts)
