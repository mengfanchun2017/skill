---
name: ffeishu
user-invocable: true
description: |
  飞书文档编排层 — 创建飞书wiki/表格/白板、更新报告、整合/拆分文档、飞书↔Office双向转换、文档对比。
  用法：用户说"创建文档"/"写文档"、"更新文档"/"更新报告"、"整合文档"/"合并文档"、
  "拆分文档"、"导出Word/PPT"、"飞书转Office"、"导入到飞书"、"对比文档"、
  或给出飞书文档URL要求操作。
  PPT 委托 fpptx，图表委托 fdiagram。
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# ffeishu — 飞书文档编排

编排层，不重新实现底层工具。委托飞书操作给 lark-cli，Office 给 OfficeCLI，PPT 给 fpptx，图表给 fdiagram。

**命令一律走 `fcore`，不手写 lark-cli 参数**（此前 5 处各抄一份 auth 预检，其中 3 处 grep
写错导致认证明明正常也恒报失败）：

```bash
~/.claude/skills/fcore/bin/fcore auth                    # 0=可用 1=未装 2=未配置
~/.claude/skills/fcore/bin/fcore doc create <parent> <title> [file|-]
~/.claude/skills/fcore/bin/fcore doc get <doc> [full|with-ids]
~/.claude/skills/fcore/bin/fcore upload <file>
~/.claude/skills/fcore/bin/fcore search "<关键词>" [数量]
~/.claude/skills/fcore/bin/fcore fmt-xml <file>          # 格式断言，不用人眼核
```

不可用时**降级**：产出落本地 markdown，不阻断主流程。

## 快速决策

```
用户意图
  ├─ "创建文档"/"写文档"/"生成报告"        → 工作流 0（创建）
  ├─ "创建表格"/"画表格"                   → 工作流 0 + 表格 XML
  ├─ "画架构图"/"流程图"/"时序图"          → 委托 fdiagram
  ├─ "生成PPT"/"做slides"                 → 委托 fpptx
  ├─ "更新文档"/"update report"           → 工作流 A（增量更新）
  ├─ "整合"/"合并"/"consolidate"          → 工作流 B
  ├─ "拆分"/"split"                       → 工作流 C
  ├─ "导出Word/PPT"/"转Office"/"导入飞书"  → 工作流 D
  ├─ "对比"/"diff"                        → 工作流 E
  ├─ 输入是 PDF（排版/转飞书/翻译/导出）   → 委托 fpdf
  └─ "找文档"/"有哪些关于X的文档"         → Step S
```

## 文档父子层级规则

**默认父目录**：配置的 `wiki_nodes.default`（真值在私有配置，本仓库只有 `.example` 占位符）。

**任务级判断**：
- 用户给出父文档 URL → 以该 token 为 `--parent-token`
- "扩展"/"增加"/"补充"已有文档 → 新建子文档放在**同一父文档下**（从源 URL 反推 parent token）
- 未指定且无法推断 → 用默认父目录

**新建 vs 追加**：
- 独立模块（报价表、规格表、附件清单）→ **新建子文档/sheet**
- 改原文措辞/删除/替换 → 原文档内 `str_replace` / `block_*`

**Sheet 导入**：`sheets +workbook-import` 的 `--folder-token` **只接受 Drive folder token**，
不接受 wiki node token；导入 Drive 后需 `wiki +node-create --node-type shortcut` 挂到 wiki 父节点。

**Why**：飞书没有"移动文档到 wiki 节点"的直接 API。子文档散在 Drive 根目录用户找不到（2026-07-08 踩过）。

## 工作流 0：创建新文档

1. **构造内容**：标题 `# ## ###` 三级无手动编号；表格用 XML + `<colgroup>`（宽度和 = 822）；图表委托 fdiagram
2. **创建**：`fcore doc create <parent> "<标题>" <内容文件|->`
3. **验证（必做，ok:true 不代表生效）**：
   ```bash
   fcore doc get <doc> full
   fcore fmt-xml <导出的XML>      # colgroup/手动编号/H4+/分割线 一次报全
   ```
4. 追加到线上文档索引

**超长文档（>5,000 块）**：单次请求上限 5,000 块，但同一文档可多次 append 累积到上万块。
块数换算 `1 + <p> + <h> + <table> + 2×<td> + 2×<li>`。按顶层块边界切段逐段 append。

## 工作流 A：增量更新

1. **fetch 必带 `--detail with-ids`**（默认 simple 丢 colgroup width，别用它验）
2. **策略判断**：`grep -c '<whiteboard\|<sheet\|<bitable\|<img\|<file'`
   - 含嵌入资源 → **禁止 overwrite**，只能 `str_replace` / `block_insert_after` / `block_delete`
   - 不含 → 可全量 overwrite
3. 展示结构（H1/H2 + 嵌入资源位置），用户确认范围
4. 编辑，然后**必做验证**（同上，逐项核对）

**编辑安全规则**：
- 多步 block 操作**必须串行**（并行触发版本冲突，静默失败）
- 同一 block 的 `block_replace` 只能执行一次（block_id 会变）
- `str_replace` 不能跨 block；pattern 须文档内唯一
- 白板只能 `block_insert_after` 插入，不能 `str_replace` 插 `<whiteboard>`
- 🚨 **`block_replace --block-id -1` 会截断文档**（`-1` = 到文档末尾）。2026-11-03 实测：
  改标题时 19.5KB 正文只剩 6.2KB

**改文档标题**：本地有完整 XML → 改 `<title>` 后整篇 overwrite。
❌ `block_replace --block-id -1`（截断）｜❌ wiki `update_title`（缺 scope 报 99991679）。

