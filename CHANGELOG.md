# Changelog

## [0.5.0] — 2026-06-06

### Removed
- **lark-* 全部 plugin 入口**：larksuite/cli 24+ skill 太噪音，且 f-doc 已封装所有 lark-cli 命令组合
- 改用 `npm install -g @larksuite/cli` 装 lark-cli binary，f-doc 编排全部飞书操作

## [0.4.0] — 2026-06-06

### Changed
- **外部 plugin 重塑**：14 个 subdir path 入口 → 2 个 monorepo root 入口
  - `mattpocock-skills`：装 vinvcn/mattpocock-skills-zh-CN 一次，暴露 18 个 skill
  - `lark-suite`：装 larksuite/cli 一次，暴露 26 个 lark-* skill
- 修复 `/skills` 对话框 6×/8× 重复条目（同一 plugin name 被装多份）

## [0.3.0] — 2026-06-05

### Added
- **8 个自建 plugin**（加 f-report-std — 报告写作横向规范，4 套模板）
- marketplace.json 版本 → 0.3.0

## [0.2.0] — 2026-06-05

### Changed
- **重构**：14 个非自建 skill（lark-* 8 + 三方 6）从仓内删除，marketplace.json 改用 `source` 引用外部 GitHub 仓
- 仓大小从 1.3M → 250K（减 80%）
- 第三方 skill 自动跟官方更新，不再需要手动同步

### Added
- 7 个自建 plugin（f-pdf, f-ppt, f-research, f-research-deep, f-research-report, f-doc, f-vessel）
- 14 个 marketplace 引用（larksuite/cli 8 + vinvcn/mattpocock-skills-zh-CN 6）

## [0.1.0] — 2026-06-05

### Added
- 初始发布，21 个 skill 全部复制到 plugins/
- 飞书：f-doc, f-ppt, f-pdf, f-research, f-research-deep, f-research-report
- 飞书 CLI：lark-shared, lark-doc, lark-base, lark-sheets, lark-wiki, lark-whiteboard, lark-drive, lark-calendar
- 浏览器 / 工具：f-vessel, caveman, diagnose, grill-me, improve-codebase-architecture, write-a-skill, zoom-out
- option-vessel/ 配套安装器
- .claude-plugin/marketplace.json 入口
