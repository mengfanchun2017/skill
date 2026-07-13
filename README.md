# claude-skills — Claude Code skill 集合

> Claude Code 技能聚合仓。**15 个自建**（plugin 安装）+ **第三方 skill 由用户用 npx skills 自管**（不通过 marketplace）。
> 飞书 / 调研 / 文档 / PPT / PDF / Excel / 图表 / AI 浏览器一站式。

## 快速开始

在 Claude Code 里添加 marketplace（一次性）：

```
/plugin marketplace add <your-github-username>/claude-skills
```

然后按需安装（挑你需要的，`<name>` 替换为下表中的名称）：

```
/plugin install <name>@<your-github-username>-skills
```

| 你需要… | 安装命令 |
|---------|---------|
| 飞书文档操作 | `/plugin install f-feishu@<your-github-username>-skills` |
| PPT 生成 | `/plugin install f-pptx@<your-github-username>-skills` |
| Word 文档 | `/plugin install f-docx@<your-github-username>-skills` |
| Excel 表格 | `/plugin install f-xlsx@<your-github-username>-skills` |
| PDF 处理 | `/plugin install f-pdf@<your-github-username>-skills` |
| 画架构图/流程图 | `/plugin install f-diagram@<your-github-username>-skills` |
| 搜索/调研 | `/plugin install f-search@<your-github-username>-skills` |
| 研究报告 | `/plugin install f-research-report@<your-github-username>-skills` |
| 个人 OKR/日志 | `/plugin install f-logme@<your-github-username>-skills` |
| 新项目脚手架 | `/plugin install f-launch@<your-github-username>-skills` |
| 慕课推荐 | `/plugin install f-moocrec@<your-github-username>-skills` |
| 系统架构师备考 | `/plugin install f-sysarchi@<your-github-username>-skills` |
| 得到笔记 | `/plugin install getnote@<your-github-username>-skills` |
| 报告写作规范 | `/plugin install f-report-std@<your-github-username>-skills` |
| 研究方法论框架 | `/plugin install f-research-frame@<your-github-username>-skills` |

可以一次装多个：

```
/plugin install f-feishu@<your-github-username>-skills
/plugin install f-pptx@<your-github-username>-skills
/plugin install f-search@<your-github-username>-skills
```

后续更新：

```
/plugin marketplace update <your-github-username>-skills
```

## 第三方 skill 装法（不通过 marketplace）

