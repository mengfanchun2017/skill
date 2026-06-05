# Changelog

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
