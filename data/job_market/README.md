# 公开岗位样本库

本目录保存经过来源核验的公开招聘要求摘要。原始简历数据、联系人和招聘平台账号信息不进入仓库。

## 样本字段

每行一个 JSON 对象，推荐使用 `backend/scripts/import_job_market.py` 导入：

- `source_url`：最终访问地址
- `collected_at`：采集时间
- `title`：岗位页面标题
- `text_redacted`：脱敏后的岗位正文
- `education.minimum`：最低学历，支持 `college` / `bachelor` / `master` / `doctorate`
- `education.preferred`：优先学历
- `skill_mentions`：规则初筛出的技能词，须人工复核为 `must_skills` / `nice_skills`
- `review_status`：未人工核验前不得进入监督训练集

## 采集边界

- 只导入明确公开、无需登录、无需验证码的页面。
- 遵守来源站点 `robots.txt` 和使用条款，默认请求间隔 2 秒。
- 不采集手机号、邮箱、联系人姓名等个人信息。
- 原始 HTML 不保存；只保存脱敏文本和来源元数据。
- 未完成人工复核的样本只能用于岗位检索候选库，不能宣称为训练集。

## 训练分层

`text_redacted` 可用于文本检索和岗位画像统计；只有补充 `must_skills`、`nice_skills`、学历和岗位类别并完成人工复核后，才可进入规则校准或匹配模型训练。

## 当前样本概况

截至 2026-08-03，`public_job_samples.jsonl` 包含 109 条 UTF-8 编码的公开岗位摘要，其中 95 条来自公开职位详情页、14 条为搜索结果候选样本；详情页样本覆盖西安、北京、上海 3 个城市，学历字段包含大专、本科、硕士等层级。

其中 `public_job_page` 样本已从公开职位详情页核验并完成一次人工结构化，标记为 `single_source_verified`；`public_job_search_result` 样本只来自公开搜索结果列表，标记为 `pending_manual_review`，不代表完整 JD，也不代表多标注黄金样本。当前适合用于岗位库检索、规则匹配演示、相关岗位 Top5 分数榜和岗位画像统计；未完成详情复核的样本不应直接作为监督训练集。若 `must_skills` 曾写入「岗位详情已核验，技能需人工复核」占位句，已改为从职责文本回填技能或留空，不再把备注当技能展示。
