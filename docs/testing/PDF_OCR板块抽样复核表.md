# PDF OCR 后板块级抽样复核

> 目标：证明「OCR 后可读」≠「板块识别准」。抽 8～10 份做人工板块核对，形成边界证据，不追求全量标注。

## 一、三层指标（答辩必须分开说）

| 层 | 指标 | 现有证据口径 | 能证明什么 |
|---|---|---|---|
| L1 链路 | 分析成功率 / 报告生成率 | 平台冒烟、功能基准 | 系统能跑通 |
| L2 可读 | 无 OCR 可读率 / OCR 后可读率 | 如无 OCR≈0–56% 量级、开 OCR 后 PDF 可读率上升 | 真实扫描件难，必须开 OCR |
| L3 可信 | 板块命中（人工抽检）+ 告警是否合理 | 本表抽样 | 可读之后边界在哪 |

禁止把 L2 说成解析准确率，禁止把 L1 说成分析质量。

## 二、抽样规则

1. 从本地离线 PDF 池中，在 **OCR 成功可读** 的文件里分层抽：
   - 清晰单栏 2～3 份
   - 双栏/表格 3～4 份
   - 扫描噪声明显 2～3 份
2. 总数 8～10；不进 git 原文，只记脱敏 ID / 哈希 / 版式类型。
3. 每份只核：系统检出板块 vs 人工可见板块（有/无），不要求字段级抽取。

## 三、记录字段

见 `PDF_OCR板块抽样工作表.json`（由脚本生成空表）：

- `sample_id`：脱敏编号（如 OCR-01）
- `layout_type`：single / dual / table / scan_noise
- `ocr_readable`：是否 OCR 后可读（本抽样应为 true）
- `human_sections`：人工可见板块列表
- `system_sections`：系统非空板块列表
- `section_hit` / `section_false` / `section_miss`
- `alert_reasonable`：低信噪/版式告警是否合理（yes/partial/no）
- `note`：一句话

## 四、对外表述模板

> 在 OCR 开启后，抽样 N 份扫描/复杂版式 PDF 中，文本均可读；板块级人工核对命中率为 x/N（或列出易混板块）。该结果说明 OCR 解决可读性，板块边界仍需规则与人工复核，因此平台对低质量样本输出可信度告警而非虚高分数。

## 五、命令

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\build_ocr_section_review_sheet.py --count 10
```
