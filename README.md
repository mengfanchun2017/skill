# claude-skills — mengfanchun2017 的 Claude Code skill 集合

> Claude Code 技能聚合仓。21 个 skill，**一个 marketplace，一次安装**。
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
# ...
```

后续更新：

```
/plugin marketplace update mengfanchun2017-skills
```

## 包含的 skill（21 个）

### 文档 / PPT / PDF

| Skill | 说明 |
|-------|------|
| `f-doc` | 飞书文档统一入口（wiki/表格/白板/PPT、报告整合/拆分/转换/对比） |
| `f-ppt` | PPT 生成（双引擎：ppt-master + OfficeCLI） |
| `f-pdf` | PDF 内容提取（PyMuPDF：文字/图片/表格/元数据） |
| `f-research-report` | 报告生成（JSON/大纲/素材 → 结构化 Markdown） |

### 调研

| Skill | 说明 |
|-------|------|
| `f-research` | 快速研究（三源并行：Tavily + MiniMax + WebSearch） |
| `f-research-deep` | 深度研究（批量 JSON 输出） |

### 飞书（依赖 lark-cli）

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

### 浏览器 / 调试 / 工具

| Skill | 说明 |
|-------|------|
| `f-vessel` | AI 浏览器操控（Vessel MCP，需配套 option-vessel/ 安装器） |
| `caveman` | 超压缩输出模式（节省 ~75% token） |
| `diagnose` | 纪律化 bug 诊断循环 |
| `grill-me` | 设计审查 interview |
| `improve-codebase-architecture` | 架构深化优化 |
| `write-a-skill` | 创建新 skill |
| `zoom-out` | 代码全景视角 |

## 安装前置

**lark-* 8 个 skill** 需要先装 [lark-cli](https://github.com/larksuite/cli)：
```bash
npm install -g @larksuite/cli
lark-cli auth login
```

**f-vessel** 需要先装 [Vessel AI 浏览器](https://github.com/unmodeled-tyler/vessel-browser)：
```bash
bash option-vessel/init.sh   # 仓内已带安装器
```

## 架构

```
claude-skills/                          ← 单聚合 marketplace 仓
├── .claude-plugin/
│   └── marketplace.json                # 21 个 plugin 入口
├── plugins/                            ← 各 skill 实体
│   ├── f-pdf/.claude-plugin/plugin.json
│   ├── f-pdf/SKILL.md
│   ├── f-pdf/...
│   ├── f-ppt/
│   ├── ...
│   └── zoom-out/
├── option-vessel/                      # f-vessel 配套安装器
│   ├── init.sh
│   └── README.md
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
└── LICENSE
```

**两层 .claude-plugin**：
- 仓根 `.claude-plugin/marketplace.json`：Claude Code 用这个找"这个仓是 marketplace"
- 每个 plugin 内 `.claude-plugin/plugin.json`（自动生成）：描述**这个** plugin

## 许可

MIT — 见 [LICENSE](LICENSE)

## English Summary

21 Claude Code skills in a single marketplace repo. Install via:

```
/plugin marketplace add mengfanchun2017/claude-skills
/plugin install <skill-name>@mengfanchun2017-skills
```

Categories: docs (f-doc/f-ppt/f-pdf/f-research-report), research (f-research/f-research-deep), Feishu (8 lark-* skills via lark-cli), AI browser (f-vessel + option-vessel installer), dev tools (caveman/diagnose/grill-me/improve-codebase-architecture/write-a-skill/zoom-out).
