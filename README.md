# claude-skills — mengfanchun2017 的 Claude Code skill 集合

> Claude Code 技能聚合仓。**8 个自建 + 14 个外部引用**，一个 marketplace，一次安装。
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
/plugin install f-research@mengfanchun2017-skills
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

## 外部 skill（14 个，marketplace.json 引用，自动跟官方更新）

### 飞书 — 来自 [larksuite/cli](https://github.com/larksuite/cli)

| Skill | 说明 |
|-------|------|
| `lark-shared` | 飞书基础：认证、多账号 |
| `lark-doc` | 飞书云文档 CRUD |
| `lark-base` | 飞书多维表格 |
| `lark-sheets` | 飞书电子表格 |
| `lark-wiki` | 飞书知识库 |
| `lark-whiteboard` | 飞书画板 |
| `lark-drive` | 飞书云空间 |
| `lark-calendar` | 飞书日历 |

**官方安装地址**：[github.com/larksuite/cli](https://github.com/larksuite/cli) / `npm install -g @larksuite/cli`（拿到完整 CLI + 26 个 skill）

### 辅助工具 — 来自 [vinvcn/mattpocock-skills-zh-CN](https://github.com/vinvcn/mattpocock-skills-zh-CN)

| Skill | 说明 |
|-------|------|
| `caveman` | 超压缩输出模式（节省 ~75% token） |
| `diagnose` | 纪律化 bug 诊断循环 |
| `grill-me` | 设计审查 interview |
| `improve-codebase-architecture` | 架构深化优化 |
| `write-a-skill` | 创建新 skill |
| `zoom-out` | 代码全景视角 |

> 这些 skill 不在仓内实体，marketplace.json 用 `source: {source: "github", repo: ..., path: ...}` 引用。安装时从原仓库拉取，**自动跟官方更新**。

## 安装前置

**lark-* 8 个 skill** 是 larksuite/cli 官方维护。两种装法：
```bash
# 方式 A：官方 npm 装 lark-cli（推荐，CLI 命令 + 26 个 skill 全有）
npm install -g @larksuite/cli
lark-cli auth login

# 方式 B：本 marketplace 只装 skill（不开 CLI 功能）
# /plugin install lark-base@mengfanchun2017-skills
```
> 方式 A 拿完整 CLI + skill，方式 B 只拿 skill 走 Claude Code 编排。**不要重复装**（CLI 装过就别 marketplace 装 lark-*）。

**f-vessel** 需要先装 [Vessel AI 浏览器](https://github.com/unmodeled-tyler/vessel-browser)：
```bash
bash option-vessel/init.sh   # 仓内已带安装器
```

## 架构

```
claude-skills/                          ← 单聚合 marketplace 仓
├── .claude-plugin/
│   └── marketplace.json                # 22 个 plugin 入口（8 本地 + 14 外部）
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

**为什么用 marketplace 引用而不是复制**：
- lark-* 来自 larksuite/cli，三方来自 mattpocock-skills-zh-CN，**这些是上游社区维护**，不在我仓里更对（避免重复维护、跟官方版本错位）
- 用户想要 lark 完整功能（CLI + skill）走官方 `npm install -g @larksuite/cli`；只要 skill 走本 marketplace
- 我的贡献是 `f-*` 编排层（飞书/调研/PPT/PDF/浏览器）和集成经验（option-vessel/）

## 许可

MIT — 见 [LICENSE](LICENSE)

## English Summary

A Claude Code marketplace with 7 original skills + 14 external references:

- **Self-built (in repo)**: f-doc, f-ppt, f-pdf, f-research, f-research-deep, f-research-report, f-report-std, f-vessel
- **Feishu CLI (from `larksuite/cli`)**: lark-shared, lark-doc, lark-base, lark-sheets, lark-wiki, lark-whiteboard, lark-drive, lark-calendar
- **Utilities (from `vinvcn/mattpocock-skills-zh-CN`)**: caveman, diagnose, grill-me, improve-codebase-architecture, write-a-skill, zoom-out

Install:
```
/plugin marketplace add mengfanchun2017/claude-skills
/plugin install <skill>@mengfanchun2017-skills
```
