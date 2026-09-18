# Notice / 第三方声明

The Apache License 2.0 in [`LICENSE`](LICENSE) applies to project-authored source code and documentation only. It does not replace the licenses, terms, or attribution requirements of third-party software, models, fonts, public job listings, or other materials.

- Dependencies remain under their respective licenses; see `backend/requirements.txt` and `frontend/package.json`.
- `data/models/sbert-resume-match/` contains model metadata and tokenizer configuration derived from `shibing624/text2vec-base-chinese`. The model card identifies its upstream source but does not declare a license. It is disabled by default and must not be redistributed or enabled until its upstream license and data provenance are confirmed.
- `data/job_market/` contains redacted summaries of public job listings. Retain source URLs and comply with the source sites' terms; do not add contact data or scraped HTML.
- Real resumes, API keys, session secrets, databases, uploads, generated reports, and raw annotation material are intentionally excluded from version control.

本仓库的 Apache License 2.0 只覆盖项目自行编写的代码和文档，不替代第三方依赖、模型、字体、公开岗位内容及其他材料本身的许可或署名要求。真实简历、密钥、数据库和上传/报告产物不得提交。
