"""脱敏脚本关键边界：不误伤专业词，能清手机邮箱。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from anonymize_resumes import anonymize_text  # noqa: E402


def test_anonymize_keeps_major_and_strips_contacts():
    raw = """张三
手机：13800138000
邮箱：zhangsan@example.com
求职意向：数据分析实习生
教育背景
某某大学 软件工程
实习经历
某科技有限公司 数据分析实习：使用 Python 清洗数据，转化率提升 12%。
技能
Python、SQL、数据分析
"""
    out, stats = anonymize_text(raw)
    assert "13800138000" not in out
    assert "zhangsan@example.com" not in out
    assert "【手机号】" in out
    assert "【邮箱】" in out
    assert "数据分析" in out
    assert "软件工程" in out
    assert "Python" in out
    assert stats.get("phone", 0) >= 1
    assert stats.get("email", 0) >= 1


def test_anonymize_does_not_blank_whole_resume_as_names():
    raw = "教育背景\n人力资源管理\n专业技能\n沟通、组织、Office\n"
    out, _ = anonymize_text(raw)
    assert "人力资源管理" in out
    assert out.count("【姓名】") == 0
