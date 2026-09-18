# Jianxi Resume Intelligence / Resume Analysis & Evaluation Platform

[中文](README.md) | [English](README_EN.md)

[![CI](https://github.com/zhaokai0604/-/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/zhaokai0604/-/actions/workflows/ci.yml) [![CodeQL](https://github.com/zhaokai0604/-/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/zhaokai0604/-/actions/workflows/codeql.yml) [![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

Jianxi Resume Intelligence is a full-stack platform for structured resume ingestion, evidence-aware evaluation, job matching, document delivery, and aggregated teaching insights. It was created as a vocational-education competition project and is now maintained as an open-source engineering project.

> The system is a decision-support tool, not an automated hiring decision system. Scores and matching results require human review.

## Highlights

- Parse Word/PDF resumes, with optional OCR, structured extraction, and SSE progress events.
- Evaluate resumes across six dimensions while separating pipeline completion, text readability, and analysis reliability.
- Match a resume to a job profile with rules, evidence, and optional semantic retrieval.
- Produce a revised DOCX and an explainable diff without inventing candidate experience.
- Provide separate student, teacher, and administrator surfaces; teacher views use aggregation rather than resume body text.
- Run locally without an API key; optional external-AI use is explicit and has a local fallback.

## Architecture

```text
Vue 3 + Vite frontend
        │ HTTP / SSE
FastAPI service ── SQLite (local) or MySQL (deployment)
        ├── parsing / OCR / structured extraction
        ├── rule-based scoring and reliability guardrails
        ├── job matching and optional semantic retrieval
        └── DOCX/PDF/ZIP delivery and optional Celery workers
```

## Quick start (Windows)

Prerequisites: Python 3.10–3.12 and Node.js 18+.

```powershell
git clone https://github.com/zhaokai0604/-.git
cd -
copy .env.example .env
# Set a unique SESSION_SECRET and ADMIN_PASSWORD in .env before exposing the service.
.\start_dev.bat
```

The local launcher uses SQLite and starts the API at `http://127.0.0.1:8000` and the UI at `http://127.0.0.1:5174` unless those ports are occupied. The application can run without Redis when `USE_CELERY=false`.

For containers:

```powershell
copy .env.example .env
docker compose up -d --build
```

For an internet-facing deployment, read [the deployment guide](docs/部署指南.md), use the production Compose overlay, and complete the strict preflight check. Do not publish a service with example credentials.

## Development and verification

```powershell
# Backend
.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q

# Frontend
cd frontend
npm ci
npm run lint
npm run build
```

GitHub Actions performs backend lint/tests, frontend install/lint/build, Docker Compose validation, dependency update checks, and CodeQL analysis. Tagging `v*` creates a release artifact; it does not deploy to an unspecified server.

## Data, privacy, and limitations

- Never commit real resumes, contact information, `.env` files, databases, uploaded documents, or generated reports.
- The included job dataset is a redacted public-job sample set, not a hiring benchmark or a training dataset by default.
- Optional semantic-model metadata has an upstream license/provenance review requirement; the optional model is disabled by default.
- Evaluation figures in competition documents are scoped evidence, not claims of universal accuracy or hiring suitability.
- If an external AI provider is enabled, resume text may leave the local environment. Obtain authorization and provide an appropriate notice first.

See [NOTICE.md](NOTICE.md), [SECURITY.md](SECURITY.md), and the Chinese [data-safety note](docs/数据安全说明.md) for boundaries and responsibilities.

## Contributing

Issues and pull requests are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and never include personal data or credentials in an issue, commit, or pull request.

## License

Project-authored code and documentation are released under the [Apache License 2.0](LICENSE). Third-party dependencies, models, data, and fonts retain their own terms; see [NOTICE.md](NOTICE.md).
