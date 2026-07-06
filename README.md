# claude-skills — mengfanchun2017 的 Claude Code skill 集合

> Claude Code 技能聚合仓。**12 个自建**（plugin 安装）+ **第三方 skill 由用户用 npx skills 自管**（不通过 marketplace）。
> 飞书 / 调研 / 文档 / PPT / PDF / AI 浏览器一站式。

## 快速开始

在 Claude Code 里执行一行命令：

```
/plugin marketplace add mengfanchun2017/claude-skills
```

然后挑你需要的装（**只装自建 f-***）：

```
/plugin install f-pdf@mengfanchun2017-skills
/plugin install f-doc@mengfanchun2017-skills
```

后续更新：

```
/plugin marketplace update mengfanchun2017-skills
```

## 第三方 skill 装法（不通过 marketplace）

**WHY**（2026-06-06 重构）：marketplace install 第三方 skill 会暴露 plugin 前缀（`mattpocock-skills:caveman`）和 🔒 锁，dialog 太噪音。
**HOW**：用 [`npx skills`](https://github.com/vercel-labs/skills) 直接装上游仓库的 sub-skill，自动 symlink 到 `~/.claude/skills/`，**干净显示**（无前缀无锁）。

```bash
# 装单个 skill
npx --yes skills@latest add vinvcn/mattpocock-skills-zh-CN --skill caveman -g -y

# 装多个 skill
npx --yes skills@latest add vinvcn/mattpocock-skills-zh-CN \
  --skill caveman --skill diagnose --skill grill-me --skill improve-codebase-architecture --skill write-a-skill --skill zoom-out -g -y

# 跟上游更新
npx --yes skills@latest update -g -y
```

ccconfig 用户：`bash init-skill.sh sync` 自动从 `conf/third-party-skills.txt` 列表幂等装，update 跑 `scripts/update-third-party-skills.sh`。

## 自建 skill（12 个，仓内）

| Skill | 说明 |
|-------|------|
| `f-doc` | 飞书文档统一入口（wiki/表格/白板/PPT、报告整合/拆分/转换/对比） |
| `f-ppt` | PPT 生成（OfficeCLI 引擎：批量 JSON、模板合并） |
| `f-pdf` | PDF 内容提取（PyMuPDF：文字/图片/表格/元数据） |
| `f-search` | 多源搜索编排原语（三源并行：Tavily + MiniMax + WebSearch） |
| `f-research` | 快速研究（领域自动识别 + 三源并行） |
| `f-research-deep` | 深度研究（outline.yaml → 批量 JSON 输出） |
| `f-research-report` | 报告生成（JSON/大纲/素材 → 结构化 Markdown） |
| `f-report-std` | 报告写作横向规范（4 套模板：研究/分析/对比/方案）|
| `f-logme` | 个人管理（OKR/Worklog/Reflect/SUM，飞书 Base） |
| `f-launch` | 项目启动脚手架（8 种项目类型，自动 CLAUDE.md + rules） |
| `f-moocrec` | 慕课推荐（QS 课程 + 学习路径，飞书 Base + Supabase） |
| `f-vessel` | AI 浏览器操控（Vessel MCP，需配套 option-vessel/ 安装器） |

## 外部 skill — 三方上游 + 系统层 lark-cli（不通过本仓装）

### 飞书操作 — 不走 plugin，走 npm 全局 lark-cli

**飞书 lark-* skill 不在本仓 marketplace**（2026-06-06 重构移除）。
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

**用户装法**：见上文"第三方 skill 装法"（用 `npx skills add` 装指定 sub-skill）。本仓 marketplace 不强制装（避免 dialog 噪音），但保留 `mattpocock-skills` entry 给愿意接受噪音的人。

| 代表 skill | 说明 |
|-------|------|
| `caveman` | 超压缩输出模式（节省 ~75% token） |
| `diagnose` | 纪律化 bug 诊断循环 |
| `grill-me` | 设计审查 interview |
| `improve-codebase-architecture` | 架构深化优化 |
| `write-a-skill` | 创建新 skill |
| `zoom-out` | 代码全景视角 |

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
│   └── marketplace.json                # 13 个 plugin 入口（12 本地 + 1 monorepo 外部，lark-* 走系统 lark-cli）
├── plugins/                            ← 12 个自建 plugin
│   ├── f-doc/SKILL.md
│   ├── f-ppt/SKILL.md
│   ├── f-pdf/SKILL.md
│   ├── f-search/SKILL.md
│   ├── f-research/SKILL.md
│   ├── f-research-deep/SKILL.md
│   ├── f-research-report/SKILL.md
│   ├── f-report-std/SKILL.md
│   ├── f-logme/SKILL.md
│   ├── f-launch/SKILL.md
│   ├── f-moocrec/SKILL.md
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

A Claude Code marketplace with 12 self-built skills. Third-party skills use `npx skills` (not /plugin install) for clean dialog UX.

- **Self-built (in repo)**: f-doc, f-ppt, f-pdf, f-search, f-research, f-research-deep, f-research-report, f-report-std, f-logme, f-launch, f-moocrec, f-vessel
- **Feishu CLI (system level)**: install `@larksuite/cli` via npm — f-doc orchestrates all `lark-cli` commands
- **Utilities (user-installed via `npx skills`)**: vinvcn/mattpocock-skills-zh-CN sub-skills (caveman, diagnose, grill-me, ...)
