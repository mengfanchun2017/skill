# CLAUDE.md — skill

> 项目级 AI 行为指南。**仅在 `/home/francis/git/skill/` 工作时加载**。全局规则在 `~/.claude/CLAUDE.md`。

## 项目定位
Claude Code skill 聚合仓。**26 个自建 plugin，全部在 marketplace 注册**（每个 `plugins/<name>/` 是独立 Claude Code plugin），第三方 skill 由用户用 `npx skills` 自管（不通过 marketplace）。

## 目录结构
```
skill/
├── plugins/                # 26 个自建 plugin
├── scripts/                # marketplace 工具脚本
├── .claude-plugin/         # Claude Code plugin 元数据
├── .github/                # CI
├── CHANGELOG.md
├── CONTRIBUTING.md
├── README.md
└── www/                    # 静态展示页（部署到 skill.aiagt.dev）
```

## 26 个 plugin
| Plugin | 用途 |
|--------|------|
| ffeishu | 飞书文档/PPT/表格/Base 操作统一入口 |
| fpptx | PPT / 飞书 Slides 生成 |
| fdocx | Word 文档 |
| fxlsx | Excel 表格 |
| fdiagram | 飞书画板统一入口（架构/流程/时序/ER/类/甘特/思维导图） |
| fsearch | 搜索活动统一原语（中英双语路由） |
| fresearchframe | 4 领域研究方法论框架 |
| fworch | 撰写系统统一入口（按体裁路由） |
| fworch-report | 报告生成 orchestrator |
| fworch-course | 系列课程创作 orchestrator |
| fworch-case | 案例库编排器 |
| fworch-interview | 面试准备 orchestrator |
| fwstd-report | 报告写作规范 |
| fwstd-course | 课程内容规范 |
| fwstd-case | 案例库内容规范 |
| fwstd-interview | 面试准备内容规范 |
| flogme | 个人 OKR/工作日志/反思 |
| fmoocrec | MOOC 课程推荐 |
| fsysarchi | 系统分析师备考 |
| flibaudit | 仓库全面审计 |
| fsyncdoc | 源码文档同步 + 产品页同步 |
| fmashwork | AI 图生 3D → 拓竹打印 |
| fllmpack | LLM 预设配置导出/导入 |
| fskillcreat | Skill 开发脚手架 |

## 硬约束
1. **每个 plugin 是独立 Claude Code plugin**：有自己的 `commands/` `skills/` `scripts/`，可独立 `/plugin install <name>`
2. **marketplace 同步**：`marketplace.json` 是 plugin 清单的真相源，新增 plugin 必须同步
3. **不重复造轮子**：跨 plugin 共享工具放 `fsearch` / `ffeishu` 等已有 hub，不新建 `f-utils`
4. **CHANGELOG 必写**：每次发布新版本（plugin 增删或行为变更）必须更新对应节
5. **公开仓库**：本仓库公开，不放任何 API key / 个人 token。Skill 运行时的 YAML 配置放 ccprivate/skill/

## 常用命令
```bash
# 本地展示页预览
cd www && python3 -m http.server 8000

# Plugin 元数据校验
cat .claude-plugin/marketplace.json | python3 -m json.tool

# 同步到 GitHub（auto-sync 自动处理，无需手动 push）
git status  # 确认干净
```

## 添加新 plugin 流程（marketplace）
1. `mkdir plugins/<name>` — 目录名 = plugin 名（小写、无连字符）
2. 写 `SKILL.md`，frontmatter 含 `name` 和 `description`（description 是单一真相源）
3. 在 `.claude-plugin/marketplace.json` 添加 entry（`name`, `source`, `keywords`，不用写 description）
4. `python3 scripts/sync-marketplace.py --write` — 从 SKILL.md 同步 description
5. 写 CHANGELOG 一行：`### Added - <name>: ...`
6. `git commit && git push` → auto-sync 推送

## 与 ccconfig 的关系
- `~/git/ccconfig/` 提供通用编码规范（rules/）+ init-skill.sh 同步脚本
- 本仓库的 skill/plugin 是产物，ccconfig 负责安装分发
- skill YAML 配置（私有 key）从 ccprivate/skill/<name>.yaml 通过 symlink 注入到 `~/.claude/skills/<name>/config.yaml`

## 链接
- 完整 skill 列表 → [README.md](README.md)
- 变更历史 → [CHANGELOG.md](CHANGELOG.md)
- 贡献指南 → [CONTRIBUTING.md](CONTRIBUTING.md)

## 依赖管理
每个 plugin 用 `deps.txt` 声明底层 npm 包依赖（仅声明，不自动安装）：
```
<package> <type:version> <skill-name>
```
- 运行时 skill 本身应在首次调用时检测依赖是否可用（`which <binary>` 或 `command -v`）
- 缺失时提示用户安装，不强制自动安装（避免公开仓库的安装脚本风险）
- Config 在 `config.yaml.example`，真实值通过 ccprivate 注入

## 配置注入模式
```
ccprivate/skill/<name>.yaml  →  symlink  →  ~/.claude/skills/<name>/config.yaml
```
Skill 运行时读 config.yaml 拿 API key/私有参数。公开仓只放 `config.yaml.example`（占位值/文档）。
CI 检查 `plugins/*/config.yaml` 是否存在——有真实配置 = CI 报错。

## 同步流程
```bash
python3 scripts/sync-marketplace.py           # 检查：SKILL.md frontmatter 与 marketplace.json 一致？
python3 scripts/sync-marketplace.py --write   # 写入：SKILL.md description → marketplace.json
```
**SKILL.md 的 `description` 是单一真相源**。新增 plugin 时：写 SKILL.md frontmatter → `--write` 同步 → 提交。