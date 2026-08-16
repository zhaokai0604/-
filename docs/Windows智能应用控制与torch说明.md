# Windows 智能应用控制与 torch 说明

> 记录时间：2026-08-02  
> 目的：本机安装 `torch` / `sentence-transformers` 做 SBERT 微调时，被「智能应用控制」拦截 DLL；曾修改注册表关闭该策略。怕日后忘记，特此留档。

---

## 1. 现象

导入 torch 时报错（包装上了但跑不起来）：

```text
ImportError: DLL load failed while importing _C: 应用程序控制策略已阻止此文件。
```

常见原因：Windows 11 **智能应用控制（Smart App Control, SAC）** 拦截了 `torch` 的本地 DLL。

---

## 2. 实际改了什么（不是清空注册表）

只改了 **一个 DWORD 键**：

| 项 | 值 |
|----|-----|
| 路径 | `HKLM\SYSTEM\CurrentControlSet\Control\CI\Policy` |
| 名称 | `VerifiedAndReputablePolicyState` |
| 修改前 | `1`（开启 / 强制） |
| 修改后 | `0`（关闭） |

含义：关闭智能应用控制。

**没有**做整机注册表清空，也没有批量删除其他键。

查当前值（PowerShell）：

```powershell
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy" |
  Select-Object VerifiedAndReputablePolicyState
```

- `0` = 关  
- `1` = 开（强制）  
- `2` = 评估模式（若系统支持）

改完后通常需要 **重启** 才会完全生效。

---

## 3. 影响

| 方面 | 说明 |
|------|------|
| 对本项目 | `torch` 可正常 `import`，才能跑 `backend/scripts/train_sbert.py` |
| 日常使用 | 一般无感 |
| 安全 | 少了一层「只允许信誉好的应用运行」的防护；Windows Defender 等仍在 |
| 可逆性 | 注册表可改回 `1`，但微软对 SAC 的策略往往是：**关掉后很难再完整打开**，有时需重置/重装系统 |

---

## 4. 如何改回（尽量恢复）

### 4.1 改注册表（需管理员 PowerShell）

```powershell
Set-ItemProperty `
  -Path "HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy" `
  -Name "VerifiedAndReputablePolicyState" `
  -Value 1 `
  -Type DWord
```

然后 **重启电脑**。

### 4.2 用系统设置确认

**设置 → 隐私和安全性 → Windows 安全中心 → 应用和浏览器控制 → 智能应用控制**

若界面仍无法重新开启，属于 Windows 已知限制，不是本项目又改坏了别的东西。

### 4.3 再次关闭（若以后又要训模型）

```powershell
Set-ItemProperty `
  -Path "HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy" `
  -Name "VerifiedAndReputablePolicyState" `
  -Value 0 `
  -Type DWord
```

重启后验证：

```powershell
cd backend
.\.venv\Scripts\python.exe -c "import torch; import sentence_transformers; print(torch.__version__, sentence_transformers.__version__)"
```

---

## 5. 与本项目的关系（备忘）

- 可选依赖说明：`backend/requirements-semantic.txt`
- 微调脚本：`backend/scripts/train_sbert.py`
- 权重目录：`data/models/sbert-resume-match/`
- 环境变量：`.env` 中 `USE_SEMANTIC_MODEL=true`，可选 `SEMANTIC_MODEL_PATH`
- 国内拉基座模型可设：`HF_ENDPOINT=https://hf-mirror.com`

**不微调、不用向量模型时**：保持 `USE_SEMANTIC_MODEL=false` 即可，系统仍可用 jieba 语义基线，**不必**为日常跑服务长期关 SAC。

---

## 6. 一句话结论

为跑通本地 torch，曾把智能应用控制对应注册表从 `1` 改为 `0`；影响面小、可记可查；改回注册表简单，但系统是否允许再次完整开启 SAC 以 Windows 自身策略为准。
