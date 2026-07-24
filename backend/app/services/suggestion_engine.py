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
    if _is_new_media_context(match_result, evidence):
        suggestions.extend(_new_media_specific_suggestions(evidence))
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
        suggestions.append(
            f"把已有量化亮点前置，例如「{_shorten(evidence['sample_metric_lines'][0], 40)}」这类句子适合放在项目第一条。"
        )
    return _unique(suggestions)[:10] or ["当前简历基础较好，建议进一步围绕目标岗位强化关键词和量化成果。"]


def build_structured_suggestions(
    scores: dict[str, int],
    sections: dict[str, list[str]],
    match_result: dict[str, Any],
    parse_quality: str,
    evidence: dict[str, Any],
) -> list[dict[str, str]]:
    """证据约束建议：问题点 + 证据 + 影响 + 方向 + 示例。"""
    if parse_quality == "low":
        return [
            {
                "problem": "正文提取不足",
                "evidence": "系统未能稳定识别简历正文",
                "impact": "评分与建议可能严重偏离真实内容",
                "direction": "改用可选中复制的标准 DOCX 或文字版 PDF",
                "example": "在 Word 中另存为 .docx，或导出「可搜索文本」PDF 后重新上传",
            }
        ]

    items: list[dict[str, str]] = []
    target_label = match_result.get("target_position") or "目标岗位"
    if _is_new_media_context(match_result, evidence):
        _append_new_media_structured(items, evidence, target_label)

    for line in evidence.get("weak_experience_lines", [])[:2]:
        sample = _shorten(line, 40)
        items.append(
            {
                "problem": "经历描述缺少结果闭环",
                "evidence": sample,
                "impact": f"招聘方难以判断你在{target_label}相关任务中的实际贡献",
                "direction": "按「背景/任务 → 行动 → 量化结果」重写",
                "example": f"原句「{sample}」→「负责…，通过…方法，完成…，带来…%提升/…次转化」",
            }
        )

    for keyword in (match_result.get("missing_keywords") or [])[:3]:
        items.append(
            {
                "problem": f"缺少岗位关键词「{keyword}」",
                "evidence": "JD 或岗位画像要求中出现，但简历正文未体现",
                "impact": "语义匹配与 ATS 筛选通过率下降",
                "direction": "把关键词写入项目/实习经历，而非只堆在技能栏",
                "example": f"在项目描述中加入「使用 {keyword} 完成…，产出…」",
            }
        )

    for snippet in match_result.get("evidence_snippets") or []:
        if sum(1 for item in items if str(item.get("problem", "")).startswith("已匹配关键词")) >= 2:
            break
        items.append(
            {
                "problem": f"已匹配关键词「{snippet.get('keyword', '')}」",
                "evidence": snippet.get("text", ""),
                "impact": "这是当前简历中与岗位要求最相关的证据之一",
                "direction": "把此类证据前置到经历第一条，并补充量化结果",
                "example": "在该段经历开头直接写出关键词与核心成果",
            }
        )
        if len(items) >= 6:
            break

    if evidence.get("metric_line_count", 0) < 2:
        items.append(
            {
                "problem": "量化成果偏少",
                "evidence": f"仅识别到 {evidence.get('metric_line_count', 0)} 条带数字/比例的表述",
                "impact": "同类候选人中亮点说服力不足",
                "direction": "为每段核心经历至少补充 1 个可验证指标",
                "example": "阅读量 10w+、转化率提升 15%、处理 2 万条数据、完播率 35%",
            }
        )

    for key, score in scores.items():
        if score < 60 and len(items) < 8:
            weak_line = ""
            if key == "experience_match" and evidence.get("weak_experience_lines"):
                weak_line = _shorten(evidence["weak_experience_lines"][0], 36)
            elif key == "highlight_strength":
                weak_line = f"量化表达仅 {evidence.get('metric_line_count', 0)} 条"
            elif key == "job_match" and match_result.get("missing_keywords"):
                weak_line = f"缺少：{'、'.join(match_result['missing_keywords'][:3])}"
            items.append(
                {
                    "problem": f"{label_for_score(key)}得分偏低（{score}）",
                    "evidence": weak_line or f"{label_for_score(key)}维度规则评分 {score} 分",
                    "impact": "会拉低综合得分与岗位匹配判断",
                    "direction": "优先补齐该维度对应模块的内容与证据",
                    "example": "参见优化改写 Tab 中的 STAR 成稿参考",
                }
            )

    return items[:8] or [
        {
            "problem": "整体结构较完整",
            "evidence": "核心模块与岗位关键词已有一定覆盖",
            "impact": "可继续微调以提升投递竞争力",
            "direction": "围绕目标岗位强化量化成果与关键词密度",
            "example": "上传新版本后可使用版本对比查看分数变化",
        }
    ]


