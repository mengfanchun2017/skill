---
name: flibaudit
user-invocable: true
description: 仓库全面审计 — 大变更后对 lib 完整审核：架构/代码/文件卫生/测试/文档/发布就绪。更新测试并跑功能测试修复 bug。面向个人小项目，默认本地 markdown 报告，飞书 opt-in。用法：用户说"审计仓库"/"代码审计"/"lib审计"/"上线前审计"/"发布审计"、或大变更后需要完整质量审查时触发。
allowed-tools: Bash, Read, Write, Edit, Agent, Grep, Glob, WebSearch, mcp__tavily__tavily_search, mcp__tavily__tavily_extract, Skill, EnterPlanMode, ExitPlanMode, AskUserQuestion
---

# flibaudit — 仓库全面审计

## 概述

**大变更后对 lib 的完整审核**：架构 → 代码 → 文件卫生 → 测试 → 文档 → 发布就绪。审计不是只看，**发现 bug 当场修**，测试跟不上当场补。面向个人/小团队项目（单人维护、无 review 流程、main 直推）。报告默认本地 markdown，飞书 opt-in。

## 定位

- **触发时机**：一次大变更后（重构、新功能、架构调整），对整个 lib 做完整质量收尾
- **目标项目**：个人项目、小团队仓库。不追求企业级合规
- **单仓库为主**：多仓库审计可选，最后汇总
- **轻量优先**：能内联做的不用 Agent，能本地输出的不上飞书
- **实用导向**：solo 项目不需要的治理文件直接标删

## lib 结构更新定位

flibaudit **产出结构更新建议但不执行重组**——审计只诊断，重组是开发决策。架构审计阶段输出结构建议（拆分大文件、提取公共库、重命名一致性），列为 P2 改进项，用户决定后单独执行。

> **无专门"lib 结构更新"skill**。`fsysarchi` 是软考备考 skill，不适用。结构重组建议作为 flibaudit P2 输出，执行由用户批准后走正常开发流程。

## 配置

报告输出选择：
- **本地 markdown（默认）** → `docs/audit/audit-YYYY-MM-DD.md`（或仓库根）
- **飞书文档（opt-in）** → 仅当用户明确要求"写飞书"/"出飞书报告"。需 lark-cli 已认证 + 委托 `ffeishu` skill 编排格式

## 审计流程

### Phase 0: 范围确认

快速确认（有默认值，不卡流程）：
- 审计哪个仓库？（默认：当前仓库）
- 深度？（快速扫描 / 标准 / 深度，默认标准）
- 关注领域？（默认全维度；可指定安全/性能/可维护性）
- 仓库类型？（ccconfig 型 / 普通项目 / 第三方 fork — 影响检查重点）

**深度审计时**：设计审查用 Claude 内置能力——直接对关键设计决策提问（架构边界、依赖方向、扩展策略），或 spawn `Plan` agent 出设计问题清单作为审计输入。不依赖 grill-me skill（已废弃）。

### Phase 1: 架构审计

1. 目录树（`tree -L 3 -I 'node_modules|.git|__pycache__|*.log'`）
2. 识别组件边界：核心 vs 工具 vs 胶水
3. 依赖方向：有无循环依赖、跨层调用
4. **调用图完整性**：所有次级脚本至少被一个根脚本按层级调用；无人 source/调用且无生产引用的文件标 dead-at-runtime（有测试覆盖可保留，否则删）
5. 文件大小分布（超大文件 >500 行标记，但已主动管理的大文件不强拆）
6. 模块耦合度

**关键架构规则（ccconfig 型仓库）**：
- **根脚本串接 option**：根入口脚本（`init-base.sh`/`init-option.sh`/`maintain.sh`）通过动态枚举（`has_init_script`/`install_option`）串接 `option-*/init.sh`，用户无需单独跑 option 即可全装
- **option 可独立执行**：每个 `option-*/init.sh` 支持手动单独跑（`--install`/`--run` 子命令），必须保留
- **根脚本间不互相直调**：除定义的入口点外，根脚本不直接调用彼此
- **auth 类 option 自动跳过**：`--yes` 非交互模式下，需扫码/配 key 的 option（larkcli/getnote）自动跳过 + 提示

调 `Plan` agent 或内联分析获取架构优化建议。结构重组建议列为 P2。

### Phase 2: 代码审计 + bug 修复

**按项目规模选模式**：
- 小仓库（<20 文件）：内联扫，不分 Agent
- 中大仓库：Agent 并行跑维度

| Agent | 审计内容 |
|-------|----------|
| Agent A: 安全 | 密钥泄露、注入、权限风险 |
| Agent B: 质量 | 重复代码、死代码、硬编码、错误处理 |
| Agent C: SH 专项 | `.sh` 文件（清单见 REFERENCE.md） |

严重程度分级（P0/P1/P2，详见 REFERENCE.md）：
- **P0 安全/阻断**：密钥泄露、`.gitignore` 与 track 冲突、注入、公开仓库含私有数据
- **P1 代码质量**：重复 3+、死代码、硬编码、错误处理缺失、set -u 下无参崩溃（`${1}` → `${1:-}`）、pipefail 下管道恒 false（`cmd | grep` 当 cmd 永远非零）、拼写错误死分支
- **P2 改进**：可提取公共库、命名不一致、注释过期、结构重组建议

