# Changelog

## [0.13.0] — 2026-10-18

### Added
- **fpdf**（PDF 精排）：把 PDF 精确拆解后重排为飞书文档，可选导出 Word、可选生成译文版。三个入口 `/fpdf <路径>` / `/fpdf word <路径>` / `/fpdf trans <路径>`。marketplace 24 → 25 个 plugin
  - `scripts/parse.py`：MinerU Precision 解析 → 结构包（markdown + `content_list` 带 bbox + 图片 + 版式推断）
  - `scripts/render.py`：结构包 → 飞书 DocxXML（表格列宽 822、`<grid>` 分栏、`<callout>` 强调、图片 caption）
  - `scripts/translate.py`：逐段翻译（复用 Claude 当前模型，走 Anthropic Messages）
  - `scripts/run.sh`：编排器（解析 → 渲染 → 上传飞书 → 可选 Word 导出）
  - `scripts/setup.sh`：依赖预检 + 自动安装（uv / **poppler-utils** / lark-cli / 飞书授权 / MinerU token），支持 `--check` 只检查
  - `run.sh` 启动时**自动调 setup.sh 补齐依赖**，用户无需手动预检
- fpdf: `deps.txt` 声明 `poppler-utils apt:latest`（init-skill.sh sync 一并处理）
- fpdf: `config.yaml.example` + `.gitignore`

### Fixed
- **表格 XML 语法更正（重要）**：`<lark-table rows= cols= column-widths=>` 经实测**无效** —— 列宽被丢弃（全变 120）、第二个 `<lark-tr>` 被吞。正确写法是标准 HTML `<table><colgroup><thead><tr><th>`（实测列宽 411 保留、多行完整）。ffeishu SKILL.md + write-checklist.md 已更正，fworch-interview / fwstd-course / fwstd-report / fwstd-interview 的残留引用一并清理，`report_check.py` 的标签白名单同步更新

### Changed
- **ffeishu**: PDF 处理改为**委托 fpdf**（新增「PDF 处理 → 委托 fpdf skill」路由节），不再自己用 MCP/外部工具临时对付；移除低效的 `— | 用 MCP/外部工具` 占位

## [0.12.0] — 2026-10-16

### Added
- marketplace.json: 注册 fworch 撰写系统全套缺失条目 — **fworch**（统一入口）+ **fworch-course** + **fworch-case** + **fworch-interview**，及 **fllmpack**（LLM 预设导出/导入）。marketplace 从 20 → 24 个 plugin，与 `plugins/` 目录数一致

### Changed
- marketplace.json 版本 0.9.0 → 0.12.0（此前用旧版号，与 CHANGELOG 漂移）
- **README.md 全面重写**：修正仓名 `claude-skills` → `skill`；marketplace add 命令修正；自建 skill 表从 16 条刷新为 24 条（补 fworch/fwstd-* 撰写系统 8 个 + fllmpack + fmashwork）；移除不存在的 `freportstd` / `fresearchreport` 旧名（实为 `fwstd-report` / `fworch-report`）
- **CLAUDE.md 重写**：plugin 数 15→24、目录结构、插件清单、配置注入路径（`ccprivate/skill-config/` → `ccprivate/skill/`）
- **CONTRIBUTING.md**：仓名修正；移除不存在的 `plugins/skill-template/` 与 `option-<name>/` 结构条目

### Fixed
- README / CLAUDE.md / CONTRIBUTING.md 中所有 `github.com/mengfanchun2017/claude-skills` 死链 → `github.com/mengfanchun2017/skill`
- **www/index.html 展示页刷新**：SKILLS 数组 15 → 24 张卡片（修正 3 个不存在的 skill 名 `fresearchreport`/`freportstd`/`getnote` → `fworch-report`/`fwstd-report`/撰写系统全套）；技能数文案 16 → 24；GitHub 链接与 marketplace add 命令修正；补充 i18n fllmpack 卡片

