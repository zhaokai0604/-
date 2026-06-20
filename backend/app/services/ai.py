import json
import re
from typing import Any

import requests

from app.services.runtime_config import get_ai_runtime_config


def enhance_with_deepseek(result: dict[str, Any], resume_text: str, enable_ai: bool) -> tuple[dict[str, Any], str]:
    ai_config = get_ai_runtime_config()
    if not enable_ai:
        return result, "offline"
    if not ai_config["api_key"]:
        result["ai_fallback_reason"] = "未配置 DEEPSEEK_API_KEY，已自动使用离线规则分析。"
        return result, "offline_fallback"
    target_position = (result.get("target_position") or "").strip()
    target_source = result.get("target_position_source", "generic")
    source_label = {
        "manual": "手动输入岗位",
        "detected": "简历识别岗位",
        "generic": "通用建议",
    }.get(target_source, "通用建议")
    prompt = (
        "你是高校学生简历优化专家。请基于现有规则评分结果，输出更具体的诊断和修改建议。"
        "要求只返回 JSON，不要 Markdown 代码块。字段为 diagnosis 和 suggestions，值为字符串数组。"
        "如果本次已有目标岗位，请严格围绕该岗位给出针对性建议；"
        "如果目标岗位来源是手动输入，则必须以手动输入为准；"
        "如果没有目标岗位，则按通用求职建议输出。\n\n"
        f"本次采用岗位：{target_position or '无'}\n"
        f"岗位来源：{source_label}\n\n"
        f"规则结果：{result}\n\n简历文本：{resume_text[:6000]}"
    )
    try:
        response = requests.post(
            ai_config["api_url"],
            headers={"Authorization": f"Bearer {ai_config['api_key']}", "Content-Type": "application/json"},
            json={
                "model": ai_config["model"],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            },
            timeout=20,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        result["ai_fallback_reason"] = f"DeepSeek 调用失败，已自动使用离线规则分析：{exc}"
        return result, "offline_fallback"

    try:
        enhanced = _parse_deepseek_json(content)
    except json.JSONDecodeError:
        result["ai_fallback_reason"] = "DeepSeek 返回内容不是有效 JSON，已自动使用离线规则分析。"
        return result, "offline_fallback"
    if isinstance(enhanced.get("diagnosis"), list):
        result["diagnosis"] = enhanced["diagnosis"]
    if isinstance(enhanced.get("suggestions"), list):
        result["suggestions"] = enhanced["suggestions"]
    return result, "deepseek"


def _parse_deepseek_json(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.S)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    return json.loads(cleaned)
