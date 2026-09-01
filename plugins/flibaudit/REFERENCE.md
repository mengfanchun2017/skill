# flibaudit 审计清单

> SKILL.md 的展开参考。Phase 编号与 SKILL.md 一致。

## Phase 1: 架构审计清单

- [ ] 目录树获取完整（`tree -L 3 -I 'node_modules|.git|__pycache__|*.log'`）
- [ ] 识别核心模块 vs 工具模块 vs 胶水代码
- [ ] 依赖方向检查（核心不依赖工具，工具可依赖核心）
- [ ] 调用树检查：根脚本（根下 *.sh）不互相调用；所有次级脚本至少被一个根脚本按层级调用
- [ ] **间接调用规则**：`option-*/init.sh` 通过 `init-option.sh` 动态枚举（`has_init_script` / `install_option`）或 `option_status` 调用即视为有根入口。不要求根脚本硬编码调用每个 option init.sh
- [ ] **串接契约**：根脚本能串接 option（`init-base.sh all` → `init-option.sh all`），用户无需单独跑 option
- [ ] **option 独立可执行**：每个 `option-*/init.sh` 支持 `--install`/`--run` 手动单独跑
- [ ] **auth 类 option 非交互跳过**：`--yes` 模式下 larkcli/getnote 等需手动配置的 option 自动跳过 + 提示
- [ ] 超大文件标记（>500 行建议审查是否需拆分）
- [ ] 无用文件标记（空文件、注释全部删除的文件）
- [ ] 死代码检测：无人 source/调用且无生产引用的文件标记删除
- [ ] 目录命名一致性（kebab-case / snake_case 统一）
- [ ] Plan agent / 内联分析建议与手动发现交叉验证

## Phase 2: 代码审计清单

### P0 — 安全/阻断
- [ ] `grep -rE '(api.?key|token|secret|password|AUTH_TOKEN)\s*[=:]' --include='*.{yaml,yml,json,sh,js,ts,py,env}'` 检查密钥
- [ ] `.gitignore` 条目是否已 track（`git ls-files` 对 `.gitignore` 内容验证）
- [ ] 公开仓库不含任何 `.env` / `credentials.*` / 私有 config
- [ ] 无 `eval()` / `exec()` 动态执行用户输入
- [ ] 无 shell 注入（`os.system()` 接用户输入）

### P1 — 代码质量
- [ ] 相同逻辑块出现 ≥3 次 → 提取公共函数/库
- [ ] 函数超过 100 行 → 建议拆分
- [ ] 硬编码路径（`/home/francis/` 等个人路径）
- [ ] 已删除功能的引用（import 不存在的模块）
- [ ] 废弃代码块（被注释掉的大段代码）

### P2 — 改进建议
- [ ] 命名不一致（同一概念多个名字）
- [ ] 注释与代码不符
- [ ] 缺少错误处理（网络请求、文件操作）
- [ ] 文件组织（相关文件散落多处）
- [ ] 过时的 TODO/FIXME

## SH 审计清单（项目含 `.sh` 文件时启用）

以 ccconfig `sh-script-standards.md` 为检查标准。

### P0 — 安全/阻断
- [ ] 危险命令：`rm -rf` 无保护、`git reset --hard`、`chmod 777`、`sudo`（apt-get 除外）
- [ ] 密钥/Token 硬编码在脚本中
- [ ] 存在命令注入（未引用的变量接 `eval` / 动态拼接用户输入）

### P1 — 质量
- [ ] 缺少 `set -euo pipefail`（不可预期错误不终止）
- [ ] `SCRIPT_DIR` 未用 `BASH_SOURCE[0]` 定义（用 `$0` 或硬编码路径）
- [ ] 自定颜色变量（`RED='\033[0;31m'` 等）而非 `source lib/colors.sh`
- [ ] 菜单 `case` 无 `0)` 返回/退出路径（死循环无法退出）
- [ ] 菜单输入检查未用 `[[ "$choice" =~ ^[0-9]+$ ]]`
- [ ] 写操作类脚本（调 MCP/LLM/网络请求）未 source `lib/dry-run.sh`
- [ ] `--status` 首行非 `OK | WARN | MISSING` 格式（供 init-option 解析）
- [ ] 函数用 `function` 关键字（非 `name()` 格式）
- [ ] `local var` 未初始化（set -u 下立即引用触发 unbound，须 `local var=""`）

### P2 — 改进
- [ ] 缩进 tab/4空格混合（统一 4 空格）
- [ ] 函数内未用 `local` 声明局部变量
- [ ] 无 `#!/bin/bash` shebang
- [ ] 文件头缺少功能描述注释（`# xxx.sh — 一句话描述`）
- [ ] case 的 `;;` 未与 `case`/`esac` 对齐
- [ ] Edit 后未跑 `bash -n`（防 P0 行合并 bug）

## Phase 3: 文件卫生审计清单（solo 项目重点）

逐文件评估必要性，不确定先问用户：