def build_action_roadmap(
    scores: dict[str, int],
    structured_suggestions: list[dict[str, str]],
    match_result: dict[str, Any],
    parse_quality: str,
    missing_sections: list[str],
    diagnosis: list[str],
) -> list[dict[str, str]]:
    """生成概览页优先行动清单（最多 5 条）。"""
    roadmap: list[dict[str, str]] = []

    if parse_quality == "low":
        roadmap.append(
            {
                "priority": "urgent",
                "title": "修复文件解析",
                "detail": "正文提取不足，当前评分仅供参考，请更换标准 DOCX/PDF 后重新分析",
                "action_tab": "diagnosis",
            }
        )

    if missing_sections:
        labels = [SECTION_LABELS.get(key, key) for key in missing_sections[:3]]
        roadmap.append(
            {
                "priority": "high",
                "title": f"补齐核心板块：{'、'.join(labels)}",
                "detail": "缺失板块会拉低完整性评分，建议补充对应经历或技能描述",
                "action_tab": "parse",
            }
        )

    for item in structured_suggestions[:2]:
        problem = str(item.get("problem", "")).strip()
        if not problem or problem.startswith("已匹配关键词"):
            continue
        roadmap.append(
            {
                "priority": "high",
                "title": problem,
                "detail": str(item.get("direction", "")).strip() or str(item.get("impact", "")).strip(),
                "action_tab": "diagnosis",
            }
        )

    missing_kw = match_result.get("missing_keywords") or []
    if missing_kw and len(roadmap) < 5:
        target = match_result.get("target_position") or "目标岗位"
        roadmap.append(
            {
                "priority": "medium",
                "title": f"补充{target}关键词",
                "detail": f"建议写入项目/实习经历：{'、'.join(missing_kw[:5])}",
                "action_tab": "match",
            }
        )

    if scores:
        weak_score_key = min(scores, key=lambda key: scores.get(key, 100))
        if scores.get(weak_score_key, 100) < 65 and len(roadmap) < 5:
            roadmap.append(
                {
                    "priority": "medium",
                    "title": f"提升{label_for_score(weak_score_key)}",
                    "detail": f"当前 {scores[weak_score_key]} 分，可参考优化改写中的 STAR 成稿",
                    "action_tab": "enhance",
                }
            )

    if not roadmap and diagnosis:
        roadmap.append(
            {
                "priority": "medium",
                "title": "查看诊断建议",
                "detail": _shorten(diagnosis[0], 60),
                "action_tab": "diagnosis",
            }
        )

    return roadmap[:5]


def _is_new_media_context(match_result: dict[str, Any], evidence: dict[str, Any]) -> bool:
    profile = str(match_result.get("profile") or "")
    target = str(match_result.get("target_position") or "")
    combined = f"{profile} {target} {' '.join(evidence.get('domain_keywords') or [])}"
    return any(token in combined for token in ["新媒体", "内容运营", "小红书", "公众号", "短视频", "淘宝运营", "SEO", "SEM"])


def _new_media_specific_suggestions(evidence: dict[str, Any]) -> list[str]:
    keywords = evidence.get("domain_keywords") or []
    keyword_text = "、".join(keywords[:6]) if keywords else "新媒体平台、内容选题、账号运营"
    course_line = _primary_new_media_line(evidence)
    suggestions = [
        f"当前新媒体相关证据主要集中在「{_shorten(course_line, 48)}」，建议补 1 个真实账号/课程项目案例：写清平台、目标人群、选题方向、发布频次和最终数据。",
        f"把已识别到的{keyword_text}从课程或技能词改成产出描述，例如“围绕__人群策划__篇笔记/短视频，使用 PS/PR/AE 完成封面与剪辑，带来曝光__、互动__、涨粉__”。",
    ]
    if not any(token in " ".join(evidence.get("domain_signal_lines") or []) for token in ["阅读量", "播放量", "涨粉", "互动率", "完播率", "转化率"]):
        suggestions.append("新媒体运营建议至少补 2 类指标：内容传播指标（阅读量/播放量/完播率/互动率）和运营结果指标（涨粉/收藏/转化/咨询）。")
    return suggestions


def _append_new_media_structured(items: list[dict[str, str]], evidence: dict[str, Any], target_label: str) -> None:
    course_line = _primary_new_media_line(evidence)
    keywords = evidence.get("domain_keywords") or []
    keyword_text = "、".join(keywords[:6]) if keywords else "新媒体运营、内容策划、账号运营"
    items.append(
        {
            "problem": "新媒体岗位证据停留在课程/关键词层面",
            "evidence": _shorten(course_line, 70),
            "impact": f"能说明学过{target_label}相关工具和方法，但还不能证明账号运营产出",
            "direction": "补充 1 个账号、活动或课程项目案例，按平台、目标人群、动作、数据结果展开",
            "example": "运营小红书/公众号账号，围绕__人群策划__篇内容，完成选题、文案、封面和发布，累计曝光__、互动__、涨粉__。",
        }
    )
    items.append(
        {
            "problem": "缺少新媒体核心数据",
            "evidence": "未稳定识别到阅读量、播放量、涨粉、互动率、完播率或转化率等指标",
            "impact": "运营岗位会更看重内容效果与复盘能力，只有课程名会显得说服力不足",
            "direction": "为每段内容运营经历补充 1-2 个可验证指标，并说明数据来自哪次活动或哪个账号",
            "example": "发布__篇短视频/笔记，平均播放__，互动率__%，通过标题关键词和封面优化使收藏量提升__%。",
        }
    )
    if any(token in keyword_text for token in ["SEO", "SEM", "淘宝运营", "网络整合营销", "推广"]):
        items.append(
            {
                "problem": "电商/搜索营销关键词没有转化成项目成果",
                "evidence": keyword_text,
                "impact": "这些词与新媒体运营高度相关，但只出现在课程中时无法体现执行能力",
                "direction": "补一条搜索或电商内容优化案例，写清关键词、标题/主图/投放动作和转化结果",
                "example": "基于 SEO/SEM 思路优化标题关键词与推广文案，配合淘宝运营活动完成__次内容发布，带来点击__、咨询__或转化__。",
            }
        )


def _primary_new_media_line(evidence: dict[str, Any]) -> str:
    for line in evidence.get("course_lines") or []:
        return line
    for line in evidence.get("domain_signal_lines") or []:
        return line
    return "已识别到新媒体运营相关关键词，但缺少项目化描述"


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
