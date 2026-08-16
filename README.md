# 简历评价智能体 V2.0

> **大学生数据要素素质大赛 · 职教组参赛作品**  
> 高校就业数据治理闭环：学生诊断 → 教师班级洞察 → 岗位与简历质量沉淀。  
> 无需编程基础：双击启动即可完整体验；未配置大模型时自动离线运行。  
> **赛前证据已冻结**：[`docs/赛前收口完成.md`](docs/赛前收口完成.md)

---

## 一、项目是什么？

上传 Word / PDF 简历后，系统自动完成解析、评分、匹配与可下载优化稿，并形成学生 / 教师 / 管理三端闭环。

| 能力 | 说明 |
|------|------|
| 内容解析 | 分节识别 + OCR（可选）+ 结构化抽取（教育 / 经历 / 技能 / 获奖） |
| 六维评分 | 完整性、经历、语言、格式、亮点、岗位匹配；低信噪比纠偏与证据置信度 |
| 可信度分层 | 详情与报告分栏展示：**链路完成 ≠ 文本可读 ≠ 分析可信**；证据不足告警或总分封顶 |
| 岗位匹配 | 规则关键词 ⊕ 语义通道融合；本地公开岗位库筛选、相关岗位 Top5、命中 / 缺失依据 |
| 诊断与优化 | 技能图谱提示、**基于初稿的优化稿 DOCX + Diff**（不足处标【待补充】，不编造经历） |
| 实时过程 | 上传后 SSE 推送解析 / 评分中间事件，过程可演示、可复核 |
| 报告与版本 | Word / PDF 报告、ZIP 批量、历史版本 Δ 分（时光机） |
| 模拟面试 | 多模板随机换题、避重上轮；无 Key 也可离线出题 |
| 教师 / 管理 | 班级统计（无简历正文）、一键成课短板模板、用户与系统管理 |

**设计原则**

- **简析智评三擎架构**：语义理解 · 证据护航 · 生成交付（见下节）  
- **无 Key 可演示**：证据护航 + 本地语义理解可跑通；生成交付无云端时走本地模板回退  
- **交付物是优化稿**：建议与诊断是解释层，可下载完整 DOCX 才是结果  
- **证据分层报告**：成功率、可读率、板块 F1 分栏说，禁止混成「一个准确率」  

---

## 二、3 分钟快速体验

### 1. 环境

| 要求 | 说明 |
|------|------|
| 系统 | Windows 10 / 11（推荐） |
| Python | 3.10～3.12（安装时勾选 Add to PATH；勿用 3.14 建 venv） |
| Node.js | 18+ |
| 浏览器 | Chrome / Edge |

