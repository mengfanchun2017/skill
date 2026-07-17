# CLAUDE.md — claude-skills

> 项目级 AI 行为指南。**仅在 `/home/francis/git/skill/` 工作时加载**。全局规则在 `~/.claude/CLAUDE.md`。

## 项目定位
Claude Code skill 聚合仓。**15 个自建 plugin**（每个 `plugins/<name>/` 是独立 Claude Code plugin），第三方 skill 由用户用 `npx skills` 自管（不通过 marketplace）。

## 目录结构
```
skill/
├── plugins/                # 15 个自建 plugin（每个含 commands/skills/scripts 等）
├── scripts/                # marketplace 工具脚本
├── .claude-plugin/         # Claude Code plugin 元数据
├── .github/                # CI
├── CHANGELOG.md
├── CONTRIBUTING.md
├── README.md
└── www/                    # 静态展示页（部署到 skills.aiagt.dev）
```

## 15 个 plugin
| Plugin | 用途 |
|--------|------|
| f-feishu | 飞书文档/PPT/表格/Base 操作统一入口 |
| f-docx | Word 文档 |
| f-pptx | PPT 生成 |
| f-xlsx | Excel 表格 |
| f-diagram | 架构图/流程图/时序图 |
| f-search | 中英双语搜索 |
| f-research-report | 深度研究报告 |
| f-research-frame | 研究方法论框架 |
| f-logme | 个人 OKR/工作日志/反思 |
| f-moocrec | 慕课推荐 |
| f-sysarchi | 系统架构师备考 |
| f-report-std | 报告写作规范 |
| getnote | 得到笔记 |
| f-libaudit | Library 审计 |
| f-syncdoc | 文档同步 + 产品页同步（内部工具）|

## 硬约束
1. **每个 plugin 是独立 Claude Code plugin**：有自己的 `commands/` `skills/` `scripts/`，可独立 `/plugin install <name>`
2. **marketplace 同步**：`marketplace.json` 是 plugin 清单的真相源，新增 plugin 必须同步
3. **不重复造轮子**：跨 plugin 共享工具放 `f-search` / `f-feishu` 等已有 hub，不新建 `f-utils`
4. **CHANGELOG 必写**：每次发布新版本（plugin 增删或行为变更）必须更新对应节
5. **公开仓库**：本仓库公开，不放任何 API key / 个人 token。Skill 运行时的 YAML 配置放 ccprivate/skill-config/

## 常用命令
```bash
# 本地展示页预览
cd www && python3 -m http.server 8000

# Plugin 元数据校验
cat .claude-plugin/marketplace.json | python3 -m json.tool

# 同步到 GitHub（auto-sync 自动处理，无需手动 push）
git status  # 确认干净
```

## 添加新 plugin 流程
1. `mkdir plugins/<name>` — 目录名 = plugin 名（小写、`-` 分隔）
2. 写 `commands/` 和/或 `skills/` 和 `README.md`
3. 在 `.claude-plugin/marketplace.json` 注册
4. 写 CHANGELOG 一行：`### Added - <name>: ...`
5. `git commit && git push` → auto-sync 推送

## 与 ccconfig 的关系
- `~/git/ccconfig/` 提供通用编码规范（rules/）+ init-skill.sh 同步脚本
- 本仓库的 skill/plugin 是产物，ccconfig 负责安装分发
- skill YAML 配置（私有 key）从 ccprivate/skill-config/<name>.yaml 通过 symlink 注入到 `~/.claude/skills/<name>/config.yaml`

## 链接
- 完整 skill 列表 → [README.md](README.md)
- 变更历史 → [CHANGELOG.md](CHANGELOG.md)
- 贡献指南 → [CONTRIBUTING.md](CONTRIBUTING.md)