**WHY**（2026-06-06 重构）：marketplace install 第三方 skill 会暴露 plugin 前缀（`mattpocock-skills:caveman`）和 🔒 锁，dialog 太噪音。
**HOW**：用 [`npx skills`](https://github.com/vercel-labs/skills) 直接装上游仓库的 sub-skill，自动 symlink 到 `~/.claude/skills/`，**干净显示**（无前缀无锁）。

```bash
# 装单个 skill
npx --yes skills@latest add mattpocock/skills --skill caveman -g -y

# 装多个 skill
npx --yes skills@latest add mattpocock/skills \
  --skill caveman --skill diagnose --skill grill-me --skill improve-codebase-architecture --skill write-a-skill --skill zoom-out -g -y

# 跟上游更新
npx --yes skills@latest update -g -y
```

cconfig 用户：`bash ccconfig/init-skill.sh sync` 自动从 `conf/third-party-skills.txt` 列表幂等装，update 跑 `scripts/update-third-party-skills.sh`。

### 配合 ccconfig 使用

克隆 [ccconfig](https://github.com/<your-github-username>/ccconfig) 后，`init-skill.sh sync` 自动完成：symlink 自建 skill、注册 marketplace、安装第三方 skill、注入私有配置。详见 ccconfig 文档。

## 自建 skill（15 个，仓内）

| Skill | 说明 |
|-------|------|
| `f-feishu` | 飞书文档编排层（wiki/表格/白板、报告整合/拆分/转换/对比） |
| `f-report-std` | 报告写作横向规范（4 套模板：研究/分析/对比/方案） |
| `f-pdf` | PDF 内容提取 + 翻译原语（PyMuPDF：文字/图片/表格/元数据） |
| `f-pptx` | PPTX 总控（OfficeCLI 引擎：批量 JSON、模板合并、autofit） |
| `f-research-frame` | 4 领域研究方法论 + 批量深度研究（customer/generic/market/technical） |
| `f-research-report` | 报告生成（JSON/大纲/素材 → 结构化 Markdown） |
| `f-search` | 多源搜索编排原语（三源并行：Tavily + MiniMax + WebSearch） |
| `f-diagram` | 代码驱动图表生成（Mermaid 架构/流程/时序/ER/类图、白板） |
| `f-docx` | Word .docx 总控（OfficeCLI 引擎：模板/样式/表格/图片/目录） |
| `f-xlsx` | Excel .xlsx 总控（OfficeCLI 引擎：公式/图表/条件格式/透视表） |
| `f-logme` | 个人管理系统（OKR/Worklog/Reflect/SUM，飞书 Base） |
| `f-launch` | 项目启动脚手架（8 种项目类型，自动 CLAUDE.md + rules） |
| `f-moocrec` | 慕课推荐（QS 课程 + 学习路径，飞书 Base + Supabase） |
| `f-sysarchi` | 系统分析师备考 — 暗号 `archi` 触发，随工边做边学 |
| `getnote` | 得到大脑集成 — MCP 驱动，笔记 CRUD/搜索/知识库/直播 |

## 外部 skill — 三方上游 + 系统层 lark-cli（不通过本仓装）

### 飞书操作 — 不走 plugin，走 npm 全局 lark-cli

**飞书 lark-* skill 不在本仓 marketplace**（2026-06-06 重构移除）。
原因：larksuite/cli 是 monorepo，一次 plugin install 暴露 26 个 lark-* skill，dialog 太噪音。
解决：`npm install -g @larksuite/cli` 装 CLI，由 **f-feishu 编排**所有飞书操作（f-feishu 直接调 `lark-cli docs/base/sheets/wiki/...` 命令，不依赖 lark-* skill）。

```bash
npm install -g @larksuite/cli   # 拿 lark-cli binary
lark-cli auth login              # 飞书登录
```

| 替代入口 | 说明 |
|------|------|
| f-feishu | 飞书文档统一入口，编排所有 lark-cli 命令（wiki/表格/白板/PPT/Base） |

### 辅助工具 — 来自 [mattpocock/skills](https://github.com/mattpocock/skills)

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

**f-feishu** 需要 `lark-cli` binary（f-feishu 编排层直接调 lark-cli 命令）：
```bash
npm install -g @larksuite/cli
lark-cli auth login
```
> lark-cli 没装 → f-feishu 触发时报 "lark-cli: command not found"。

## 架构

```
claude-skills/                          ← 单聚合 marketplace 仓
├── .claude-plugin/
│   └── marketplace.json                # 16 个 plugin 入口（15 本地 + 1 monorepo 外部，lark-* 走系统 lark-cli）
├── plugins/                            ← 15 个自建 plugin
│   ├── f-feishu/SKILL.md
│   ├── f-report-std/SKILL.md
│   ├── f-pdf/SKILL.md
│   ├── f-pptx/SKILL.md
│   ├── f-research-frame/SKILL.md
│   ├── f-research-report/SKILL.md
│   ├── f-search/SKILL.md
│   ├── f-diagram/SKILL.md
│   ├── f-docx/SKILL.md
│   ├── f-xlsx/SKILL.md
│   ├── f-logme/SKILL.md
│   ├── f-launch/SKILL.md
│   ├── f-moocrec/SKILL.md
│   ├── f-sysarchi/SKILL.md
│   ├── getnote/SKILL.md
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
└── LICENSE
```

**为什么 monorepo 一次装而不是 subdir 拆开**：
- mattpocock/skills 是 monorepo，`path: "skills/caveman"` 拆 6 个 entry 实际每次都 clone 整个仓
- 同一 plugin（`name: mattpocock-skills`）被装 6 份 = /skills 对话框出现 6 份重复条目
- 改为 root 一次装：cache 省 ~10× 空间，UI 干净，install 速度 5×+

**为什么 lark-* 不在 marketplace**：
- larksuite/cli monorepo 一次装暴露 26 个 lark-* skill（lark-base/lark-doc/lark-approval/lark-mail/lark-im/...），dialog 太噪音
- 飞书操作实际只需要 `lark-cli` binary + f-feishu 编排层（f-feishu 已封装所有 lark-cli 命令组合）
- lark-* skill 作为单独 plugin 是冗余中间层

**为什么用 marketplace 引用而不是复制**：
- 三方 skill 来自 mattpocock-skills-zh-CN，**这是上游社区维护**，不在我仓里更对（避免重复维护、跟官方版本错位）
- 用户想要 lark 完整功能走官方 `npm install -g @larksuite/cli`；其他 skill 走本 marketplace
- 我的贡献是 `f-*` 编排层（飞书/调研/PPT/PDF/Excel/图表/浏览器）和集成经验

## 许可

MIT — 见 [LICENSE](LICENSE)

## English Summary

A Claude Code marketplace with 15 self-built skills. Third-party skills use `npx skills` (not /plugin install) for clean dialog UX.

- **Self-built (in repo)**: f-feishu, f-report-std, f-pdf, f-pptx, f-research-frame, f-research-report, f-search, f-diagram, f-docx, f-xlsx, f-logme, f-launch, f-moocrec, f-sysarchi, getnote
- **Feishu CLI (system level)**: install `@larksuite/cli` via npm — f-feishu orchestrates all `lark-cli` commands
- **Utilities (user-installed via `npx skills`)**: mattpocock/skills sub-skills (caveman, diagnose, grill-me, ...)