- [ ] `CITATION.cff` — 非学术发布则删
- [ ] `CODE_OF_CONDUCT.md` — 无协作方则删
- [ ] `CONTRIBUTING.md` — 无外部贡献者则删
- [ ] `SECURITY.md` — 无外部安全上报需求则删
- [ ] `ROADMAP.md` — 基本功能完成后无意义则删
- [ ] `skills-lock.json` / 其他 lock — 评估有无对应管理机制，无则删
- [ ] 项目级 `CLAUDE.md` — 与 user 级 `~/CLAUDE.md` 对比，删重复部分，保留独有内容（暗号/常用命令/项目约束）
- [ ] 删文件前 `grep -r <filename>` 确认无引用
- [ ] `.example` 模板同步方向（只跟踪模板，真实值在 ccprivate/`.gitignore`）
- [ ] 无用的 `.snapshot`/`.bak`/`*.tmp` 残留

## Phase 4: 文档审计清单

### 准确性
- [ ] 所有路径引用指向存在的文件
- [ ] 命令示例可直接复制执行
- [ ] 版本号与 `conf/versions.json` / git tag 一致
- [ ] 依赖列表与 `package.json` / `requirements.txt` 一致
- [ ] 无指向已删除功能的描述

### 清晰度
- [ ] README 第一屏说清项目是什么
- [ ] 安装步骤无跳跃（每一步都有命令或说明）
- [ ] 术语全文一致（不混用同义词）
- [ ] 目录树与实际结构一致
- [ ] 代码示例有输出示例

### 完整性
- [ ] `README.md` — 项目说明
- [ ] `BOOTSTRAP.md` — 初始化（solo 项目核心文档）
- [ ] `CHANGELOG.md` — 变更记录
- [ ] `docs/` — 补充文档
- [ ] 单 skill/模块的安装说明
- [ ] CONTRIBUTING/SECURITY — solo 项目非必须（Phase 3 已评估删除）

### ADR 审计
- [ ] `docs/adr/` 存在的决策状态反映现状
- [ ] 状态合法：Proposed / Accepted / Superseded / Deprecated
- [ ] 被 supersede 的旧 ADR 标注指向新 ADR 编号
- [ ] 无断链（引用不存在的 ADR）
- [ ] 决策内容与当前代码实际一致（过时决策标 Deprecated）

## Phase 5: 发布就绪清单

- [ ] 可见性：公开→public、私有→private
- [ ] 安全终扫：`grep -rE '(api.?key|token|secret|password|AUTH_TOKEN)\s*[=:]\s*["\x27]?[a-zA-Z0-9_-]{20,}' --include='*.{yaml,yml,json,sh,js,ts,env}'` 无命中
- [ ] 初始化模拟：干净环境走完整流程，无报错
- [ ] 版本一致性交叉验证
- [ ] 依赖无过期且有安全漏洞的版本
- [ ] git tag 存在且推送到 remote
- [ ] 公开仓库保密：无真实 IP/域名/密钥/用户名/邮箱/公司名

## Phase 2 并行审计 Agent 分配

| Agent | Label | 审计内容 | 产出 |
|-------|-------|----------|------|
| Agent A | `audit:security` | P0 安全项 | 密钥发现 + 注入点列表 |
| Agent B | `audit:quality` | P1-P2 质量项 | 重复/死代码/硬编码清单 |
| Agent C | `audit:sh` | SH 专项 | SH 脚本合规问题清单 |

小仓库（<20 文件）内联扫，不分 Agent。中大仓库用 Agent 并行，结果汇总到 Phase 6。

## 审计报告模板

```markdown
# {仓库名} v{版本号} 审计报告

**日期**: YYYY-MM-DD
**审计范围**: 架构 / 代码 / 文件卫生 / 文档 / 发布就绪
**审计级别**: 快速 / 标准 / 深度
**输出**: 本地 markdown / 飞书文档

## 1. 总体评估

| 维度 | 评级 | 说明 |
|------|------|------|
| 架构 | A/B/C/D | 一句话 |
| 代码 | A/B/C/D | 一句话 |
| 文件卫生 | A/B/C/D | 一句话 |
| 文档 | A/B/C/D | 一句话 |
| 安全 | A/B/C/D | 一句话 |
| 发布就绪 | ✅/⚠/❌ | 一句话 |

## 2. 发现汇总

| 级别 | 数量 | 已修复 | 遗留 |
|------|------|--------|------|
| P0 | N | N | N |
| P1 | N | N | N |
| P2 | N | N | N |

## 3. P0 发现

| # | 文件 | 问题 | 修复 |

## 4. P1 发现

| # | 文件 | 问题 | 修复 |

## 5. P2 改进

| # | 文件 | 建议 | 状态 |

## 6. 文件卫生

| 文件 | 处理 | 原因 |

## 7. 文档修复

| 文件 | 修复数 | 主要问题 |

## 8. ADR 状态

| ADR | 原状态 | 现状态 | 说明 |

## 9. 变更文件汇总

| 文件 | 变更类型 | 说明 |

## 10. 残余风险

{如果 P0/P1 有未修复项，在此列出原因和缓解措施}

## 11. 结论

{是否可以发布。如有阻塞项，说明条件。}
```

## 严重级别定义

| 级别 | 含义 | 行动 |
|------|------|------|
| **P0** | 阻断发布。安全漏洞、数据泄露、公开仓库含私密信息 | 必须修复 |
| **P1** | 影响质量。重复代码、死代码、错误处理缺失 | 强烈建议修复 |
| **P2** | 改进建议。命名、组织、文档完善 | 建议修复 |
