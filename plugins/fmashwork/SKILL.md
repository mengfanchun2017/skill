---
name: fmashwork
user-invocable: true
description: |
  AI 图生 3D → 拓竹打印自动化工作流。Claude 编排：免费生成（混元3D/Meshy 网页版，Playwright MCP）
  → 本地校验（trimesh 水密/体积/流形）→ pymeshfix 修复 → 导出 STL/3MF → Bambu Studio 人工确认打印。
  用法：用户说 "meshwork" / "fmashwork" / "跑图生3D" / "3D 打印工作流" / "校验模型" 触发
allowed-tools: Read, Write, Bash, Glob, Grep,
  mcp__playwright__browser_navigate, mcp__playwright__browser_click, mcp__playwright__browser_snapshot,
  mcp__playwright__browser_fill, mcp__playwright__browser_take_screenshot, mcp__playwright__browser_wait_for
---

# fmashwork — AI 图生 3D → 拓竹打印自动化

> 个人孵化项目编排层。从描述/参考图到可打印文件的端到端管线。

## 架构（5 段）

```
输入（描述/图片）
   │
   ▼
生成段（网页免费通道）
  ├─ 腾讯混元3D 网页版（每天 ~20 次免费，Apache 2.0）
  └─ Meshy 官方网页版（每月 ~100 积分起步）
   │  ← Playwright MCP 操作浏览器
   ▼
下载段（落到 shared_dir，跨 WSL/Windows）
   │
   ▼
校验段（本地 Python：trimesh + pymeshfix）
  水密性 / 体积 / 面数 / 流形 / 孔洞修复 → 转 STL/3MF
   │
   ▼
交付段
  Bambu Studio（人工最后确认：方向/支撑/切片）→ 拓竹打印
```

## 首次安装（一次）

**无需手动装依赖** —— skill 首次调用时自动检测并安装（隔离 venv + pip，幂等）。直接跑：

```bash
python3 ~/.fmashwork-venv/bin/python scripts/fmashwork.py check-env
# 或简写：python3 scripts/fmashwork.py check-env  （会自动切到 venv + 自动装依赖）
```

- 缺依赖 → 自动执行 `scripts/setup.sh` 建 venv + 装 trimesh/pymeshfix/pygltflib/pyyaml
- **唯一可能的手动步骤**：若系统缺 `python3.x-venv`（PEP-668 需要），需一次性执行：
  `sudo apt-get install python3.14-venv`，之后重跑即可全自动
- `set -euo pipefail` + 幂等：重复运行只补装缺失，安全

> 为什么 venv：新版 Ubuntu/Debian 的 pip 有 PEP-668 保护，`pip install` 系统级报 `externally-managed-environment`。skill 用隔离 venv（`~/.fmashwork-venv`）不污染系统 Python。`fmashwork.py` 自动优先用 venv 运行；venv 不存在则用系统 python3 并触发自动安装。

## 配置

**ccconfig 用户**：真实值放 `ccprivate/skill/fmashwork.yaml`，`init-skill.sh sync` 自动 symlink 到 `~/.claude/skills/fmashwork/config.yaml`。
**独立用户**：`cp config.yaml.example config.yaml` 填入你的值。

`config.yaml` 字段说明见 `references/config-schema.md`。

---

## 工作流

### Phase 1: 环境检查（首次 / 异常时跑）

```bash
python3 scripts/fmashwork.py check-env
```

输出 WSL Python 版本、trimesh/pymeshfix/pygltflib 是否安装、`shared_dir` 是否可达。**缺依赖会自动装**（见「首次安装」）；失败项先修再继续。

### Phase 2: 生成（Playwright MCP）

打开厂商网页版 → 输入提示词/上传参考图 → 等待生成 → 下载到 `shared_dir`。

**网页免费 ≠ 免费 API**：MCP 通道（Meshy 官方/混元3D 社区版）都需要付费 API key，本 skill 默认走 Playwright 吃网页免费额度。

| 通道 | 网页免费额度 | 备注 |
|------|------|------|
| 腾讯混元3D | ~20 次/天 | 国内首选，功能最全，开源 |
| Meshy 官方 | ~100 积分/月 | 3D 打印流程最强 |

⚠️ `meshyai.net` 是冒充 Meshy 的假站，**只用 `meshy.ai`**。

### Phase 3: 校验

```bash
python3 scripts/fmashwork.py validate <shared_dir>/model.glb
```

返回水密性 / 体积 / 面数 / 流形 报告。**非水密 → 必须修复才能打印**。

### Phase 4: 修复（必要时）

```bash
python3 scripts/fmashwork.py repair <shared_dir>/model.glb <shared_dir>/model_fixed.stl
```

pymeshfix 修孔洞，重新校验一次。

### Phase 5: 转换 + 交付

```bash
# 转 STL
python3 scripts/fmashwork.py convert <shared_dir>/model_fixed.glb <shared_dir>/model.stl

# 转 3MF（含颜色/材质）
python3 scripts/fmashwork.py convert <shared_dir>/model.glb <shared_dir>/model.3mf --format 3mf
```

在 Bambu Studio 中打开 → 人工确认方向/支撑/切片 → 发送拓竹打印机。

**为什么人工最后一步不可省**：打印失败可能伤机器/材料，安全责任归属在用户。脚本只生成可打印文件，不替你打印。

---

## 何时用

| 触发 | 行为 |
|------|------|
| "meshwork" / "fmashwork" | 进入编排：按当前阶段往下走 |
| "跑图生3D" / "图生3D" / "AI 生成 3D" | 跳到 Phase 2 |
| "校验模型" / "检查模型" / "validate" | 跳到 Phase 3 |
| "修模型" / "修孔洞" / "repair" | 跳到 Phase 4 |
| "转格式" / "GLB 转 STL" | 跳到 Phase 5 |

## 工作流选择

| 场景 | 走法 |
|------|------|
| 新需求，端到端 | Phase 1 → 5 全跑 |
| 已有模型，只要校验/修复/转换 | Phase 3/4/5 |
| 测试新厂商 | Phase 2 单跑，看生成质量 |

## 命令速查

```bash
# 一行完成：校验 + 修复 + 转换
python3 scripts/fmashwork.py pipeline <input> --output <output_dir>
```

详见 `scripts/fmashwork.py --help`。

## 安全 / 隐私

- 本 skill 不上传任何模型到云端（除厂商生成 API）
- 校验/修复/转换全部本地 Python
- 飞书 wiki node / token 走 `config.yaml`(ccprivate)，不进公开仓库

## 相关

- 调研：[[ai-image-to-3d-tools-landscape-2026]] — 国产图生3D 工具格局
- 案例：vibe-print / Claudeware / meshy-3d-printing skill（公开 GitHub 可搜）
