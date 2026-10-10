---
name: fwriteorch
user-invocable: true
description: |
  撰写系统统一入口（路由层）。读体裁注册表判断需求属于哪种体裁（课程/报告/案例），
  派发到对应 orchestrator（forchcourse/forchreport/forchcase）。用户只描述需求，无需记内部 skill 名。
  用法：用户说"做课程"/"写报告"/"新增案例"等撰写需求时触发
allowed-tools: Read, Bash, Glob, Grep
---

# fwriteorch — 撰写系统统一入口（L4）

职责：需求 → 判体裁 → 派 orchestrator。**不自己撰写**，只做路由。

## 架构

```
用户需求（自由描述）
  └─ fwriteorch 读注册表 → 判体裁 → 派发
       ├─ course  → forchcourse   （系列课程）
       ├─ report  → forchreport   （报告）
       └─ case    → forchcase     （案例库）
```

四层：`fwriteorch`(L4 路由) → `orch*`(L3 编排) → `fstd-*`(L2 规范) → `ffeishu`+工具(L0 机械)。
架构决策见 `ccconfig/docs/adr/0043-writing-system-architecture.md`。

## 步骤

### Step 1: 读体裁注册表

```bash
cat "${CCPRIVATE_HOME:-$HOME/git/ccprivate}/conf/writing/registry.yaml"
```

注册表 `genres` 下每条含：`trigger`（触发词）/ `orchestrator`（编排器）/ `spec`（规范）/ `config`（真值文件）/ `outputs`。

### Step 2: 判体裁

按用户输入匹配 `trigger`；不明确时用 AskUserQuestion 让用户选（course/report/case）。

判出体裁 → 读该体裁的 `config` 真值文件（父目录/根文档 token 等）：

```bash
cat "${CCPRIVATE_HOME:-$HOME/git/ccprivate}/conf/writing/<genre>.yaml"
```

### Step 3: 派发

把控制权交给对应 orchestrator（用 Skill 工具调用，或按用户话术直接进入其流程）：

| 体裁 | 编排器 | 规范 |
|------|--------|------|
| course | `forchcourse` | `fstd-course` |
| report | `forchreport` | `fstd-report` |
| case | `forchcase` | `fstd-case` |

**降级（注册表缺失时）**：按触发词直接映射——"课程"→forchcourse / "报告"→forchreport / "案例"→forchcase，父目录用各 skill 内置默认（`ffeishu` 默认 wiki 节点）。不阻断。

## 约定

- **飞书在线 = 唯一真相源**，本地 yaml 仅镜像（见注册表 `defaults.online_source_of_truth`）
- **真实 token/父目录只在 `ccprivate/conf/writing/`**，公开仓库零真实值
- 格式规则统一走 `ffeishu`（`references/write-checklist.md` 为真相源）

## 关联

- `forchcourse` / `forchreport` / `forchcase` — 编排层
- `fstd-course` / `fstd-report` / `fstd-case` — 体裁规范层
- `ffeishu` / `fdiagram` / `fpptx` — 机械层
