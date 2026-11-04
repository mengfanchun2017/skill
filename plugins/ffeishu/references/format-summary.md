# 飞书文档格式规范（实现摘要）

> ⚠️ **真相源是 `write-checklist.md` §2**。本文件是给写代码时快速查的摘要，
> 两者不一致时以 write-checklist 为准，并回来修这里。
>
> 机械可判的部分已脚本化：`fcore fmt-xml <file>` 会直接报出违规项，
> 不用人眼逐条核对。

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