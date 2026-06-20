# 简历评价智能体

面向高校学生的简历评价与岗位匹配系统。系统支持上传 Word、PDF 和 ZIP 批量简历，默认优先调用 DeepSeek 完成诊断与建议生成；当 DeepSeek 不可用时自动回退到离线规则分析，继续完成解析、评分、岗位匹配、可视化展示、报告导出和历史记录管理。

## 技术栈

- 前端：Vue 3 + Vite + ECharts
- 后端：FastAPI
- 数据库：MySQL
- Word 解析：python-docx
- PDF 解析：pdfplumber
- OCR：PaddleOCR
- 报告导出：python-docx + reportlab
- AI 分析：默认优先 DeepSeek，失败自动回退离线规则分析
- 登录安全：用户名密码登录 + HttpOnly Cookie 会话 + PBKDF2 密码哈希

## 目录结构

```text
简历分析/
  backend/              FastAPI 后端
  frontend/             Vue 前端
  data/                 上传、解压、报告文件
  assets/fonts/         PDF 中文字体
  docs/                 使用和安全说明
  database.sql          MySQL 建表脚本
  docker-compose.yml    Docker 启动配置
  .env.example          配置模板
```

## Docker 运行

先复制配置：

```powershell
copy .env.example .env
```

启动：

```powershell
docker compose up -d --build
```

如果工程位于中文路径下，Docker 新版构建器可能出现构建会话兼容问题，可使用下面的兼容命令启动：

```powershell
$env:COMPOSE_BAKE='false'
$env:DOCKER_BUILDKIT='0'
$env:COMPOSE_DOCKER_CLI_BUILD='0'
docker compose up -d --build
```

访问：

- 前端：http://localhost:5173
- 后端健康检查：http://localhost:8000/api/health
- Docker 内置 MySQL 对外端口：`3307`

如果刚安装 Docker Desktop 或刚启用 WSL，Windows 可能需要重启一次后 Docker 引擎才会正常工作。

停止：

```powershell
docker compose down
```

## Windows 本地运行

前置条件：

- Python 3.10、3.11 或 3.12（不要用 3.13+，部分依赖尚未完全兼容）
- Node.js
- MySQL

创建数据库：

```powershell
mysql -uroot -p < database.sql
```

复制配置：

```powershell
copy .env.example .env
```

如本机 MySQL 账号密码不同，修改 `.env` 中的 `DATABASE_URL`。

当前默认本地数据库配置为：

```text
mysql+pymysql://resume:resume123@localhost:3306/resume_ai?charset=utf8mb4
```

启动后端：

```powershell
.\start_backend.bat
```

启动前端：

```powershell
.\start_frontend.bat
```

运行后端测试（需 Python 3.10–3.12）：

```powershell
.\run_tests.bat
```

访问：

```text
http://127.0.0.1:5173
```

## DeepSeek 增强分析

默认优先使用 DeepSeek 分析。系统会先完成本地解析和规则评分，再调用 DeepSeek 生成更具体的诊断、修改建议和表达优化。

如需真正启用 DeepSeek：

1. 在 `.env` 中填写 `DEEPSEEK_API_KEY`。
2. 保持前端“配置”页的“优先使用 DeepSeek 分析”开启。

如果未配置 API Key、网络不可用、接口超时或返回格式异常，系统会自动回退到离线规则分析，并把本次记录标记为 `offline_fallback`。如果用户在配置页主动关闭 DeepSeek，则本次记录标记为 `offline`。

页面、历史记录和导出报告都会显示实际分析来源：

- `deepseek` / `DeepSeek 已使用`：已调用 DeepSeek 生成诊断和建议。
- `offline_fallback` / `DeepSeek 不可用，已回退离线规则分析`：原本优先调用 DeepSeek，但因无 Key、无网络或 API 异常回退。
- `offline` / `离线规则分析`：用户主动关闭 DeepSeek 或明确使用离线规则。

注意：总分和分项评分默认由本地规则体系计算，以保证评分稳定可解释；DeepSeek 主要增强问题诊断、修改建议和表达优化。因此 DeepSeek 成功时，分数和图表也可能与离线分析一致。

## 登录与账号安全

系统支持用户名密码注册、登录和退出，同时保留游客试用模式。未登录时上传和历史记录归属 `guest` 游客账号；登录后上传、历史、批量任务、报告下载和删除都按当前用户隔离。

- 密码不会明文保存，后端使用安全哈希保存密码。
- 登录态使用 `HttpOnly` Cookie，前端脚本不能直接读取会话值。
- 注册时前端展示密码强度提示，后端强制校验最少 8 位且同时包含字母和数字。
- 登录用户可在账号页导入游客历史；导入不会删除游客演示数据。
- 微信登录当前仅预留配置项，未配置时保持关闭，不影响离线运行。

建议在 `.env` 中配置独立的 `SESSION_SECRET`。生产或公网 HTTPS 环境可把 `SESSION_COOKIE_SECURE` 设为 `true`。

## 管理员账号

系统支持轻量管理员后台。首个管理员通过 `.env` 配置：

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=请改成强密码
ADMIN_DISPLAY_NAME=系统管理员
```

后端启动时会自动创建或更新该管理员账号，密码只保存 PBKDF2 哈希。普通注册接口不能创建管理员。管理员登录后顶部会出现“管理”入口，可查看系统统计、用户列表、记录元数据和审计日志，可禁用/启用账号、生成临时密码、删除异常记录。管理员默认不能直接查看或下载用户简历正文和报告内容。

管理员保护规则：

- 普通用户访问 `/api/admin/*` 会被拒绝。
- 不能禁用游客账号、不能禁用当前管理员账号、不能禁用最后一个管理员。
- 管理员操作会写入 `audit_logs` 审计日志。
- 管理员后台不返回密码哈希、会话密钥、DeepSeek Key 等敏感信息。

## 数据安全

- 上传文件保存在 `data/uploads/`。
- ZIP 解压文件保存在 `data/extracted/`。
- 报告文件保存在 `data/reports/`。
- 默认优先调用 DeepSeek 时会把简历文本和规则评分结果发送到配置的 DeepSeek API；如需完全本地处理，可在前端配置页关闭 DeepSeek。
- 登录后只能访问当前账号的数据；游客只能访问游客数据。
- 报告下载统一走 `/api/reports/{id}/download`，后端会校验报告归属用户。
- 删除历史记录时会同步清理相关本地文件；导入游客历史产生的共享文件只有在没有其他记录引用时才会被删除。
- `.env` 不应提交到版本管理。

## 第一阶段已实现接口

- `GET /api/health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `POST /api/auth/import-guest-history`
- `POST /api/resumes/analyze`
- `POST /api/resumes/analyze-zip`
- `GET /api/history`
- `GET /api/history/{record_id}`
- `POST /api/history/bulk-delete`
- `GET /api/reports/{id}/download?format=docx|pdf`
- `DELETE /api/history/{id}`

## 注意事项

- 第一版只支持 `.docx`、`.pdf`、`.zip`。
- `.doc` 老格式会提示转换为 `.docx`。
- 默认 Docker / 本地依赖先不安装 PaddleOCR，以保证主流程快速可运行。
- 后续需要扫描版 PDF OCR 时，在后端环境额外执行 `pip install -r backend/requirements-ocr.txt`；建议使用 Python 3.10 或 3.11。
- PDF 中文报告依赖项目内字体 `assets/fonts/NotoSansSC-Regular.ttf`。打包提交时必须保留 `assets/fonts/`，否则 PDF 中文可能显示为方块或问号。
