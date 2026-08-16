# A 池分歧裁决规则与清单

> 对应 `annotation_disagreements_A_B_common15.json`。本文件只裁决标准与执行顺序，**不覆盖** A/B 原始标注。

## 一、硬边界（先背下来）

| 字段 | 判什么 | 不判什么 |
|---|---|---|
| `gold_sections` | 脱敏正文里**是否存在该板块内容** | 写得好不好、能否进 Prompt |
| `parse_quality` | **文本可读 / 版式是否可分块**（high/medium/low） | 简历竞争力、实习含金量 |
| `resume_quality` | 内容完整度、证据与量化（1–5） | OCR 糊不糊 |
| `issue_types` | 有文本证据才勾选，可多选 | 凭感觉“看起来乱” |

三者禁止互相顶替：扫描糊 ≠ 简历差；简历差 ≠ 板块不存在。

## 二、`gold_sections` 裁决树

按下列顺序对每个争议板块二选一：

1. **有独立标题或连续语义块** → 标记该板块。
2. **无标题，但正文能明确归类**（如“在某某公司实习三个月”）→ 仍标记。
3. **仅一句带过、无法独立成块**（如自我评价里提一句“获过奖”）→ **不标** awards；可标 summary。
4. **校园活动 vs 项目**：有明确项目名/交付物 → `projects`；班级活动/社团值班无交付物 → `campus`；两者都有则都标。
5. **教育**：出现学校/专业/学历任一即可标 `education`；仅年级无学校且无专业 → 不标。
6. **空数组**：仅当全文几乎不可读、无法判断任何板块时才允许；否则至少应有 `basic_info` 或可识别板块。

优先字段：先裁决全部 `gold_sections`，再碰其他字段。

## 三、`parse_quality` 三档

| 档 | 条件 |
|---|---|
| high | 正文连续可读，模块边界清楚，关键字段可定位 |
| medium | 可读但双栏/表格/碎片导致边界模糊，或关键字段偶发缺失 |
| low | OCR 噪声重、乱序严重，或核心模块大面积无法定位 |

注意：`parse_quality=low` 的样本**仍可有**完整 `gold_sections`（人眼能看出板块，机读难）。

## 四、`issue_types` 证据门槛

| 类型 | 勾选条件 |
|---|---|
| `layout_fragmentation` | 明显双栏/表格打断/行碎片 |
| `ocr_noise` | 错字、断字、乱码、竖排混排 |
| `weak_structure` | 几乎无标题、段落粘连 |
| `missing_*` | 规范期望有、正文确实没有（不是“看不清”） |
| `missing_metrics` | 经历/项目无量化结果 |
| `over_scored_risk` | 内容空洞但易被规则打高分 |

无证据不勾；A/B 一边有一边无时，裁决员打开原文核对一句即可。

## 五、本轮 15 条执行顺序（约 60–90 分钟）

工作表由脚本生成：`docs/testing/A池裁决工作表.json`。

| 优先级 | ID | 先裁什么 | 常见坑 |
|---|---|---|---|
| P0 | resume-009 | gold_sections（A 为空） | 空标签几乎必错，先按原文重标 |
| P0 | resume-005 / 013 / 015 | gold_sections 差集大 | campus/education/internship 边界 |
| P1 | resume-002 / 003 / 004 / 006 / 012 / 014 | gold_sections 差 1–2 项 | summary / campus / awards |
| P2 | resume-007 / 008 / 010 | parse / resume_quality / issues | 勿把内容分当解析分 |
| — | resume-001 / 011 | 若未进分歧表 | 确认两边一致后直接入黄金集候选 |

裁决记录字段（写入工作表，勿改原 JSON）：

- `adjudicated_gold_sections`
- `adjudicated_parse_quality`
- `adjudicated_resume_quality`
- `adjudicated_issue_types`
- `adjudicator` / `adjudicated_at` / `rationale`（一句话）

## 六、完成后才允许做的事

1. 导出黄金标签 → `data/eval/real_parse_annotations.json`（仅裁决版）。
2. 跑 `eval_real_annotations.py`，F1 **必须**写清“真实脱敏样本板块识别 F1（裁决后）”。
3. 从裁决稳定样本中抽 8～15 条进 Prompt 示例池；测试池样本不得进示例。

未完成裁决前：**禁止**对外报告真实 F1，禁止用这批标签微调。

> **更新（已收口）**：A 池前 15 已完成第三方裁决并评测，micro F1≈0.98（解析规则收口后复测）。对外引用必须带「脱敏 + 裁决后 + 板块非空」口径。详见 `docs/赛前收口完成.md`。

## 七、命令

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\build_adjudication_worksheet.py
.\.venv\Scripts\python.exe scripts\compare_annotation_sets.py `
  --a <A导出.json> --b <B导出.json> `
  --output ..\docs\testing\annotation_disagreements_A_B_common15.json `
  --common-only
```
