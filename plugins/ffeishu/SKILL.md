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

编排层，不重新实现底层工具。委托飞书操作给 lark-cli，Office 给 OfficeCLI，PPT 给 fpptx，图表给 fdiagram

## 前置条件

- lark-cli 命令参考 → `references/lark-cli-cheatsheet.md`。本 skill 直接调 lark-cli，不依赖 lark-* skill。
- 跨格式转换（涉及 Office 时）→ `references/feishu-office-bridge.md`

## 配置

> 📖 完整说明 → [config.aiagt.dev](https://config.aiagt.dev/ffeishu)

配置查找由**单一实现** `references/plugin_env.sh`（Python 版 `config_env.py`）统一决定，
所有 skill 共用同一条 8 级链（完整清单见「用户配置」一节）。

| 你是哪类用户 | 配置写在哪 |
|---|---|
| plugin 安装（`/plugin install`） | `claude plugin configure ffeishu@<market>` 弹窗填；值落 `settings.json` 的 `pluginConfigs` 或 `.credentials.json` 的 `pluginSecrets` |
| ccconfig 用户 | `$CCPRIVATE_HOME/conf/ffeishu.yaml`（旧位置 `skill/ffeishu.yaml` 仍兼容） |
| 独立用户（git clone） | `cp config.yaml.example config.yaml` 填真实值，或 `$CLAUDE_PLUGIN_DATA/config.json` |

⚠️ **不要**把配置写进 `<skill目录>/config.yaml` 然后指望它跨 `/plugin update` 存活 ——
plugin 用户装的是 `cache/<market>/<plugin>/<版本号>/` 只读副本，更新即整目录替换。

需提前准备：
- 飞书租户（企业版/个人版）
- `npm install -g @larksuite/cli` → `lark-cli auth login`
- wiki 节点 token（新文档默认父目录）

> 完整格式约束+安全规则参考 → `references/write-checklist.md`

## 文档父子层级规则

**默认父目录**：`config.yaml → wiki_nodes.default`（真实值在私有 `ccprivate/skill/ffeishu.yaml`，本仓库只放占位）。

**任务级父目录判断**：
- 若用户明确给出父文档 URL → 以该 URL token 为 `--parent-token`
- 若在已有文档基础上"扩展"/"增加"/"修改补充" → 新建子文档/子表格放在**同一父文档下**（从源文档 URL 反推 parent token）
- 若用户未指定父目录且无法从上下文推断 → 使用默认父目录

**新建 vs 追加**：
- 补充内容（报价表、规格表、附件清单等独立模块）→ **新建子文档/sheet**，`--parent-token` 用源文档 wiki token
- 修改原文措辞/删除/替换 → 在原文档内 `str_replace` / `block_*`

**Sheet 导入的特殊处理**：
- `sheets +workbook-import` 的 `--folder-token` **只接受 Drive folder token，不接受 wiki node token**
- 导入到 Drive 后，需通过 `wiki +node-create --node-type shortcut --parent-node-token <wiki> --obj-type sheet --origin-node-token <sheet>` 挂到 wiki 父节点下

**Why**：飞书文档没有"移动"到 wiki 节点的直接 API，只能通过创建节点关联。子文档散落在 Drive 根目录会导致用户找不到（2026-07-08 已踩坑）。
**How to apply**：每次创建/导入文档前，先判断父目录，`--parent-token` 必须显式传递。

## 快速决策

```
用户意图
  ├─ "创建文档"/"写文档"/"生成报告"        → 工作流 0: 创建新文档
  ├─ "创建表格"/"画表格"                   → 工作流 0 + 表格 XML
  ├─ "画架构图"/"流程图"/"时序图"          → 委托 fdiagram skill
  ├─ "生成PPT"/"做slides"                 → 委托 fpptx skill
  ├─ "更新文档"/"update report"           → 工作流 A: 增量更新
  ├─ "整合"/"合并"/"consolidate"          → 工作流 B: 多文档整合
  ├─ "拆分"/"split"                       → 工作流 C: 大文档拆分
  ├─ "导出Word/PPT"/"转Office"            → 工作流 D: 飞书→Office
  ├─ "导入飞书"                           → 工作流 D: Office→飞书
  ├─ "对比"/"diff"                        → 工作流 E: 文档对比
  ├─ 输入是 PDF（排版/转飞书/翻译/导出）   → **委托 fpdf skill**（见下方「PDF 处理」）
  └─ "找文档"/"有哪些关于X的文档"         → Step S: 文档发现
```

---

## PDF 处理 → 委托 fpdf skill

**任何以 PDF 为输入的操作都走 fpdf，不要在本 skill 里临时用 MCP/外部工具对付。**
fpdf 负责「精确拆解版式 → 飞书精排」，包括复杂表格/分栏/图片/公式，是本仓 PDF 能力的唯一入口。

| 用户说法 | 委托命令 |
|---------|---------|
| "PDF 转飞书"/"PDF 排版"/"处理这个 PDF" | `bash ~/.claude/skills/fpdf/scripts/run.sh "<路径>"` |
| "PDF 转飞书并导出 Word" | 同上 `--word` |
| "翻译 PDF" | 同上 `--trans` |

fpdf 创建完成后，本 skill 只在其需要嵌入已有文档时参与（`block_insert_after`）。
PDF 的完整执行流程、依赖预检、父文档配置 → 见 `../fpdf/SKILL.md`。

---

## 飞书文档树 → 合订本 PDF（反向导出）

把一个 wiki 节点及其**全部子文档**（+ 子文档里的飞书画板）导出成一本带封面、目录页码、章节标签、书签的 PDF。用于发布课程/手册类知识产品。

```bash
bash ~/.claude/skills/ffeishu/scripts/export_whole_tree_pdf.sh \
  <root_wiki_node_token> <root_obj_token> /tmp/bookout "书名" "总览标题前缀"
```

| 参数 | 说明 |
|------|------|
| `root_wiki_node_token` | 父节点 node_token（顶层目录） |
| `root_obj_token` | 该节点自身文档的 obj_token（会作为「导航」章节） |
| 输出目录 | **必须**在 `cwd` 或 `/tmp` 下（lark-cli 路径 allowlist） |
| 书名 | 输出 `<书名>.pdf`，同时用作封面标题与页眉 |
| 总览前缀 | 可选，如 `"BADTI "`；命中的子文档排在单元之前 |

流程：抓内容 → 导画板图 → DocxXML→HTML → chromium 打印 → 回填页码（迭代收敛）→ 加书签。

**产出特征**：A4 · 封面 · 目录（中文标题 + 页码 + 可点击锚点）· 每章标签（单元/案例/总览）· 内嵌画板图 · PDF 书签（阅读器侧栏可导航）· 元数据。

依赖：lark-cli（已 auth）、`python3` + pymupdf、`node` + playwright-core + chromium（脚本自动探测 `~/.npm/_npx/*/node_modules` 与 `~/.local/state/pw-chromium/chrome`，可用 `PW_NODE_MODULES` / `PW_CHROME` 覆盖）。

**踩坑**（已在脚本内处理，改动时勿回退）：
- 🚨 **`--output`/`--content`/`--file` 等 lark-cli 路径参数有 allowlist（cwd / `/tmp` / `~/files`）**。输出目录放到别处 → `whiteboard +export` **静默失败**、画板全丢。脚本开头有 guard 直接报错。
- `whiteboard +export --output <dir>` 会在文件名前加 `whiteboard_` 前缀；给完整文件名（`<tok>.jpg`）才可控
- `docs +fetch` 对**非 docx 节点**（附件/表格）返回空 → 抓取前必须过滤 `obj_type == 'docx'`，否则 JSON 解析炸
- python 里调 lark-cli 必须 `stdin=subprocess.DEVNULL`（否则 lark-cli 可能去读 stdin）
- **PDF 导出不渲染画板**（只显示占位框）→ 画板要用 `whiteboard +export --output-type preview` 单独取图再嵌入
- 目录页码需**迭代一次收敛**：加页码会轻微改变分页，脚本已跑两轮
- `add_bookmarks.py` 输出 `<书名>.final.pdf`，脚本最后 `mv` 成正式名；别只保留未加书签的版本

---

## 文档格式规范（所有创建/编辑遵循）

> **格式硬约束唯一真相源 → `references/write-checklist.md`**。本节为实现摘要，规则变更以 write-checklist §2 为准。

### 标题
- 纯 `# ## ###` 层级，**不加手动编号**（飞书自动生成目录）
- H1/H2/H3 三级，**禁止 H4+**
- 非正文内容用 `>` 引用包裹，不出现在目录；禁止 `<hr/>` 分割线
- **文档标题用简单连贯的中文短名**（2-6 字），不带长前缀/后缀/副标题。同项目多文档可用统一短词风格：`项目概览` `厂商对比` `工作流介绍` `案例调研` `通道选型`
- 禁止风格：`厂商盘点 — 国产图生3D 工具全景`、`类似案例调研 — 别人怎么做...` 这类「长主语 — 解释副标题」

#### 标题样式（硬约束）
**H1 = 蓝色文字、无底色；H2 及以下 = 默认黑色。** 标题不加 `<b>`、不加底色。

```xml
<h1><span text-color="blue">一级标题</span></h1>   <!-- 蓝字，无底色 -->
<h2>二级标题</h2>                                   <!-- 默认黑 -->
<h3>三级标题</h3>                                   <!-- 默认黑 -->
```

- ❌ `<h1><span background-color="blue">`（蓝底横幅）→ ✅ 只染文字
- ❌ `<h2><span text-color="...">`（H2 彩色）→ ✅ `<h2>` 裸标签
- ❌ `<h1 text-color="...">`（属性被静默丢弃）→ ✅ 必须用 `<span>` 包裹
- 飞书 `text-color` **只认 7 个基础色相**（`red orange yellow green blue purple gray`）；RGB/hex/数字/`light-*` 前景全被丢弃或归一成 blue
- **验色导出 docx 看 `w:color`，或 PDF 转 PNG 肉眼看**（`docs +fetch` 只见存储值）

### 正文加粗（硬约束：克制）
**正文段落不撒黑体** —— 满篇加粗"很吵闹"，反而看不出重点。`<p>` 里的 `**x**` 一律降级为纯文本；仅**列表项的短术语**（`**优点**：成本低`，术语 ≤12 字且紧跟 `：`/`—`）保留加粗。要强调优先拆列表或改小标题。

### 表格 —— 先问「该不该用表」
⚠ **两列表（术语→说明）用表格可读性很差**。按内容选形态：

| 内容形态 | 用什么 |
|---------|--------|
| 术语 → 说明（2 列） | 无序列表 `<li><b>术语</b>：说明</li>` |
| 步骤 / 阶段 / 序号 | 有序列表 `<ol>` |
| 3–4 列、字段等权、需横向对比 | 真表格 |
| ≥5 列 | 嵌套列表（首列主项 + 其余列为子项） |
| 单列枚举 | 无序列表 |

- **只有「等权字段横向对比」才用表格**；层次关系用嵌套列表
- **禁止 Markdown 表格**（列宽被固定成 120），全部用 `<table>` XML
- **要控制列宽必须显式写 `<colgroup>`，宽度之和 = 822**（`round(822/N)` 均分；首列约 26–30%，其余均分）；单元格内容包在 `<p>` 里
- 列表支持**两级嵌套**，子列表必须放进 `<li>` 内

> ⚠ **旧写法 `<lark-table rows="N" cols="N" column-widths="...">` 已废弃**：2026-10-18 实测该标签
> 被渲染器忽略 —— 列宽全变 120、第二个 `<lark-tr>` 被吞（只剩首行）。现存文档用标准 `<table>`，
> 本文件此前教的 lark-table 语法与实态不符，已更正。

> 🚨 **Markdown 表格分隔行有 `|-|-|` 与 `|------|` 两种**。判定正则若写成 `-{2,}` 会漏掉单横线那种，
> **分隔行被当数据** → 整表错位（首组变 `-`、表头错配）。2026-10-25 实际踩到，表现为"表格都是乱的"。
> 正确判定：`all(re.fullmatch(r':?-+:?', c) for c in cells)`

#### 手机竖屏优化（≥4 列必须转换）
5 列时每列仅 164px ≈ 7 个中文字，手机上折行成"豆腐块"。**列数 ≥ 4 → 转「分组竖排」两列表**：

```xml
<table><colgroup><col width="240"/><col width="582"/></colgroup><tbody>
  <tr><td colspan="2" background-color="light-blue"><p><b>第 1 列的值（分组标题）</b></p></td></tr>
  <tr><td><p>第 2 列表头</p></td><td><p>第 2 列值</p></td></tr>
</tbody></table>
```

> ⚠ **旧写法 `<lark-table rows="N" cols="N" column-widths="...">` 已废弃**：2026-10-18 实测该标签
> 被渲染器忽略 —— 列宽全变 120、第二个 `<lark-tr>` 被吞（只剩首行）。现存文档用标准 `<table>`，
> 本文件此前教的 lark-table 语法与实态不符，已更正。

### 图表 → 委托 fdiagram skill
- 架构图/流程图/时序图等由 fdiagram 生成，通过 `block_insert_after` 插入
- 图表在对应内容位置嵌入，不在末尾

### 批量转换 Markdown → DocxXML
长文档成批入库（如课程化 18 篇）用 `references/md2docxxml.py`：

```bash
python3 ~/.claude/skills/ffeishu/references/md2docxxml.py input.md out_name "--root=画板根节点名"
# 产出 ./gen/out_name.xml，再 cat 进 lark-cli
cat gen/out_name.xml | lark-cli docs +create --api-version v2 --parent-token <node> \
  --as user --title "标题" --doc-format xml --content -
```

自带：三级标题配色 + 手机竖屏宽表转竖排 + 自动剥离手动编号 + 从大纲生成结构 mindmap。

### 缩写
- 首次出现用 DFN 格式：`中文全称（English Full Name, ABBR）`

### 父目录
- **子文档**（用户指定父文档URL）：提取 token 作为 `--parent-token`。**禁止**套用默认值
- **独立文档**（用户未指定位置）：默认 `--wiki-node <token>`（config.yaml → wiki_nodes.default）

---

## Step S: 文档发现

```bash
lark-cli drive +search --query "关键词" --doc-types "wiki,doc,docx" --page-size 20
lark-cli drive +search --query "关键词" --doc-types "wiki,doc,docx" --only-title
lark-cli drive +search --query "关键词" --space-ids "space_id_1,space_id_2"
```

列出知识空间：`lark-cli wiki +space-list`

---

## 工作流 0: 创建新文档

### Step 0: 内容构造
1. 标题：`# ## ###` 三级，检查无 `数字[.、]` 前缀
2. 表格：`<table>` XML（含 `<colgroup>`，宽度之和 = 822）
3. 图表：委托 fdiagram skill，通过 `block_insert_after` 嵌入

### Step 1: 创建

```bash
cat << 'EOF' | lark-cli docs +create --api-version v2 --wiki-node <token> --as user --doc-format markdown --content - --title "标题"
内容
EOF
```

常见错误: ❌ `--folder-token` | ❌ `--markdown "内容"` | ✅ `--doc-format markdown --content -` + heredoc

### Step 2: 验证（必做）

```bash
lark-cli docs +fetch --api-version v2 --doc "{token}" --detail full
```
检查：
- `grep '<colgroup'` → 列宽之和 = 822
- `grep '^#'` → 无 `一、` `1.1` `(1)` 等手动编号前缀
- 白板/嵌入资源数量与预期一致

创建后追加到「线上文档索引」表格。

---

## 工作流 A: 增量更新

### Step 1: fetch（必带 `--detail with-ids`）

```bash
lark-cli docs +fetch --api-version v2 --doc "{token或URL}" --detail with-ids
```

### Step 2: 策略判断（fetch 后立即执行）

```bash
# 检查嵌入资源
grep -c '<whiteboard\|<sheet\|<bitable\|<img\|<file'
```
- **含嵌入资源 → 禁止 overwrite**。只能用 `str_replace` / `block_insert_after` / `block_delete`
- 不含 → 全量重写可用 overwrite

### Step 3: 展示结构
标注 H1/H2 层级 + 嵌入资源位置，用户确认变更范围。

### Step 4: 编辑

命令选择：
```
替换文本（单行内）     → str_replace --pattern "..." --content "..."
替换整个 block          → block_replace --block-id "xxx" --content "..."（注意：block_id 会变）
插入到 block 后         → block_insert_after --block-id "xxx" --content "..."
删除 block              → block_delete --block-id "xxx"
追加到末尾              → append
```

安全规则：
- 多步 block 操作**必须串行**（并行触发版本冲突，静默失败）
- 同一 block 的 `block_replace` 只能执行一次
- `str_replace` 不能跨 block；pattern 须文档内唯一
- 白板只能 `block_insert_after` 插入，不能 `str_replace` 插 `<whiteboard>` 标签

### Step 5: 验证（必做，ok:true 不代表生效）

```bash
lark-cli docs +fetch --api-version v2 --doc "{token}" --detail full
```
逐项检查：
1. `grep '<colgroup'` → 列宽之和 = 822
2. `grep '^#'` → 无手动编号
3. `grep '<whiteboard token=' | wc -l` → 数量与编辑前一致
4. 内容变更已生效

```bash
# 追加（示例）
cat << 'EOF' | lark-cli docs +update --api-version v2 --doc <doc_id> --as user --mode append --doc-format markdown --content -

# 替换章节（示例）
cat << 'EOF' | lark-cli docs +update --api-version v2 --doc <doc_id> --as user --mode replace_range --selection-by-title "章节标题" --doc-format markdown --content -
```

详见 `references/update-workflow.md`

---

## 工作流 B: 多文档整合

```
搜索相关文档 → 全部fetch → 去重+结构分析 → 合并方案 → 用户审批 → 创建
```

详见 `references/merge-workflow.md`

---

## 工作流 C: 大文档拆分

```
fetch 源文档 → 分析H1/H2边界 → 拆分方案 → 用户审批 → 创建子文档
```

子文档 MUST 使用源文档 URL 的 token 作为 `--parent-token`。

详见 `references/split-workflow.md`

---

## 工作流 D: 飞书↔Office 双向转换

**飞书→Office（导出）：**
1. `docs +fetch` 获取内容 → OfficeCLI JSON
2. `officecli add` / `officecli set` 写入 .docx
3. PPT 委托 fpptx skill

**Office→飞书（导入）：**
1. `officecli get` 读取 .docx
2. 转为飞书 DocxXML
3. `docs +create --api-version v2` 上传

详见 `references/feishu-office-bridge.md`

---

## 工作流 E: 文档对比

1. 获取两个文档内容
2. 按章节对齐
3. 输出对比报告

---

## 工作流 G: 图子文档生成（数据/分析图）

> 架构/流程图委托 fdiagram。本工作流用于**数据/分析图**（matplotlib/plotly）：每个图建独立子文档。
> 内容规范见 `../fwstd-report/SKILL.md`，触发见 `../fworch-report/SKILL.md` 工作流 G。

### 完整流程

```
父文档（已有）
  ↓ G.1 写 python 脚本 → /tmp/figs/<名>.py
  ↓ G.2 跑脚本 → /tmp/figs/<名>.png
  ↓ G.3 创建子文档（含图/解读/代码 3 段）
  ↓ G.4 父文档 block_insert_after 嵌入图块
父文档（含图嵌入 + 详见子文档链接）
```

### Step G.1: 写 python 脚本

```python
# /tmp/figs/<图名>.py
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC']  # 中文
plt.rcParams['axes.unicode_minus'] = False  # 负号

fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
# ... 数据 + 绘图 ...
plt.tight_layout()
plt.savefig('/tmp/figs/<图名>.png', dpi=150, bbox_inches='tight')
print('✅ /tmp/figs/<图名>.png')
```

```bash
python3 /tmp/figs/<图名>.py
```

### Step G.2: 验证图生成

```bash
ls -la /tmp/figs/<图名>.png
file /tmp/figs/<图名>.png  # 确认 PNG
```

### Step G.3: 创建子文档（3 段式）

子文档用 lark-cli docs +create，**父文档 token 作为 --parent-token**：

```bash
PARENT_TOKEN="<父文档 URL 或 token>"
FIG_NAME="<图名，简洁中文>"

cat << EOF | lark-cli docs +create --api-version v2 \
  --parent-token "$PARENT_TOKEN" --as user \
  --title "$FIG_NAME" --doc-format markdown --content -

# $FIG_NAME

## 图

![$FIG_NAME](attachment://<图名>.png)

> 详细解读见下文

## 解读

> 此处填写图的分析：数据来源、对比维度、关键洞察、注意点、不确定项

- 关键发现 1
- 关键发现 2
- 关键发现 3
- 不确定项：[待确认] / [数据有限]

## 代码

\`\`\`python
# 完整可重跑的 python 脚本
$(cat /tmp/figs/<图名>.py)
\`\`\`

EOF
```

**输出**：子文档 URL 和 token（保存到父文档嵌入步骤）。

### Step G.4: 父文档嵌入图块

**先 fetch 父文档拿到 block 结构**：

```bash
lark-cli docs +fetch --api-version v2 --doc "$PARENT_TOKEN" --detail with-ids
```

**找到要插入位置的 block_id**（如 `<target_block_id>`），用 `block_insert_after` 嵌入子文档链接：

```bash
CHILD_TOKEN="<子文档 token>"
CHILD_URL="<子文档 URL>"

# 在目标 block 后插入图块（链接到子文档）
cat << EOF | lark-cli docs +update --api-version v2 \
  --doc "$PARENT_TOKEN" --as user --mode block_insert_after \
  --block-id "<target_block_id>" --doc-format markdown --content -

**$FIG_NAME**：详见 [$FIG_NAME]($CHILD_URL)

EOF
```

**关键原则**：
- **绝不复制图到父文档**（飞书是引用，子文档 = 唯一源）
- 父文档用 `block_insert_after` 不能用 `str_replace`（避免破坏嵌入资源）
- **多步操作必须串行**（并行触发版本冲突）

### Step G.5: 验证

```bash
lark-cli docs +fetch --api-version v2 --doc "$PARENT_TOKEN" --detail full | grep -c "$FIG_NAME"
# 期望：≥ 1
```

### 常见错误

| 错误 | 原因 | 修复 |
|------|------|------|
| `media-insert` 路径错 | 路径必须相对 git 根目录 | `cd <git 根> && lark-cli drive +upload` |
| `block_insert_after` 找不到 block | block_id 错了 | 重 fetch 带 `--detail with-ids` |
| 子文档父目录错 | `--parent-token` 用了 doc token 而非 wiki node | 父文档 URL 提取的 token 即 wiki node |
| 中文乱码 | matplotlib 字体未设 | `plt.rcParams['font.sans-serif']=['Noto Sans CJK SC']` |

### 命名约定

- 子文档名 = 图名（简洁中文，与正文用语一致）
- `/tmp/figs/<图名>.{py,png}` 命名一致（`占比分析.py` → `占比分析.png`）

---

## 工具委托速查

| 操作 | 工具 | 命令 |
|------|------|------|
| 搜索文档 | lark-drive | `lark-cli drive +search` |
| 读取文档 | lark-doc | `lark-cli docs +fetch --api-version v2` |
| 编辑文档 | lark-doc | `lark-cli docs +update --api-version v2` |
| 创建文档 | lark-doc | `lark-cli docs +create --api-version v2` |
| 知识库操作 | lark-wiki | `lark-cli wiki +node-*` |
| 创建/编辑 .docx | OfficeCLI | `officecli add/set/get` |
| 生成 PPT | fpptx | 委托 fpptx skill |
| 画图表 | fdiagram | 委托 fdiagram skill |
| 数据图（图子文档） | ffeishu 本工作流 G | lark-cli + python |
| 文件上传 | lark-drive | `lark-cli drive +upload` |
| PDF 提取+翻译+排版 | fpdf | 委托 fpdf skill（`fpdf/scripts/run.sh`） |

---

## 用户配置

用户说"配置 ffeishu"时，读取 `config.yaml` 展示可配置项，用 AskUserQuestion 让用户修改，写回文件。

配置文件按以下顺序找（命中即用，写入也写**命中的那个**）：
1. `$FFEISHU_CONFIG`（环境变量显式指定）
2. `~/.claude/skill-config/ffeishu.yaml` —— **plugin 安装的用户写这里**（cache 之外，更新不丢）
3. `<skill目录>/config.yaml` —— git clone / ccconfig 用户

```bash
cfg="$FFEISHU_CONFIG"
for p in ~/.claude/skill-config/ffeishu.yaml "$SKILL_DIR/config.yaml"; do
  [ -z "$cfg" ] && [ -f "$p" ] && cfg="$p"
done
cat "${cfg:-$SKILL_DIR/config.yaml}"
```

配置项说明见 `config.yaml` 注释。用户直接编辑该文件也可，无需重启。

---

## 参考手册

> 完整格式约束、命令速查、所有陷阱 → `references/write-checklist.md`
> Markdown → DocxXML 转换器 → `references/md2docxxml.py`（标题配色 + 表格/列表选型 + 自动结构白板）
> 文档树 → 合订本 PDF 工具链 → `scripts/`（`export_whole_tree_pdf.sh` 一键；`docxxml2html.py` / `html2pdf.js` / `collect_pages.py` / `add_bookmarks.py` 分步）

---

## 文档索引

> ffeishu 创建/编辑的文档。**文档索引统一存私有 `ccprivate/skill/ffeishu.yaml` 的 `doc_index`**（title/url/doc_token/parent_doc/description），不进公开仓库（避免暴露个人飞书链接）。
> 本仓库只放占位模板。查询方式：`lark_conf` 读取 `ccprivate/skill/ffeishu.yaml` 的 `doc_index`，或 `lark-cli drive +search`。

### 常用 Wiki 节点（占位符，真实值在 ffeishu.yaml `wiki_nodes`）

| 用途 | Token | URL |
|------|-------|-----|
| Claude 工作 wiki（默认父目录） | `<token>` | https://<tenant>.feishu.cn/wiki/<token> |
| OKR/SUM 文档父目录 | `<token>` | https://<tenant>.feishu.cn/wiki/<token> |

> **注意**: flogme 管辖的文档（OKR/SUM/Worklog）索引在 `skills/flogme/SKILL.md` 的「线上文档索引」节。ffeishu 索引只记录 ffeishu 直接创建的文档（研究/合并等）。
