# 简析智评 / Jianxi Resume Intelligence

[简体中文](README.md) | [English](README_EN.md)

[![CI](https://github.com/zhaokai0604/jianxi-resume-intelligence/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/zhaokai0604/jianxi-resume-intelligence/actions/workflows/ci.yml) [![CodeQL](https://github.com/zhaokai0604/jianxi-resume-intelligence/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/zhaokai0604/jianxi-resume-intelligence/actions/workflows/codeql.yml) [![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

> 2026 大学生数据要素素质大赛国赛晋级作品。现以完整软件项目方式开源维护。

简析智评是一个面向学生成长与教学分析的简历处理平台。它将简历上传、文本提取、结构化解析、证据约束评分、岗位匹配、优化稿生成和聚合统计串成可运行的应用闭环。

它是**辅助分析工具**，不是自动化招聘决策系统；任何评分、匹配或生成结果均应由具备相应职责的人复核后使用。

## 功能概览

- Word / PDF 简历上传、文本提取与可选 OCR，支持 SSE 实时过程反馈。
- 教育、经历、技能、奖项等结构化解析，以及六维度质量分析。
- 区分“链路完成、文本可读、分析可信度”，避免把处理成功误写成结论准确。
- 基于岗位画像、规则约束与可选语义检索的岗位匹配，并展示命中和缺失依据。
- 生成可下载的优化稿 DOCX 与差异对比；不应编造候选人的经历或技能。
- 学生、教师和管理员角色；教师侧使用聚合信息，不以简历正文作为教学看板数据。
- 无 API Key 的本地回退模式；外部 AI 仅为可选能力，失败时回退到本地逻辑。

## 架构

```text
Vue 3 + Vite 前端
        │ HTTP / SSE
FastAPI 服务 ── SQLite（本地）/ MySQL（部署）
        ├── 文档解析、OCR、结构化抽取
        ├── 评分、可信度护栏与结果解释
        ├── 岗位画像、匹配与可选语义检索
        └── DOCX/PDF/ZIP 交付与可选 Celery 异步任务
```

## 快速开始

### 环境要求

- Windows 10/11（启动脚本优先支持 Windows）
- Python 3.10–3.12
- Node.js 18+
- Docker Desktop（可选，用于容器化运行）

### 本地开发模式

```powershell
git clone https://github.com/zhaokai0604/jianxi-resume-intelligence.git
cd jianxi-resume-intelligence
copy .env.example .env
.\start_dev.bat
```

默认使用 SQLite，本地未启用 Celery 时不依赖 Redis。启动完成后访问：

| 服务 | 默认地址 |
| --- | --- |
| 前端 | `http://127.0.0.1:5174` |
| 健康检查 | `http://127.0.0.1:8000/api/health` |

`start_dev.bat` 会在端口被占用时尝试选择可用后端端口。若需要管理员功能，请在 `.env` 中设置唯一且不少于 12 位的 `ADMIN_PASSWORD`；任何联网部署都必须重新设置 `SESSION_SECRET`。

### Docker 模式

```powershell
copy .env.example .env
# 修改 .env 中的 SESSION_SECRET、ADMIN_PASSWORD 和数据库密码
docker compose up -d --build
```

面向公网或多人使用时，请使用生产覆盖配置，并先执行严格预检：

```powershell
cd backend
python scripts/preflight.py --strict-production
cd ..
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

详细部署、反向代理、备份和恢复说明见 [部署指南](docs/部署指南.md)。

## 配置要点

真实配置只保存在本地 `.env`，不要提交到 Git。

| 配置项 | 用途 |
| --- | --- |
| `APP_ENV` | 运行环境；公网部署使用 `production`。 |
| `DATABASE_URL` | SQLite 或 MySQL 连接地址。 |
| `SESSION_SECRET` | 会话签名密钥；必须使用随机且唯一的值。 |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | 管理员账号；密码不少于 12 位且不得使用示例值。 |
| `ALLOW_REGISTER` | 公网部署建议设为 `false`。 |
| `SESSION_COOKIE_SECURE` | HTTPS 部署必须设为 `true`。 |
| `DEEPSEEK_API_KEY` | 可选外部 AI；留空时走本地回退。 |
| `USE_CELERY` / `REDIS_URL` | 可选异步任务能力。 |

外部 AI 启用后，简历文本可能会离开本地环境。使用前应获得适当授权并向用户提供清晰告知。

## 开发与质量验证

```powershell
# 后端：安装依赖后执行
.\backend\.venv\Scripts\python.exe -m ruff check backend
.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q

# 前端
cd frontend
npm ci
npm run lint
npm run build

# Compose 定义
cd ..
docker compose -f docker-compose.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet
```

GitHub Actions 会在 `main` 的推送和拉取请求中执行后端 lint/测试、前端干净安装/lint/构建、Compose 校验与 CodeQL 扫描。`v*` 标签会创建 GitHub Release 并附带前端构建产物；没有配置未提供目标的自动部署。

## 目录结构

```text
backend/       FastAPI 服务、业务逻辑、任务与测试
frontend/      Vue 3 前端
data/          示例、公开岗位摘要与运行目录占位文件
deploy/        Nginx 等部署配置
docs/          使用、部署、数据安全与技术说明
scripts/       备份与恢复脚本
.github/       CI、CodeQL、发布、依赖更新与协作模板
```

## 数据、安全与使用边界

- 不提交真实简历、姓名/联系方式、`.env`、数据库、上传件、导出报告、令牌或会话密钥。
- 仓库中的岗位数据仅为脱敏公开摘要，默认不构成训练集、招聘基准或真实性保证。
- 可选语义模型的上游许可与数据来源须单独核验；默认不启用相关模型。
- 处理成功率、解析结果或匹配分数不等同于招聘适配性、就业能力或普适准确率。
- 发现漏洞、密钥或个人数据暴露时，请勿公开提交 Issue；见 [SECURITY.md](SECURITY.md)。

更多边界说明见 [数据安全说明](docs/数据安全说明.md) 与 [NOTICE.md](NOTICE.md)。

## 贡献

欢迎提交 Issue 和 Pull Request。贡献前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)，并确保提交内容不含个人数据、真实简历和凭据。

## 许可证

项目自行编写的代码和文档采用 [Apache License 2.0](LICENSE)。第三方依赖、模型、数据和字体遵循各自许可，详见 [NOTICE.md](NOTICE.md)。
