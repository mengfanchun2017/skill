---
name: flibaudit
description: 仓库全面审计 — 从架构到代码到文档到测试，输出审计报告到飞书文档。Use when 用户说"审计仓库"/"代码审计"/"lib审计"/"上线前审计"/"发布审计"、或需要对仓库做多维度质量审查。
---

# f-libaudit — 仓库全面审计

## 概述

对仓库执行 4 阶段结构化审计：架构 → 代码 → 文档 → 发布就绪。每个阶段记录发现并按 P0/P1/P2 分级。最终生成审计报告写入飞书文档。

## 配置

> 📖 完整说明 → [config.aiagt.dev](https://config.aiagt.dev/f-libaudit)

审计报告输出到飞书文档 → 需 lark-cli 已认证（`lark-cli auth login`）。
飞书文档格式约束由 `f-feishu` 编排，本 skill 委托 f-feishu 创建文档。

## 前置

审计开始前先 `lark-cli auth` 预检（参考 [[feishu.md]] § auth 预检）。飞书文档格式约束调用 `f-feishu` Skill。

## 审计流程

### Phase 0: 范围确认

询问用户：
- 审计哪些仓库？（多仓库则逐个审计，最后汇总）
- 审计深度？（快速扫描 / 标准审计 / 深度审计）
- 是否有特定关注领域？（安全、性能、可维护性...）

### Phase 1: 架构审计

1. 获取仓库目录树 (`tree -L 3 -I 'node_modules|.git|__pycache__'`)
2. 识别组件边界：哪些是核心、哪些是工具、哪些是胶水
3. 检查依赖方向：有无循环依赖、跨层调用
4. 检查文件大小分布（超大文件可能需要拆分）

输出：架构图（文字描述） + 发现列表

### Phase 2: 代码审计

按严重程度分级：

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

每发现一个 P0/P1 问题，先与用户讨论再修。P2 批量处理。

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

### Phase 5: 审计报告

所有阶段完成后，生成审计报告（格式见 REFERENCE.md）。**默认写入飞书文档**。更新 `recent_feishu_docs.md`。

## 关键约束

- 每个 P0/P1 发现先讨论再修，不擅自改动
- 每个阶段修改代码后更新对应文档
- 多仓库审计先分别审计，最后出汇总报告
- 审计报告必须包含：日期、范围、发现汇总、修复记录、残余风险
