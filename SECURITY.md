# Security Policy / 安全策略

## Supported version / 支持版本

Security fixes are applied to the latest `main` branch. Deployment users should update to the newest reviewed release or commit.

## Reporting a vulnerability / 漏洞报告

Do **not** open a public issue for a vulnerability, leaked credential, personal-data exposure, authentication bypass, or unsafe file-processing path. Use GitHub's private vulnerability reporting for this repository when it is enabled, or contact the maintainer privately through the repository owner's GitHub profile. Include a minimal reproduction, impact, affected revision, and safe remediation suggestion. Do not attach real resumes or secrets.

The maintainer will acknowledge a credible report, assess it privately, and coordinate a fix before public disclosure where possible.

## Deployment baseline / 部署基线

- Create a unique `SESSION_SECRET` and `ADMIN_PASSWORD` of at least 12 characters; never use values from examples.
- Set `APP_ENV=production`, `SESSION_COOKIE_SECURE=true`, and `ALLOW_REGISTER=false` for an internet-facing deployment.
- Keep `.env`, databases, uploads, extracted files, reports, raw resumes, and logs outside Git.
- Review the model/data provenance before enabling optional semantic or external-AI features; sending resume text to an external API requires an appropriate user notice and authorization.
