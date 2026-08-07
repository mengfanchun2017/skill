---
name: flibaudit
user-invocable: true
description: 仓库全面审计 — 从架构到代码到文档到测试，输出审计报告到飞书文档。Use when 用户说"审计仓库"/"代码审计"/"lib审计"/"上线前审计"/"发布审计"、或需要对仓库做多维度质量审查。
allowed-tools: Bash, Read, Write, Edit, Agent, Grep, Glob, WebSearch, mcp__tavily__tavily_search, mcp__minimax__web_search
---

# flibaudit — 仓库全面审计

## 概述

对仓库执行结构化审计：架构 → 代码 → 文档 → 发布就绪。利用 Claude 内置工具（`/review`、`diagnosing-bugs`、`improve-codebase-architecture`、`grill-me`）自动化和并行化审计。审计报告写入飞书文档。

## 配置

> 完整说明 → [config.aiagt.dev](https://config.aiagt.dev/flibaudit)

审计报告输出到飞书文档 → 需 lark-cli 已认证。
飞书文档格式约束由 `ffeishu` 编排，本 skill 委托 ffeishu 创建文档。

## 前置

审计开始前先 `lark-cli auth` 预检（参考 [[feishu.md]] § auth 预检）。飞书文档格式约束调用 `ffeishu` Skill。

## 审计流程

### Phase 0: 范围确认

询问用户：
- 审计哪些仓库？（多仓库用 Agent 并行审计，最后汇总）
- 审计深度？（快速扫描 / 标准审计 / 深度审计）
- 是否有特定关注领域？（安全、性能、可维护性...）
- 仓库类型？（ccconfig / 普通项目 / 第三方 fork — 不同仓库审计重点不同）

**深度审计时**：先调 `grill-me` skill 走设计审查 interview，输出设计问题清单作为审计输入。

### Phase 1: 架构审计

1. 获取仓库目录树（`tree -L 3 -I 'node_modules|.git|__pycache__'`）
2. 识别组件边界：核心 vs 工具 vs 胶水
3. 检查依赖方向：有无循环依赖、跨层调用
4. 检查文件大小分布（超大文件需拆分）
5. 检查模块间耦合度

**调 `improve-codebase-architecture` skill** 获取自动化架构优化建议，与手动发现交叉验证。

输出：架构图（文字/文字时序） + 发现列表

### Phase 2: 代码审计

**并行分维度**：用 Agent 并行跑多个维度审计，而非串行：

| Agent | 审计内容 |
|-------|----------|
| Agent A: 安全审计 | 密钥泄露、注入、权限风险 |
| Agent B: 质量审计 | 重复代码、死代码、硬编码、错误处理 |
| Agent C: SH 审计 | `.sh` 文件专项（见 SH 专项清单） |

**深度审计时**：额外调 `/review` 命令对全仓库做自动化代码审查，结果纳入审计报告。

按严重程度分级（详见 REFERENCE.md § Phase 2 清单）：

**P0 — 安全/阻断**：
- 密钥泄露（API key, token, password）
- `.gitignore` 与已 track 文件冲突
- 命令注入、SQL 注入
- 公开仓库含私有数据

**P1 — 代码质量**：
- 重复代码（同逻辑出现 3+ 次）
- 死代码（已删除功能残留）
- 硬编码路径/URL
- 错误处理缺失

**P2 — 改进建议**：
- 可提取的公共库
- 命名不一致
- 注释过期
- 文件组织优化

### SH 脚本专项（项目含 `.sh` 文件时启用）

以 ccconfig `sh-script-standards.md` 为标准，检查项详见 REFERENCE.md § SH 审计清单。

每发现一个 P0/P1 问题，先与用户讨论再修。P2 批量处理。
`diagnosing-bugs` skill 可用于深入分析可疑的 bug 模式。

### Phase 3: 文档审计

三个维度：

1. **准确性** — 路径引用存在？版本号正确？命令可执行？
2. **清晰度** — 新手能看懂？步骤无跳跃？术语一致？
3. **完整性** — README/BOOTSTRAP/CONTRIBUTING/CHANGELOG 齐全？

重点检查文件：
- `README.md` — 项目说明、安装、使用
- `BOOTSTRAP.md` — 初始化流程
- `CONTRIBUTING.md` — 贡献指南
- `CHANGELOG.md` — 变更记录
- `docs/` — 所有子文档

### Phase 4: 发布就绪

1. **可见性检查** — 公开仓库是否为 public？私有仓库是否 private？
2. **安全终扫** — `grep -rE '(api_key|token|secret|password)\s*=' --include='*.{yaml,yml,json,sh,py,js,ts}'` 排除占位符
3. **初始化模拟** — 从零开始走一遍安装流程，验证 BOOTSTRAP 可执行
4. **版本一致性** — `conf/versions.json` vs `package.json` vs git tag

### Phase 5: 审计报告汇总

各维度 Agent 返回结果后，用 **Agent 汇总合并**为统一审计报告（格式见 REFERENCE.md）。**默认写入飞书文档**。更新 `recent_feishu_docs.md`。

写入飞书前再次 `lark-cli auth` 预检（避免创建时过期）。

## 关键约束

- 每个 P0/P1 发现先讨论再修，不擅自改动
- 每个阶段修改代码后更新对应文档
- 多仓库审计先分别审计，最后出汇总报告
- 审计报告必须包含：日期、范围、发现汇总、修复记录、残余风险
- 调 external skill 时遵守目标 skill 的前置条件