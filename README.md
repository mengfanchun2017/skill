# claude-skills — mengfanchun2017 的 Claude Code skill 集合

> Claude Code 技能聚合仓。**8 个自建 + 1 个外部 monorepo 引用**，一个 marketplace，一次安装。
> 飞书 / 调研 / 文档 / PPT / PDF / AI 浏览器一站式。

## 快速开始

在 Claude Code 里执行一行命令：

```
/plugin marketplace add mengfanchun2017/claude-skills
```

然后挑你需要的装：

```
/plugin install f-pdf@mengfanchun2017-skills
/plugin install f-doc@mengfanchun2017-skills
/plugin install mattpocock-skills@mengfanchun2017-skills
```

后续更新：

```
/plugin marketplace update mengfanchun2017-skills
```

## 自建 skill（8 个，仓内）

| Skill | 说明 |
|-------|------|
| `f-doc` | 飞书文档统一入口（wiki/表格/白板/PPT、报告整合/拆分/转换/对比） |
| `f-ppt` | PPT 生成（双引擎：ppt-master + OfficeCLI） |
| `f-pdf` | PDF 内容提取（PyMuPDF：文字/图片/表格/元数据） |
| `f-research` | 快速研究（三源并行：Tavily + MiniMax + WebSearch） |
| `f-research-deep` | 深度研究（批量 JSON 输出） |
| `f-research-report` | 报告生成（JSON/大纲/素材 → 结构化 Markdown） |
| `f-report-std` | 报告写作横向规范（4 套模板：研究/分析/对比/方案）|
| `f-vessel` | AI 浏览器操控（Vessel MCP，需配套 option-vessel/ 安装器） |

## 外部 skill（1 monorepo + 系统层 lark-cli）

### 飞书操作 — 不走 plugin，走 npm 全局 lark-cli

**飞书 lark-* skill 不在 marketplace**（2026-06-06 重构移除）。
原因：larksuite/cli 是 monorepo，一次 plugin install 暴露 26 个 lark-* skill，dialog 太噪音。
解决：`npm install -g @larksuite/cli` 装 CLI，由 **f-doc 编排**所有飞书操作（f-doc 直接调 `lark-cli docs/base/sheets/wiki/...` 命令，不依赖 lark-* skill）。

```bash
npm install -g @larksuite/cli   # 拿 lark-cli binary
lark-cli auth login              # 飞书登录（走 ailab/ailab account）
```

| 替代入口 | 说明 |
|------|------|
| f-doc | 飞书文档统一入口，编排所有 lark-cli 命令（wiki/表格/白板/PPT/Base） |

### 辅助工具 — 来自 [vinvcn/mattpocock-skills-zh-CN](https://github.com/vinvcn/mattpocock-skills-zh-CN)

**1 个 plugin 入口** `mattpocock-skills`，一次安装暴露 18 个 skill（caveman/diagnose/grill-me/improve-codebase-architecture/write-a-skill/zoom-out/grill-with-docs/tdd/to-issues/to-prd/triage/prototype/handoff/git-guardrails-claude-code/migrate-to-shoehorn/scaffold-exercises/setup-pre-commit/setup-matt-pocock-skills）。

| 代表 skill | 说明 |
|-------|------|
| `caveman` | 超压缩输出模式（节省 ~75% token） |
| `diagnose` | 纪律化 bug 诊断循环 |
| `grill-me` | 设计审查 interview |
| `improve-codebase-architecture` | 架构深化优化 |
| `write-a-skill` | 创建新 skill |
| `zoom-out` | 代码全景视角 |

> 这些 skill 不在仓内实体，marketplace.json 用 `source: {source: "github", repo: ...}` 引用（**不带 path**，装 root 一次拿全 monorepo）。安装时从原仓库拉取，**自动跟官方更新**。

## 安装前置

**f-doc** 需要 `lark-cli` binary（f-doc 编排层直接调 lark-cli 命令）：
```bash
npm install -g @larksuite/cli
lark-cli auth login
```
> lark-cli 没装 → f-doc 触发时报 "lark-cli: command not found"。

**f-vessel** 需要先装 [Vessel AI 浏览器](https://github.com/unmodeled-tyler/vessel-browser)：
```bash
bash option-vessel/init.sh   # 仓内已带安装器
```

## 架构

```
claude-skills/                          ← 单聚合 marketplace 仓
├── .claude-plugin/
│   └── marketplace.json                # 9 个 plugin 入口（8 本地 + 1 monorepo 外部，lark-* 走系统 lark-cli）
├── plugins/                            ← 8 个自建 plugin
│   ├── f-pdf/SKILL.md
│   ├── f-ppt/SKILL.md
│   ├── f-research/SKILL.md
│   ├── f-research-deep/SKILL.md
│   ├── f-research-report/SKILL.md
│   ├── f-report-std/SKILL.md
│   ├── f-doc/SKILL.md
│   ├── f-vessel/SKILL.md
│   └── skill-template/                 # 脚手架（开发用）
├── option-vessel/                      # f-vessel 配套安装器
│   ├── init.sh
│   └── README.md
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
└── LICENSE
```

**为什么 monorepo 一次装而不是 subdir 拆开**：
- vinvcn 是 monorepo，`path: "skills/caveman"` 拆 6 个 entry 实际每次都 clone 整个仓
- 同一 plugin（`name: mattpocock-skills`）被装 6 份 = /skills 对话框出现 6 份重复条目
- 改为 root 一次装：cache 省 ~10× 空间，UI 干净，install 速度 5×+

**为什么 lark-* 不在 marketplace**：
- larksuite/cli monorepo 一次装暴露 26 个 lark-* skill（lark-base/lark-doc/lark-approval/lark-mail/lark-im/...），dialog 太噪音
- 飞书操作实际只需要 `lark-cli` binary + f-doc 编排层（f-doc 已封装所有 lark-cli 命令组合）
- lark-* skill 作为单独 plugin 是冗余中间层

**为什么用 marketplace 引用而不是复制**：
- 三方 skill 来自 mattpocock-skills-zh-CN，**这是上游社区维护**，不在我仓里更对（避免重复维护、跟官方版本错位）
- 用户想要 lark 完整功能走官方 `npm install -g @larksuite/cli`；其他 skill 走本 marketplace
- 我的贡献是 `f-*` 编排层（飞书/调研/PPT/PDF/浏览器）和集成经验（option-vessel/）

## 许可

MIT — 见 [LICENSE](LICENSE)

## English Summary

A Claude Code marketplace with 8 original skills + 1 monorepo external reference:

- **Self-built (in repo)**: f-doc, f-ppt, f-pdf, f-research, f-research-deep, f-research-report, f-report-std, f-vessel
- **Feishu CLI (system level)**: install `@larksuite/cli` via npm — f-doc orchestrates all `lark-cli` commands
- **Utilities (from `vinvcn/mattpocock-skills-zh-CN`)**: mattpocock-skills — installs all 18 skills (caveman, diagnose, grill-me, improve-codebase-architecture, write-a-skill, zoom-out, ...)
