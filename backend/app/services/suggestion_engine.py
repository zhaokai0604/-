"""建议与诊断引擎：基于评分证据生成可执行建议。"""

from __future__ import annotations

from typing import Any

from app.services.score_engine import SECTION_LABELS, label_for_score


def build_diagnosis(
    scores: dict[str, int],
    sections: dict[str, list[str]],
    match_result: dict[str, Any],
    warnings: list[str],
    parse_quality: str,
    evidence: dict[str, Any],
) -> list[str]:
    diagnosis = list(dict.fromkeys(warnings))
    if parse_quality == "low":
        diagnosis.append("当前文件正文提取不足，评分仅供参考；请优先确认文件是否为图片版、特殊模板或损坏文件。")
        return diagnosis

    missing_labels = [SECTION_LABELS[key] for key in evidence["missing_sections"]]
    if missing_labels:
        diagnosis.append(f"结构完整性不足：未明显识别到{'、'.join(missing_labels)}，会影响系统对能力证据的判断。")
    if evidence["experience_line_count"] and evidence["metric_line_count"] == 0:
        diagnosis.append("经历描述缺少量化结果，当前更像职责罗列，亮点说服力不足。")
    elif evidence["metric_line_count"]:
        diagnosis.append(f"已识别到 {evidence['metric_line_count']} 条量化表达，可继续把数据结果前置到每段经历中。")
    if evidence["weak_experience_lines"]:
        diagnosis.append(f"部分经历缺少结果闭环，例如“{_shorten(evidence['weak_experience_lines'][0])}”。")
    if evidence["vague_lines"]:
        diagnosis.append(f"存在泛化表述，例如“{_shorten(evidence['vague_lines'][0])}”，建议换成可验证的事实。")
    if evidence["long_lines"]:
        diagnosis.append("部分行文字过长，建议拆成“任务、行动、结果”三点，提升可读性。")
    if match_result.get("target_source") == "detected" and match_result.get("target_position"):
        diagnosis.append(f"已从简历中识别到求职意向：{match_result['target_position']}。")
    if match_result.get("missing_keywords"):
        diagnosis.append(f"目标岗位关键词覆盖不足，优先补充：{'、'.join(match_result['missing_keywords'][:6])}。")
    for key, score in scores.items():
        if score < 60:
            diagnosis.append(f"{label_for_score(key)}明显偏弱，当前分数 {score}，需要优先优化。")
    return _unique(diagnosis) or ["简历基础结构较完整，可以继续强化量化成果和岗位关键词。"]


def build_suggestions(
    scores: dict[str, int],
    sections: dict[str, list[str]],
    match_result: dict[str, Any],
    parse_quality: str,
    evidence: dict[str, Any],
) -> list[str]:
    if parse_quality == "low":
        return [
            "请优先检查文件版式：若简历是图片版、扫描版或大量文本框模板，建议另存为标准 DOCX 或导出清晰 PDF 后重新上传。",
            "在重新上传前，可确认正文文字能在 Word/PDF 中被鼠标选中复制；如果不能复制，系统也很难稳定识别。",
        ]

    suggestions: list[str] = []
    if evidence["missing_sections"]:
        suggestions.append(_missing_section_suggestion(evidence["missing_sections"]))
    if evidence["weak_experience_lines"]:
        sample = _shorten(evidence["weak_experience_lines"][0], 34)
        suggestions.append(f"把经历从职责描述改成成果描述。示例：原句“{sample}”可改为“负责/参与 X 工作，使用 Y 方法完成 Z，最终带来 N 项成果或提升 N%”。")
    elif scores["experience_match"] < 78:
        suggestions.append("经历模块建议至少补充 2-3 条 STAR 表达：背景/任务、具体行动、量化结果，避免只写岗位职责。")
    if evidence["metric_line_count"] < 2:
        suggestions.append("补充量化指标：如阅读量、播放量、涨粉数、转化率、处理数据量、完成页面/接口数量、活动参与人数等。")
    if evidence["vague_lines"]:
        suggestions.append("替换“熟悉、良好、较强、很多”等泛化词，改成工具熟练度、作品数量、证书等级或实际产出。")
    if evidence["long_lines"]:
        suggestions.append("格式上把过长段落拆成项目符号，每条控制在一行半以内，并按“动作 + 方法 + 结果”排序。")
    if match_result.get("target_source") == "generic":
        suggestions.append("简历中未识别到明确求职意向，建议补充“求职意向/目标岗位”，否则岗位匹配只能按通用规则判断。")
    if match_result.get("focus_suggestions"):
        suggestions.extend(f"围绕目标岗位强化：{item}。" for item in match_result["focus_suggestions"][:3])
    missing = match_result.get("missing_keywords") or []
    if missing:
        target_label = match_result.get("target_position") or "目标岗位"
        suggestions.append(f"围绕{target_label}补充关键词：{'、'.join(missing[:8])}，并尽量放进项目或实习经历，而不是只堆在技能栏。")
    if sections.get("skills") and scores["job_match"] < 70:
        suggestions.append("技能栏建议按“岗位相关技能 / 工具软件 / 证书荣誉”分组，把与目标岗位最相关的技能放在最前。")
    if sections.get("projects") and evidence["sample_metric_lines"]:
        suggestions.append(f"把已有量化亮点前置，例如“{_shorten(evidence['sample_metric_lines'][0], 40)}”这类句子适合放在项目第一条。")
    for snippet in match_result.get("evidence_snippets") or []:
        suggestions.append(f"已匹配关键词「{snippet['keyword']}」的证据：{snippet['text']}")
        if len(suggestions) >= 10:
            break
    return _unique(suggestions)[:10] or ["当前简历基础较好，建议进一步围绕目标岗位强化关键词和量化成果。"]


def _missing_section_suggestion(missing_sections: list[str]) -> str:
    labels = [SECTION_LABELS[key] for key in missing_sections]
    examples = []
    if "internship" in missing_sections:
        examples.append("没有正式实习也可以写课程实践、社团运营、兼职或志愿服务中的岗位相关任务")
    if "projects" in missing_sections:
        examples.append("项目经历建议写课程项目、实训作品、账号运营案例或作品集")
    if "skills" in missing_sections:
        examples.append("技能证书建议列工具、软件、语言能力和职业证书")
    detail = "；".join(examples)
    return f"优先补齐{'、'.join(labels)}模块。{detail}。" if detail else f"优先补齐{'、'.join(labels)}模块。"


def _shorten(text: str, limit: int = 46) -> str:
    import re

    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))