## [0.11.0] — 2026-08-23

### Added
- **ftransec**（科研英文翻译流水线）：8 步流水线 — ①结构感知切分 ②术语/风格注入 ③LLM 分段翻译(带置信分) ④五维 QE 评分+阈值路由 ⑤后编辑/复核 ⑥stitch 还原 ⑦格式还原 ⑧交付包
- ftransec: 三级术语体系（glossary / doNotTranslate / forbiddenTranslations）+ severity 分级 QC
- ftransec: 5 件交付包 — 双语正文 + 术语表 + 评审报告 + 置信度标注 + 翻译说明
- ftransec: `references/chinese-academic-style.md`（规避翻译腔）+ `references/qc-rubric.md`（五维评分细则）+ `references/terminology-extraction-prompt.md`（术语抽取 prompt 模板）
- ftransec: `config.yaml.example` + `deps.txt`（声明 LLM 网关依赖）
- 设计文档：`docs/translation-system-design.md`（10 节完整方案，自建 vs DeepL/CAT 决策依据）

### Changed
- marketplace.json: 注册 ftransec 插件（16→17）
- marketplace.json: 同步 fsearch SKILL.md 描述更新（双源 + 自动 extract）

## [0.10.0] — 2026-08-13

### Changed
- **fpptx**: PPT 生成默认飞书在线 Slides 直出（`lark-cli slides`），替代「先 OfficeCLI 生成 PPTX 再上传」旧流程
- fpptx SKILL.md: 执行流程更新，PPTX 降级为备选输出方式
- 新增 ADR-001: 决策记录 — PPT 优先飞书 Slides 直出（在线可编辑）

### Added
- fpptx: 飞书 Slides XML 生成支持（原生元素 + 图片 `@` 占位符自动上传）
- fpptx: 飞书文档图片无损提取工作流（docs +media-download → 嵌入）

## [0.9.0] — 2026-07-17

### Changed
- **f-syncpage → f-syncdoc**: 扩展为两阶段流水线 — doc sync（源码→文档）+ 条件 page sync（aiagt 产品页）。映射外置到 ccprivate，开源用户配置自己的 mapping 即可。
- f-syncdoc CLI: `/f-syncdoc` 无参交互选择 / 指定仓库直走

### Added
- f-syncdoc: `page-mapping.template.json` 映射模板（公开）
- f-syncdoc: `.gitignore` 排除私有 `page-mapping.json`

## [0.8.0] — 2026-07-08

### Removed
- **f-vessel**: 删除 Vessel AI 浏览器 skill + option-vessel 安装器（改用 Playwright @playwright/mcp）
- marketplace.json 从 17→16 个 plugin

### Changed
- README 更新：架构图移除 vessel 相关条目，插件数更新为 15

## [0.7.0] — 2026-07-06

### Added
- marketplace.json 补全 4 个缺失 plugin：f-logme、f-launch、f-moocrec、f-search
- config.yaml.example 补全 7 个 skill（f-research、f-research-deep、f-research-report、f-search、f-vessel、f-launch、f-report-std）

### Changed
- **README 全面更新**：skill 数量 8→12，架构图补齐，f-ppt 描述修正
- **marketplace.json**：f-ppt 描述移除 ppt-master 引用，版本 0.3.0→0.4.0

## [0.6.0] — 2026-06-06

### Changed
- **第三方 skill 装法改 user-managed via `npx skills`**：marketplace 不再强制推 mattpocock/lark-* plugin（避免 dialog 噪音）
- 用户自己用 `npx --yes skills@latest add <source> --skill <name> -g -y` 装（ccconfig 用户的 `init-skill.sh sync` 阶段 3 自动跑）
- 更新：`npx --yes skills@latest update -g -y`（ccconfig: `scripts/update-third-party-skills.sh`）
- `mattpocock-skills` entry 仍保留（愿意接受噪音的人可用 marketplace install）

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
