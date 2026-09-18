# Contributing / 参与贡献

Thanks for helping improve Jianxi Resume Intelligence. This project handles employment-related documents, so correctness, privacy, and reproducibility come before feature count.

## Before opening a pull request

1. Create a focused branch from `main`; do not commit `.env`, real resumes, exported reports, databases, or access tokens.
2. Explain the problem, the boundary of the change, and any effect on privacy, scoring, or evidence claims.
3. Run the checks below from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q
cd frontend
npm ci
npm run lint
npm run build
```

4. Keep test data synthetic or demonstrably anonymized. Do not turn exploratory metrics into product claims.
5. Update documentation when configuration, behavior, or a public interface changes.

## Pull-request expectations

- One purpose per pull request, with tests that fail before the fix where practical.
- Preserve the distinction between pipeline completion, text readability, and analysis reliability.
- State external dependencies and rollback considerations for operational changes.
- Use clear Chinese or English. Bilingual user-facing text is welcome.

## 中文说明

欢迎贡献，但招聘与简历场景优先考虑隐私、真实性和可复现性。请基于 `main` 建立单一目的分支；严禁提交真实简历、`.env`、密钥、数据库、上传件和导出报告。提交前运行上述测试，并在 PR 中说明改动范围、数据/隐私影响、评分或证据口径影响。探索结果不得包装为验收结论。