已装 Docker Desktop 时可跳过本机 Python/Node，见 [第六节](#六可选docker-一键启动)。

### 2. 启动

1. 进入项目目录 `简历分析V2.0`  
2. **双击** `start_dev.bat`  
3. 等待后端 / 前端窗口启动，浏览器打开首页  

| 页面 | 地址 |
|------|------|
| **系统首页** | http://127.0.0.1:5174 |
| 健康检查 | http://127.0.0.1:8000/api/health |

本地演示 **不需要 Redis**。`USE_CELERY=false` 时健康检查不会因 Redis 不可用把后端标成「异常」。

### 3. 上传体验

1. 可以**游客身份**直接用，无需登录  
2. 左侧 **「单份分析」** → 上传 `.docx` / `.pdf`  
3. 填写目标岗位（如「数据分析实习生」）→ 开始分析  
4. 看实时解析流 → 详情页看「链路｜可读｜可信」、六维分、岗位适配依据、**初稿↔优化稿 Diff**、下载报告  

关闭：关掉两个命令行窗口即可。

---

## 三、配置要不要改？（评委常问）

| 问题 | 答案 |
|------|------|
| 要自己写配置吗？ | **一般不用**。`start_dev.bat` 会从 `.env.example` 生成 `.env` |
| 管理员账号？ | 用户名见 `ADMIN_USERNAME`，密码以本地 `.env` 为准 |
| 要装 MySQL 吗？ | **演示不用**，默认 SQLite |
| 要装 Redis 吗？ | **本地不用**；仅 Docker / 异步任务可选 |
| 要配 AI 吗？ | **不用**。Key 留空 = 离线规则 + 本地语义（若已装权重） |
| 想改配置？ | 编辑项目根目录 `.env` 后重启 |

| 配置项 | 预置 | 说明 |
|--------|------|------|
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | 以 `.env.example` 为准 | 演示管理员，首次使用前请修改 |
| `ALLOW_REGISTER` | `true` | 允许注册 |
| `DEEPSEEK_API_KEY` | （空） | 空 = 不走云端大模型 |
| `USE_CELERY` | `false` | 本地无需 Redis |
| `USE_SEMANTIC_MATCH` | `true` | 启用语义匹配通道 |
| `USE_SEMANTIC_MODEL` | `false` | 只有经过独立留出验证的实验模型才显式开启 |

完整环境变量表见 [`docs/部署指南.md`](docs/部署指南.md)。

---

## 四、核心技术能力（答辩可讲）

### 4.1 简析智评三擎架构

> 简析智评采用「**语义理解、证据护航、生成交付**」三擎协同架构，形成从简历解析、岗位匹配、风险校验到优化交付的完整服务链路。

| 现有能力 | 包装名称 | 职责 |
|----------|----------|------|
| 双塔 SBERT（本地） | **语义理解引擎** | 理解简历与岗位语义关系，完成匹配排序 |
| 规则 / 分词基线（本地算法） | **证据护航引擎** | 学历硬约束、关键词核验、风险拦截、结果解释 |
| DeepSeek 等（可选云端） | **生成交付引擎** | 优化稿、建议、报告、模拟面试；无 Key 时本地回退 |

```text
语义理解引擎：判断「简历和岗位是否匹配」
        ↓
证据护航引擎：判断「结论有没有依据、是否触发硬约束」
        ↓
生成交付引擎：转化为优化稿、报告和训练建议
```

实现对应（答辩不必念代码名）：语义理解 ← `semantic_match` / 可选 `sbert-resume-match`；证据护航 ← 规则评分、匹配护栏、低信噪比；生成交付 ← `optimized_resume` / 报告 / 面试，云端仅为可选实现。**不要对外称「DeepSeek 引擎」。**

### 4.2 工程主链路

```text
上传（可 SSE 实时流）
  → 正文提取 / OCR / 分节解析 / 结构化抽取
  → 证据护航：六维规则评分 + 低信噪比 + 硬约束 / 可信度分层
  → 语义理解：岗位匹配排序；岗位库 Top5 + 命中/缺失依据
  → 生成交付：技能图谱提示 + 优化稿 / Diff / 报告（可选云端润色，失败回退）
```

### 4.3 工程验证数字（分层口径 · 赛前冻结）

平台主验收必须分栏说（详见 `docs/testing/平台能力验收实验方案.md`、[`docs/赛前收口完成.md`](docs/赛前收口完成.md)）：

| 层 | 冻结结果 | 证明什么 | 不能说成 |
|----|----------|----------|----------|
| L1 链路 | 59 份分析成功率 **100%**；合成冒烟通过；护栏 4/4 | 能跑通、能交付 | 解析准、打分准 |
| L2 可读 | 无 OCR 文本可读率 **≈55.9%**；开 OCR 后 PDF 可读率上升 | 真实扫描件难，必须 OCR | 板块 / 字段准确率 |
| L3 可信 | A 池前 15 **已第三方裁决**；板块 micro F1 **0.98**（P≈0.97 / R≈0.99） | 脱敏样本板块识别边界 | 字段级准确率、全库泛化 |

薄弱板块（可主动说明）：`projects` 仍偶发边界混淆；平台策略是告警 / 封顶，不虚高分。

**合成 / 探索附录**（主答辩页勿当平台准确率）：

| 项 | 结果 | 脚本 / 产物 |
|----|------|-------------|
| 解析板块检出（20 条合成） | micro F1 **1.00** | `backend/scripts/eval_parse_baseline.py` |
| 真实脱敏裁决后（15 条） | micro F1 **0.98** | `eval_real_annotations.py` + `data/eval/real_parse_*adjudicated*` |
| 匹配 Rule Spearman（61 条弱标注） | 0.6543 | `eval_match_baseline.py` |
| 匹配 Semantic / Fused | 探索附录，**不作泛化结论** | 同上 |

分析结果同时返回 `evidence_coverage`、`layout_complexity`、`quality_warnings`、`score_reliability`。版式复杂度用于可信度复核，不会单独降低简历质量分。

### 4.4 模型与 Prompt 策略

- **线上主叙事**：冻结语义能力 + 结构化提示词（规范 Prompt）+ 岗位知识库 + 规则护栏  
- **不做**：用小样本真实简历强行微调基础模型当平台验收依据  
- 训练脚本 / 权重仍保留为探索附件；默认线上不加载微调权重或拟合融合器，需显式配置实验路径并注明数据口径。  
- 说明：[`docs/模型微调附件说明.md`](docs/模型微调附件说明.md)、[`docs/testing/提示词对比实验执行单.md`](docs/testing/提示词对比实验执行单.md)

### 4.5 真实简历流水线与标注收口

处理自备真实简历时使用（原始件默认不进 git）：

```bash
cd backend
.\.venv\Scripts\python.exe scripts\anonymize_resumes.py
.\.venv\Scripts\python.exe scripts\classify_resumes.py
.\.venv\Scripts\python.exe scripts\capture_bad_cases.py
```

- A 池 → 双人标注 + 第三方裁决 → 解析评测；B 池 → 能力边界；C 池 → **仅演示，禁止进训练**  
- 裁决规则 / 工作表：`docs/testing/A池分歧裁决规则与清单.md`、`A池裁决工作表.json`  
- 标注规范：[`docs/真实简历标注规范.md`](docs/真实简历标注规范.md)  
- 流水线说明：[`docs/真实简历流水线说明.md`](docs/真实简历流水线说明.md)

### 4.6 岗位库

- 数据：`data/job_market/public_job_samples.jsonl`（公开核验样本）  
- 服务：`backend/app/services/job_market.py`；导入脚本 `scripts/import_job_market.py`  
- 前端：城市 / 类别 / 学历筛选 + 关键词；详情展示相关岗位与适配依据  

---

## 五、账号与演示路线

### 5.1 账号

| 方式 | 说明 |
|------|------|
| 游客 | 打开即用；Cookie 清除后历史不可见 |
| 学生 | 右上角注册（密码≥8 位且含字母数字） |
| 管理员 | 使用 `.env` 中的 `ADMIN_USERNAME` / `ADMIN_PASSWORD` → 用户管理 / 岗位模板 / 系统管理 |
| 教师 | 管理员在「用户管理」中改角色；仅见统计，**不见简历正文** |

### 5.2 推荐 2 分钟演示（赛前主路径）

| 顺序 | 操作 | 展示要点 |
|------|------|----------|
| 1 | 上传简历 + 目标岗位 | 实时解析流 |
| 2 | 详情总览 | 「链路｜可读｜可信」分层；六维雷达 |
| 3 | 诊断与优化稿 | Diff、下载完整优化稿（不编造） |
| 4 | 岗位匹配 | 命中 / 缺失、相关岗位 Top5、适配依据 |
| 5 | （可选）再传一版 / 教师看板 | 版本 Δ 分、班级短板一键成课 |

详细话术：[`docs/演示说明.md`](docs/演示说明.md)、[`docs/答辩材料速查.md`](docs/答辩材料速查.md)。

---

## 六、（可选）Docker 一键启动

```powershell
copy .env.example .env
docker compose up -d --build
```

| 页面 | 地址 |
|------|------|
| 首页 | http://localhost:5173 |
| 健康检查 | http://localhost:8000/api/health |

停止：`docker compose down`。管理员账号以 `.env` 配置为准。

---

## 七、功能概览

**学生**：单份 / 批量分析、简历空间与版本对比、岗位库筛选与匹配依据、任务中心、报告中心、模拟面试。  

**教师**：数据看板、班级分析、学生概览（无正文）、一键成课（聚合短板模板）。  

**管理**：用户角色、岗位模板、AI / 权重配置、审计日志、存储清理。

---

## 八、AI 与离线

| 情况 | 行为 |
|------|------|
| 无 DeepSeek Key | 离线规则分析 + 本地语义（若启用模型），功能完整 |
| 有 Key 且网络正常 | 诊断 / 改写表达可增强 |
| API 失败 | 自动 `offline_fallback`，不中断 |
| 解析质量过低 | 跳过 AI 增强并提示改用可选中文本的 DOCX / PDF；可信度提示中等 / 偏低 |

---

## 九、数据与安全（简要）

- 简历默认落在本机 `data/`；未开云端 AI 时不上传第三方  
- 用户数据隔离；游客按会话隔离  
- 教师只看统计元数据  
- 真实原始简历、脱敏池默认 gitignore，不进提交包  
- 删除历史会同步清理文件  
详见 [`docs/数据安全说明.md`](docs/数据安全说明.md)。

---

## 十、常见问题

**双击 `start_dev.bat` 闪退 / Backend setup failed（Pillow）？**  
本机若默认是 Python 3.14，不要用它建环境。请安装 **Python 3.12**，删除 `backend\.venv` 后重跑。

**网页打不开？**  
确认两个窗口仍在；访问 http://127.0.0.1:5174 ；前端首次编译约数十秒。

**管理员密码不对？**  
以 `.env` 中的 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 为准。仍失败可删 `data/resume_ai_dev.db` 后重启重建。

**没有 DeepSeek 能演示吗？**  
能。证据护航 + 语义理解可离线跑通；生成交付引擎无云端 Key 时走本地模板回退，这是正式能力。

**健康检查显示 Redis 相关提示？**  
本地 `USE_CELERY=false` 时 Redis 失败应为降级而非后端整体异常；无需为演示安装 Redis。

**扫描 PDF 识别差？**  
优先用 `.docx` 或文字版 PDF；开启 OCR 后可读率上升，但可读 ≠ 板块识别准（见 L2 / L3 分栏）。

**语义模型怎么开？**  
安装 `backend/requirements-semantic.txt`，并仅在完成独立留出验证后，在 `.env` 中显式设置 `USE_SEMANTIC_MODEL=true` 和 `SEMANTIC_MODEL_PATH`。融合器还需显式设置 `SEMANTIC_BLENDER_PATH`；答辩主页勿把微调 Spearman 说成平台准确率。

---

## 十一、项目结构

```text
简历分析V2.0/
├── start_dev.bat                 ← 评委首选：双击启动
├── .env.example                  ← 配置模板
├── README.md                     ← 本文（重大更新须同步维护）
├── 技术说明.md
├── docs/
│   ├── 赛前收口完成.md           ← 证据冻结页（优先读）
│   ├── 答辩材料速查.md           ← PPT 可粘贴三层指标
│   ├── 深度优化方案.md
│   ├── 创新点与消融实验.md       ← 探索附录口径已标注
│   ├── 模型微调附件说明.md
│   ├── 真实简历流水线说明.md / 真实简历标注规范.md
│   ├── 部署指南.md / 演示说明.md / 使用说明.md / 数据安全说明.md
│   └── testing/                  ← 平台验收、裁决、OCR、Prompt 执行单
├── frontend/                     ← Vue 3 + Vite
├── backend/
│   ├── app/services/             ← 解析/评分/匹配/优化稿/岗位库/面试/流式分析…
│   ├── scripts/                  ← 评测、裁决、验收、训练、脱敏流水线
│   └── tests/
├── data/
│   ├── eval/                     ← 合成评测集、裁决后黄金标签与指标
│   ├── job_market/               ← 公开岗位库 JSONL
│   ├── models/                   ← sbert-resume-match、blender、idf
│   ├── demo/                     ← 演示/失败也可信样例说明
│   ├── lexicon/ / skill_graph.json
│   ├── raw_real_resumes/         ← 真实原始件（gitignore）
│   ├── anonymized_real_resumes/  ← 脱敏输出（gitignore）
│   └── resume_pools/             ← A/B/C 分池（gitignore）
└── docker-compose.yml
```

---

## 十二、技术栈与验证命令

| 项 | 说明 |
|----|------|
| 前端 | Vue 3 + Vite + ECharts |
| 后端 | FastAPI |
| 数据库 | 演示 SQLite；生产可 MySQL 8 |
| 语义 | sentence-transformers / 微调 text2vec-base-chinese（可选） |
| 异步 | Docker 可选 Redis + Celery；本地默认关闭 |

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_parser.py tests/test_match_engine.py tests/test_scoring.py tests/test_job_market.py -q
.\.venv\Scripts\python.exe scripts\eval_parse_baseline.py
.\.venv\Scripts\python.exe scripts\eval_match_baseline.py
.\.venv\Scripts\python.exe scripts\eval_real_annotations.py --input ..\data\eval\real_parse_annotations_adjudicated_common15.json --output ..\data\eval\real_parse_metrics_adjudicated_common15.json
.\.venv\Scripts\python.exe scripts\run_platform_acceptance.py
```

训练与探索性消融复现见 [`docs/模型微调附件说明.md`](docs/模型微调附件说明.md)。平台验收见 `docs/testing/`。

---

## 十三、文档索引

| 文档 | 用途 |
|------|------|
| **README.md（本文）** | 快速了解、启动、演示、冻结口径 |
| [`docs/赛前收口完成.md`](docs/赛前收口完成.md) | **证据冻结一页纸** |
| [`docs/口径清查清单.md`](docs/口径清查清单.md) | 提交前旧口径关键词自检 |
| [`docs/答辩材料速查.md`](docs/答辩材料速查.md) | PPT 粘贴（成功率｜可读｜可信） |
| [`docs/部署指南.md`](docs/部署指南.md) | 安装、配置、排错 |
| [`docs/演示说明.md`](docs/演示说明.md) | 现场演示顺序 |
| [`docs/使用说明.md`](docs/使用说明.md) | 功能操作 |
| [`docs/数据安全说明.md`](docs/数据安全说明.md) | 隐私与合规 |
| [`docs/深度优化方案.md`](docs/深度优化方案.md) | 已落地能力与赛前清单 |
| [`docs/创新点与消融实验.md`](docs/创新点与消融实验.md) | 消融与评测（探索附录） |
| [`docs/模型微调附件说明.md`](docs/模型微调附件说明.md) | 微调附件打包 |
| [`docs/真实简历流水线说明.md`](docs/真实简历流水线说明.md) | 脱敏 / 分拣 / Bad Case |
| [`docs/真实简历标注规范.md`](docs/真实简历标注规范.md) | 板块标注与交叉裁决 |
| [`docs/testing/平台能力验收实验方案.md`](docs/testing/平台能力验收实验方案.md) | 平台主实验边界 |
| [`docs/testing/A池分歧裁决规则与清单.md`](docs/testing/A池分歧裁决规则与清单.md) | 标注裁决执行 |
| [`docs/testing/提示词对比实验执行单.md`](docs/testing/提示词对比实验执行单.md) | Prompt 对照（替代微调主叙事） |
| [`技术说明.md`](技术说明.md) | 技术叙述 |

---

## 十四、维护约定

**重大功能、评测数字、演示路径、附件材料变更时，必须同步更新本 README**（至少更新：能力表、数字表、文档索引、结构树）。  
项目内 Cursor 规则：`.cursor/rules/readme-sync.mdc`。  
赛前口径以 [`docs/赛前收口完成.md`](docs/赛前收口完成.md) 为准：不再扩功能、不做微调主叙事。

---

**参赛团队联系方式**：2605968994@qq.com（赵文凯）
