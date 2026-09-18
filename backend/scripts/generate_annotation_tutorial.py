"""Generate the beginner-friendly UTF-8 annotation tutorial."""

from __future__ import annotations

import time
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "testing" / "实验数据标注详细教程.docx"


def main() -> int:
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)
    doc.styles["Normal"].font.name = "Microsoft YaHei"
    doc.styles["Normal"].font.size = Pt(10.5)

    title = doc.add_heading("简析智评实验数据标注详细教程", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub = doc.add_paragraph("面向第一次做数据标注的项目成员　|　UTF-8　|　Windows 操作步骤")
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def h(text: str, level: int = 1) -> None:
        doc.add_heading(text, level)

    def p(text: str = "") -> None:
        doc.add_paragraph(text)

    def code(text: str) -> None:
        item = doc.add_paragraph()
        item.style = "No Spacing"
        run = item.add_run(text)
        run.font.name = "Consolas"
        run.font.size = Pt(9)

    def table(headers: list[str], rows: list[list[str]]) -> None:
        t = doc.add_table(rows=1, cols=len(headers))
        t.style = "Table Grid"
        for cell, value in zip(t.rows[0].cells, headers):
            cell.text = value
        for row in rows:
            cells = t.add_row().cells
            for cell, value in zip(cells, row):
                cell.text = value

    p("这份教程只介绍一种推荐做法：使用项目自带的本地标注工具完成标注，不需要手工编写 JSON。你只需要阅读脱敏简历、勾选板块、选择质量等级、填写备注，最后点击导出。")
    p("最重要的原则：标注是给系统准备‘正确答案’，不是凭感觉给系统打高分。先独立阅读脱敏文本，再使用工具填写标签；不能根据系统当前预测结果反推 gold 标签。")

    h("一、先分清四类数据", 1)
    table(["数据", "协作包内位置", "数量/状态", "用途"], [
        ["脱敏数据集 A", "数据集_标注员A", "59 份 TXT", "标注员 A 使用"],
        ["脱敏数据集 B", "数据集_标注员B", "59 份 TXT，与 A 内容相同", "标注员 B 使用"],
        ["标注工具", "标注工具.html", "本地浏览器工具", "勾选板块并导出 JSON"],
        ["标注结果模板", "标注结果/real_parse_annotations.template.json", "字段模板", "查看导出字段"],
        ["已有首轮初标", "标注结果/已有首轮初标_仅供参考.json", "15 条", "仅供参考，不是最终答案"],
        ["评测与辅助脚本", "脚本", "9 个", "由负责人统一运行和汇总"],
    ])
    p("组员只接触协作包内两套脱敏 TXT，不需要接触原始 DOCX/PDF，也不需要访问项目源码。文件名已统一为 resume-001.txt 等匿名名称。")

    h("二、先找到标注工具", 1)
    p("标注工具是一个可以直接用浏览器打开的本地 HTML 文件，不需要安装软件、不需要启动后端、不需要联网。")
    code(r"当前协作包\\标注工具.html")
    p("在资源管理器中双击这个 HTML 文件。如果浏览器提示选择打开方式，选择 Edge 或 Chrome。打开后看到‘简析智评 | 真实简历板块标注’标题，就说明工具启动成功。工具页面明确显示‘只在本地浏览器处理脱敏 TXT，不上传文件’。")
    p("工具使用 UTF-8 读取和导出中文。不要用 Word、Excel 或记事本另存工具文件，也不要修改 HTML 文件编码。")

    h("三、标注前的准备", 1)
    p("组员不需要安装 Python、不需要启动后端、不需要运行脚本。只需要保留整个协作包的文件夹结构，并双击包内的标注工具。")
    p("如果浏览器提示选择打开方式，选择 Edge 或 Chrome。首次打开后，先确认页面显示‘简析智评 | 真实简历板块标注’。")

    h("四、解析标注到底标什么", 1)
    p("解析标注只判断‘这份文本中有哪些板块’，不评价简历好不好。允许使用的 8 个标签如下：")
    table(["标签", "什么时候填写", "典型内容"], [
        ["basic_info", "出现姓名、联系方式、求职意向、基本资料", "求职意向、邮箱、所在地"],
        ["education", "出现学校、学历、专业、课程、教育经历", "某大学、本科、计算机科学"],
        ["internship", "出现公司实习、工作、岗位实践", "公司实习生、负责日常运营"],
        ["projects", "出现项目、作品、系统、毕业设计、科研项目", "校园小程序、数据分析项目"],
        ["campus", "出现学生会、社团、志愿、班委、校园活动", "学生会部长、志愿服务"],
        ["skills", "出现专业技能、工具、语言、证书技能", "Python、Excel、英语、剪映"],
        ["awards", "出现获奖、奖学金、荣誉、资格证书", "校级奖学金、英语六级"],
        ["summary", "出现自我评价、个人优势、职业目标", "细致负责、学习能力强"],
    ])
    p("填写规则：有明确内容就填；只有标题没有正文时不要仅因为标题存在就填；标题缺失但正文语义明确时仍然填；完全无法判断时不填。")
    p("例如：文本里出现‘教育背景’并有‘某大学 本科’，填写 education。文本里只有‘技能’两个字，没有任何技能内容，不填写 skills。")

    h("五、使用工具完成一份标注", 1)
    p("1. 标注员 A 点击页面顶部的‘导入脱敏 TXT’，选择本协作包内‘数据集_标注员A’文件夹中的全部 TXT；标注员 B 选择‘数据集_标注员B’文件夹中的全部 TXT。")
    p("2. 页面左侧显示当前脱敏简历正文。先从头到尾阅读一遍，再看右侧选项。文件名、正文和标签都只在本地浏览器内处理。")
    p("3. 在‘人工标注’区域勾选文本中确实出现且有正文的 8 个板块。只有标题没有内容时不要勾选；标题缺失但正文语义明确时仍然勾选。")
    p("4. 选择‘解析质量’：high 表示正文清楚；medium 表示有碎片或 OCR 噪声；low 表示正文缺失较多，无法可靠判断。它评价的是机器能否读懂文本，不是简历写得好不好。")
    p("5. 选择‘简历内容质量’ 1-5 分。1 分表示内容非常薄弱，5 分表示内容完整、有证据、有量化成果。它评价简历本身，不是解析结果。")
    p("6. 勾选实际存在的问题类型，可多选。没有观察到的问题不要勾选；不确定时在备注中说明，不要为了让结果更好看而少报问题。")
    p("7. 在备注中写简短证据，例如‘项目标题存在，但项目正文被 OCR 拆散’。不要写真实姓名、电话、邮箱或完整学校名称。")
    p("8. 点击‘保存当前’，再点击‘下一份’。切换上一份或下一份时工具会自动保存当前标签，但建议每份都明确点击一次‘保存当前’。")
    p("9. 全部完成后点击‘导出 UTF-8 JSON’，浏览器会下载 real_parse_annotations.json。这个文件就是评测输入，不需要你再打开修改。")
    table(["工具区域", "你要做什么", "不要做什么"], [
        ["导入脱敏 TXT", "选择 anonymized_ocr 或 A 池 TXT", "不要选择原始 PDF/DOCX"],
        ["简历正文", "独立阅读并寻找板块证据", "不要依据系统预测反推标签"],
        ["8 个板块", "勾选有实际正文的板块", "不要把空标题当成板块"],
        ["解析质量", "判断文本可读和板块可识别程度", "不要把简历好坏代入"],
        ["简历内容质量", "按内容完整性打 1-5 分", "不要当成解析准确率"],
        ["问题和备注", "记录真实问题和证据", "不要写敏感信息"],
        ["导出 JSON", "完成全部样本后导出", "不要用 Excel 另存"],
    ])

    h("六、导出结果怎么看", 1)
    p("工具会自动生成 id、gold_sections、parse_quality、resume_quality、issue_types、notes 等字段，并把导入的脱敏正文写入 text。你不需要手工填写这些字段。")
    p("导出的文件默认名是 real_parse_annotations.json。导出后立刻改名：标注员 A 改为 real_parse_annotations_A.json，标注员 B 改为 real_parse_annotations_B.json，并放入本协作包的‘标注结果’文件夹。")
    p("导出文件中的 label_policy 会标记为 independent_two_annotator_annotation，表示这是独立双人标注结果。两人的文件必须分别保存，不能互相覆盖。")
    p("只有在确实需要修复文件名、补充实验元数据或处理工具异常时，才由开发者在代码中修改 JSON；普通标注不要手工编辑 JSON。")

    h("七、字段含义速查", 1)
    table(["字段", "填写要求"], [
        ["id", "每条唯一，例如 resume-001；不要写真实姓名"],
        ["text", "脱敏正文；不要把原始手机号、邮箱、学校名称写进来"],
        ["gold_sections", "人工判断的正确板块集合，这是解析 F1 的核心"],
        ["annotator_a", "你的标注者名称或代号，例如 zhaowenkai"],
        ["annotator_b", "没有第二个人时留空，不要伪造第二标注者"],
        ["adjudicated_by", "有分歧裁决时填写；一个人初标可留空"],
        ["parse_quality", "只能填 high、medium、low"],
        ["resume_quality", "内容质量 1-5；不是解析正确性"],
        ["match_quality", "没有岗位匹配人工标签时填 null"],
        ["over_scored", "系统是否明显虚高；不确定就 false 并写 notes"],
    ])

    h("八、两个人如何标注才不会混乱", 1)
    p("本项目采用‘同一批数据、两人独立标注、结果分开保存’。两个人看到的 59 份 TXT 内容完全相同，但在完成全部标注前不要互相查看标签，也不要讨论某一份应该勾选什么。这样才能计算真实的标注一致性。")
    table(["人员", "导入目录", "导出文件名", "标注者代号"], [
        ["标注员 A", "数据集_标注员A", "real_parse_annotations_A.json", "例如 annotator_A"],
        ["标注员 B", "数据集_标注员B", "real_parse_annotations_B.json", "例如 annotator_B"],
    ])
    p("操作顺序：两人分别打开自己的标注工具副本；各自填写标注者代号；导入对应目录的全部 TXT；独立完成标注；导出后马上改名为 A 或 B 版本。绝对不要把两人的结果保存成同一个 real_parse_annotations.json。")
    p("工具会把文件名 resume-001、resume-002 等作为稳定样本 ID，并额外保存 source_file。即使两个人导入顺序不同，后续仍可以按同一个 ID 比对，不会因为顺序不同而错配。")
    p("全部完成后由项目负责人收集两个 JSON，统一做一致性比对。分歧样本由负责人依据教程规则裁决，并在最终结果中保留 annotator_a、annotator_b 和 adjudicated_by。")
    p("如果实际只有一个人完成标注，必须把 label_policy 改为 single_expert_initial_annotation_pending_review，不能声称完成双人一致性。")

    h("九、运行解析指标", 1)
    p("组员不需要运行评测脚本。标注完成后，把‘标注结果’文件夹中的 A、B 两个 JSON 发回负责人，由负责人统一比对、裁决和计算指标。")
    p("输出的 micro_precision、micro_recall、micro_f1 是板块级指标。正确表述是‘真实脱敏样本的板块识别 F1’，不能说成字段级准确率或整体简历解析准确率。")

    h("十、岗位匹配数据怎么标", 1)
    p("岗位匹配标注和简历板块标注是两套数据，不能把 gold_sections 和岗位 1-5 分混在同一条字段里。每条岗位匹配样本至少包含：脱敏简历、人工整理 JD、岗位类别、学历要求、匹配等级和说明。")
    code('''{
  "id": "real-match-001",
  "resume_text": "脱敏简历正文",
  "job_text": "人工整理后的岗位要求",
  "job_category": "数据分析",
  "education_requirement": "本科",
  "match_label": 4,
  "label_reason": "技能和项目基本匹配，但缺少 SQL 实际证据",
  "annotator": "zhaowenkai"
}''')
    table(["分数", "含义"], [
        ["1", "基本不匹配，岗位方向或硬条件明显不符"],
        ["2", "弱匹配，有少量相关内容但缺口明显"],
        ["3", "部分匹配，能做部分工作但证据不足"],
        ["4", "较匹配，主要要求满足，仍有少量缺口"],
        ["5", "高度匹配，方向、技能和经历证据都充分"],
    ])
    p("不要根据系统生成的匹配分反填人工标签；先人工阅读简历和 JD，再打分并写 label_reason。岗位匹配数据和岗位库不包含在本协作包内，由项目负责人另行组织和评测。")

    h("十一、哪些数据能训练，哪些只能测试", 1)
    table(["数据", "能否训练", "能否测试", "原因"], [
        ["A 池已人工复核板块标签", "可用于解析规则校准", "可用于解析测试", "有 gold 标签"],
        ["B 池复杂样本", "不建议直接训练", "可做边界测试", "用于发现能力边界"],
        ["C 池", "禁止", "只做现场演示", "避免演示样本污染指标"],
        ["61 条弱标注岗位集", "可做探索性训练", "不能在同源上宣称泛化", "曾用于拟合和评估"],
        ["match_splits/train.json", "可训练", "可做训练误差", "不能当最终测试"],
        ["match_splits/validation.json", "不训练", "可选配置", "用于选模型和阈值"],
        ["match_splits/test.json", "禁止训练", "最终只测一次", "最终泛化评估"],
        ["公开岗位库", "详情核验并人工结构化后才可训练", "可做岗位检索", "搜索结果不等于完整 JD"],
    ])

    h("十二、最容易犯的 8 个错误", 1)
    for text in [
        "把真实姓名、电话、邮箱复制进 JSON。",
        "看到系统预测了 education，就直接把 education 填进 gold_sections。",
        "把空标题当作有内容板块。",
        "把简历内容质量 4 分误当作解析正确率 80%。",
        "把 B 池、C 池样本混进训练或正式评测。",
        "用大模型自动生成 1-5 匹配标签再训练。",
        "在同一批数据上拟合 alpha 后又报告测试效果。",
        "用 Excel 打开 JSON 后保存，导致 UTF-8 或引号损坏。",
    ]:
        doc.add_paragraph(text, style="List Bullet")

    h("十三、你现在可以照着做的最短流程", 1)
    p("第一步：标注员 A 和 B 分别从自己的数据集目录导入同样的 59 份 TXT。")
    p("第二步：两人分别完成 A 池 15 条，确认流程无误后再继续其余样本。")
    p("第三步：两人分别导出并改名为 real_parse_annotations_A.json 和 real_parse_annotations_B.json。")
    p("第四步：负责人汇总两份结果，按稳定 ID 比对分歧；分歧样本依据教程规则裁决。")
    p("第五步：只把裁决后的版本作为正式 real_parse_annotations.json，再运行 eval_real_annotations.py 查看板块级 P/R/F1。")
    p("第六步：把 errors 中的 miss 和 extra 记录下来：miss 是解析漏掉的板块，extra 是解析误识别的板块。修改规则后重新运行指标，不能直接修改 gold 标签来让分数变高。")

    h("十四、项目中相关脚本索引", 1)
    table(["脚本", "作用"], [
        ["脚本/anonymize_resumes.py", "抽取文本并脱敏，由负责人使用"],
        ["脚本/classify_resumes.py", "A/B/C 分池，由负责人使用"],
        ["脚本/materialize_expert_annotations.py", "生成首轮专家初标 JSON"],
        ["脚本/eval_real_annotations.py", "计算真实板块 P/R/F1"],
        ["脚本/compare_annotation_sets.py", "比较 A/B 两名标注员的分歧"],
        ["脚本/eval_parse_baseline.py", "计算合成解析基线"],
        ["脚本/split_match_eval.py", "按岗位组切分匹配数据"],
        ["脚本/eval_match_holdout.py", "评估验证/测试岗位匹配集"],
        ["脚本/run_quality_benchmark.py", "生成完整功能和性能报告"],
    ])
    p("教程生成时间：" + time.strftime("%Y-%m-%d %H:%M:%S"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT))
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
