"""教师端：基于班级共性问题生成「一键成课」训练任务。"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import AnalysisRecord, User, UserProfile
from app.services.teacher_class_stats import class_label
from app.utils.json_tools import loads


_TEMPLATE_BANK: list[dict[str, str]] = [
    {
        "pattern": r"量化|指标|数据|百分比|提升",
        "title": "项目量化表达专项训练",
        "goal": "把经历从「做了什么」改成「做成了什么」",
        "tasks": "1) 为每段实习/项目补充 1 个可验证数字；2) 用「动作+方法+结果」重写 3 句；3) 上传新版本复测亮点量化分。",
        "checklist": "是否出现人数/比例/周期/次数；是否避免「很多/比较」空泛词。",
    },
    {
        "pattern": r"关键词|岗位匹配|缺失|技能",
        "title": "岗位关键词对齐训练",
        "goal": "让简历技能与目标 JD 同频",
        "tasks": "1) 对照目标岗位列出 8 个核心词；2) 在技能/项目中自然融入已掌握词；3) 对未掌握词标注学习计划而非编造。",
        "checklist": "已掌握词出现在项目证据中；未掌握词不虚构。",
    },
    {
        "pattern": r"STAR|结构|空泛|专业表达|润色|低信噪比|置信度",
        "title": "STAR 经历改写训练",
        "goal": "用情境-任务-行动-结果写清贡献",
        "tasks": "1) 选 2 段经历套 STAR；2) 每段不超过 2 句；3) 对比优化稿 Diff 后定稿。",
        "checklist": "有背景、有行动、有结果；无编造数据。",
    },
    {
        "pattern": r"格式|排版|模块|完整",
        "title": "简历结构规范化训练",
        "goal": "保证教育/实习/项目/技能模块齐全清晰",
        "tasks": "1) 按标准标题重排；2) 删除无关课程堆砌；3) 导出优化稿检查模块完整性分。",
        "checklist": "标题统一；联系方式完整；模块不缺失。",
    },
]


def build_training_task_from_issue(
    issue: str,
    *,
    class_name: str = "",
    affected_count: int = 0,
    total_records: int = 0,
) -> dict[str, Any]:
    text = (issue or "").strip()
    template = _TEMPLATE_BANK[-1]
    for item in _TEMPLATE_BANK:
        if re.search(item["pattern"], text):
            template = item
            break
    coverage = round(affected_count / max(total_records, 1) * 100, 1) if total_records or affected_count else 0.0
    student_message = (
        f"【班级训练任务】{template['title']}\n"
        f"共性问题：{text}\n"
        f"训练目标：{template['goal']}\n"
        f"本周任务：{template['tasks']}\n"
        f"验收标准：{template['checklist']}\n"
        "完成后请上传简历新版本，系统将自动对比分数变化。"
    )
    return {
        "title": template["title"],
        "source_issue": text,
        "class_name": class_name or "全年级/未分班汇总",
        "affected_count": affected_count,
        "coverage_percent": coverage,
        "goal": template["goal"],
        "tasks": template["tasks"],
        "checklist": template["checklist"],
        "student_message": student_message,
        "privacy_note": "仅推送聚合短板与训练模板，不包含任何学生简历正文。",
    }


def create_class_training_task(
    db: Session,
    *,
    issue: str,
    class_name: str = "",
) -> dict[str, Any]:
    issue_text = (issue or "").strip()
    if not issue_text:
        raise ValueError("请先选择一条共性问题。")

    rows = (
        db.query(AnalysisRecord, UserProfile)
        .join(User, User.id == AnalysisRecord.user_id)
        .join(UserProfile, UserProfile.user_id == User.id)
        .filter(AnalysisRecord.status == "success")
        .all()
    )
    matched = 0
    total = 0
    for record, profile in rows:
        label = class_label(profile)
        if class_name and label != class_name:
            continue
        total += 1
        diagnosis = loads(record.diagnosis_json, [])
        if not isinstance(diagnosis, list):
            continue
        if any(issue_text == str(item).strip() or issue_text in str(item) for item in diagnosis):
            matched += 1

    task = build_training_task_from_issue(
        issue_text,
        class_name=class_name,
        affected_count=matched,
        total_records=total or matched,
    )
    task["push_mode"] = "template_broadcast"
    task["status"] = "ready"
    return task