**P0/P1 当场修**：每个发现先与用户确认，确认后直接 Edit 修复，修完跑 `bash -n` 验证语法。P2 批量列建议，不擅自改。

### Phase 3: 文件卫生审计（solo 项目重点）

solo 项目不需要企业治理开销。逐文件评估必要性：

| 文件 | solo 项目处理 |
|------|--------------|
| `CITATION.cff` | 删（除非学术发布） |
| `CODE_OF_CONDUCT.md` | 删（无协作方） |
| `CONTRIBUTING.md` | 删（无外部贡献者） |
| `SECURITY.md` | 删（除非有外部安全上报需求） |
| `ROADMAP.md` | 删（基本功能完成后无意义） |
| `skills-lock.json` / 其他 lock | 评估：有对应 skill 管理机制则留，否则删 |
| 项目级 `CLAUDE.md` | **必要性评估**：若项目对应 user 级配置，检查项目级是否有独有内容（暗号、常用命令、项目约束）。有独有内容则留，与 user 级重复则删重复部分 |
| `LICENSE` | 留（开源必备） |

原则：**不确定先问用户，不擅自删文件**。删之前 grep 确认无引用。孤立文档（0 引用但内容有用）选择链接而非删除。

### Phase 4: 测试审计与修复（大变更后重点）

**先更新测试，再跑测试，再修 bug**。

1. **测试覆盖对齐**：`ls tests/` 对照 `lib/*.sh` + 根脚本。新增 lib 无测试 → 补；删掉的 lib 有残留测试 → 删；接口变了 → 改测试。每模块对应一个 `tests/test-<module>.sh`
2. **语法全检**：`bash tests/test-syntax.sh`（所有 .sh 跑 `bash -n`），零成本快速发现问题
3. **功能测试套件**：逐个跑 `tests/test-*.sh`，记录 pass/fail
4. **修复失败**：测试失败 → 定位（测试过期还是代码 bug）→ 修对应方 → 重跑直到全绿
5. **defer 判断**：边界 case 风险高的、有意为之的（如 word-splitting 传参）、不可能触发的（如已验证无特殊字符的插值），评估后 defer 并记录原因，不强改

测试参考模式：`test-syntax.sh`（bash -n 全检）、`test-init-option.sh`（模块功能）、`test-interact.sh`（库函数）。

### Phase 5: 文档审计

三维度：
1. **准确性** — 路径引用存在？版本号正确？命令可执行？
2. **清晰度** — 新手能看懂？步骤无跳跃？术语一致？
3. **完整性** — README/BOOTSTRAP/CHANGELOG 齐全？（solo 项目 CONTRIBUTING 非必须）

重点文件：`README.md`、`BOOTSTRAP.md`、`CHANGELOG.md`、`docs/`（含 `docs/adr/`）。

**ADR 审计**：检查 `docs/adr/` 是否过期/失效。重点查：
- 状态反映现状（Proposed/Accepted/Superseded/Deprecated）
- **编号冲突**（同编号两个 ADR——重号，一个重编号）
- 被 supersede 的旧 ADR 标注指向新 ADR
- 断链（索引引用已删 ADR，或 ADR 引用不存在的编号）
- 索引与实际文件一致

### Phase 6: 发布就绪

1. **可见性** — 公开仓库 public？私有 private？
2. **安全终扫** — `grep -rE '(api_key|token|secret|password)\s*=' --include='*.{yaml,yml,json,sh,py,js,ts}'` 排除占位符
3. **初始化模拟** — 干净环境走一遍 BOOTSTRAP，验证可执行
4. **版本一致性** — `conf/versions.json` vs `package.json` vs git tag
5. **公开仓库保密** — 无真实 IP/域名/密钥/用户名（ccconfig 型仓库重点）

### Phase 7: 审计报告 + 后续

各维度结果汇总为统一报告（模板见 REFERENCE.md）。

**输出选择**：
- **本地 markdown（默认）**：写 `docs/audit/audit-YYYY-MM-DD.md`，终端输出路径链接
- **飞书文档（opt-in）**：仅当用户明确要求。写前 lark-cli auth 预检，格式委托 `ffeishu` skill，写后更新 `recent_feishu_docs.md`

报告必须包含：日期、范围、发现汇总、修复记录、defer 项及原因、残余风险、结论。

**报告完成后询问用户**：是否调 `/fsyncdoc` 同步文档和产品页内容？大变更后文档/网页通常需同步，fsyncdoc 处理源码→文档→产品页映射。用 `AskUserQuestion` 问。

## 关键约束

- 每个 P0/P1 发现先讨论再修，修完跑 `bash -n` + 相关测试验证
- 每阶段修改代码后更新对应文档（README/BOOTSTRAP/CHANGELOG）
- 删文件前 grep 确认无引用，不确定问用户；孤立有用文档选链接非删除
- defer 项必须记录原因（风险高/有意为之/不可能触发/纯样式 churn）
- 审计报告必须含：日期、范围、发现汇总、修复记录、defer 项、残余风险、结论
- 调 external skill（ffeishu/fsyncdoc）时遵守目标 skill 前置条件
- **不默认上飞书**：小项目本地 markdown 足够，飞书是可选项
- **测试是审计一部分**：不只看测试结果，要先更新测试对齐当前代码