**误操作恢复**：`docs +history-list` 取 `history_version_id` → `docs +history-revert`。
`+fetch --revision-id N` 不能预览历史版本（返回空）。

## 工作流 B / C / D / E

| 工作流 | 用途 | 步骤要点 |
|---|---|---|
| B 多文档整合 | 合并多份文档 | 搜索 → 全部 fetch → 去重 → 合并方案 → 用户审批 → 创建 |
| C 大文档拆分 | 拆成子文档 | fetch → 分析 H1/H2 边界 → 方案 → 审批 → 创建（子文档 MUST 用源文档 URL token 作 `--parent-token`）|
| D 双向转换 | 飞书↔Office | 飞书→Office 走 OfficeCLI；Office→飞书 转 DocxXML 再 create |
| E 文档对比 | 两文档比对 | 取内容 → 按章节对齐 → 输出对比报告 |

## 图：架构图 vs 数据图

| 图类型 | 走法 |
|--------|------|
| 架构/流程/时序/思维导图 | **fdiagram**（飞书画板，就地嵌入） |
| 数据/分析图（折线/柱状/散点/热力图） | **工作流 G** → python 脚本 → 独立子文档 |

工作流 G 的完整步骤 → `references/figure-workflow.md`（每图一子文档，含图/解读/代码 3 段，
父文档只放链接不复制图）。

## PDF 处理 → 委托 fpdf

**任何以 PDF 为输入的操作都走 fpdf**，不要在本 skill 里临时用 MCP/外部工具对付。

| 用户说法 | 委托命令 |
|---------|---------|
| "PDF 转飞书"/"PDF 排版"/"处理这个 PDF" | `bash ~/.claude/skills/fpdf/scripts/run.sh "<路径>"` |
| 同上 + 导出 Word | 加 `--word` |
| "翻译 PDF" | 加 `--trans` |

本 skill 只在 fpdf 需要嵌入已有文档时参与（`block_insert_after`）。

## 文档树 → 合订本 PDF

把 wiki 节点及其全部子文档导出成带封面/目录页码/书签的 PDF（用于课程/手册类知识产品）：

```bash
bash ~/.claude/skills/ffeishu/scripts/export_whole_tree_pdf.sh \
  <root_wiki_node_token> <root_obj_token> /tmp/bookout "书名" "总览前缀"
```

输出目录**必须在 cwd 或 /tmp**（lark-cli 路径 allowlist，否则白板导出静默失败）。
完整参数、踩坑、依赖 → `references/book-pdf.md`。

## 格式约束

| 规则 | 怎么做 |
|---|---|
| 标题 | 只用 `# ## ###`，禁止 H4+，**不加手动编号**（飞书自动生成目录） |
| 标题配色 | **H1 = 蓝字无底色**（`<h1><span text-color="blue">`）；H2 及以下默认黑，不染色 |
| 分割线 | 禁止 `<hr/>` 和 `---` |
| 表格 | 先问"该不该用表"：2 列术语→定义列表；步骤→有序列表；≥5 列→嵌套列表；等权横向对比才用真表 |
| 表格 XML | `<colgroup>` 宽度和 = **822** |
| 正文加粗 | 克制，`<p>` 里的 `**x**` 降级为纯文本；只有列表项短术语（≤12 字 + `：`）保留 |

机械可判的部分跑 `fcore fmt-xml` 一次报全。**完整清单**（唯一真相源）→
`references/write-checklist.md` §2；**写代码时的速查摘要** → `references/format-summary.md`。

## 委托速查

| 操作 | 走哪 |
|------|------|
| 文档搜索/读取/编辑/创建 | `fcore doc ...` / `fcore search` |
| 知识库节点操作 | `fcore doc ...` + `lark-cli wiki +node-*` |
| 创建/编辑 .docx | 委托 fdocx（OfficeCLI） |
| 生成 PPT | 委托 fpptx |
| 画图表 | 委托 fdiagram |
| 数据图子文档 | 本 skill 工作流 G |
| PDF 提取+排版 | 委托 fpdf |
| 格式断言 | `fcore fmt-xml` |

## 参考

| 文件 | 内容 |
|---|---|
| `references/workflows.md` | 工作流 0/A/B/C/D/E 完整步骤与命令 |
| `references/figure-workflow.md` | 工作流 G 完整步骤（数据图子文档） |
| `references/book-pdf.md` | 合订本 PDF 参数与踩坑 |
| `references/write-checklist.md` | **格式约束唯一真相源** |
| `references/lark-cli-cheatsheet.md` | lark-cli 命令速查 + base 字段操作 + 踩坑 |
| `references/feishu-office-bridge.md` | 飞书↔Office 转换细节 |
| `references/setup.md` | 安装、配置、用户配置详解 |

**合订本 PDF 工具链**（`scripts/`）：`export_whole_tree_pdf.sh` 一键出书；
分步用 `collect_pages.py`（抓页面）→ `docxxml2html.py`（转 HTML）→ `html2pdf.js`（打印）
→ `add_bookmarks.py`（加书签）。

## 文档索引

创建/编辑的文档追加到私有索引 `<ccprivate>/skill/ffeishu.yaml` 的 `doc_index`
（title/url/doc_token/parent_doc/description），不进公开仓库（避免暴露个人飞书链接）。

```bash
source ~/.claude/skills/ffeishu/references/lark_env.sh
lark_doc_index --add "<标题>" "<url>" "<doc_token>" "<parent>" "<说明>"
lark_doc_index "<关键词>"      # 检索
```

> flogme 管辖的文档（OKR/SUM/Worklog）索引在 flogme 自己的文档里，不在本索引。
