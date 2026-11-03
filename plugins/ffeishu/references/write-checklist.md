# 飞书文档写操作参考手册

> 完整格式约束、命令速查、安全规则、验证步骤。**参考手册，非执行入口。**
> **格式硬约束唯一真相源** — 标题/表格/图表/缩写规则以本文件 §2 为准。
> 写操作时关键检查已内联到 `../SKILL.md` 工作流步骤中。

## 0. 策略决策（写前必问）

- [ ] **文档是否含嵌入资源？** fetch 后 grep `<whiteboard\|<sheet\|<bitable\|<img\|<file` 检查
  - 含嵌入资源 → **禁止 overwrite**。只能用 `str_replace` / `block_insert_after` / `block_delete`
  - 不含嵌入资源 → 全量重写可用 overwrite，增量用 str_replace/block_replace
- [ ] **目标文档 block 结构已知？**
  - 否 → 先 `docs +fetch --api-version v2 --doc "{token}" --detail with-ids`，再决定策略
  - 是 → 确认 block_id 未变化（文档可能被他人修改）
- [ ] **跨租户？** 不同域名（`<tenant-a>.feishu.cn` vs `<tenant-b>.feishu.cn`）→ lark-cli 无法访问，需导出本地处理

## 1. 命令选择（按场景）

```
编辑文档
├─ 含白板/嵌入资源           → str_replace / block_insert_after / block_delete（禁止 overwrite）
├─ 全量重写（无嵌入资源）     → overwrite
├─ 插入到特定 block 后       → block_insert_after --block-id "xxx"
├─ 删除特定 block            → block_delete --block-id "xxx"
├─ 替换文本                  → str_replace（pattern 需文档内唯一）
├─ 追加到末尾                → append
└─ 替换章节                  → replace_range（不支持含空行内容，改用 delete_range + insert_after）
```

### 命令参数速查

| 操作 | 正确写法 | 错误写法 |
|------|---------|---------|
| docs +create | `--doc-format markdown --content "..."` | `--markdown "..."` |
| docs +update str_replace | `--command str_replace --pattern "..." --content "..."` | `--json '{"old_str":...}'` |
| docs +update overwrite | `--command overwrite --content "..."` | 缺 `--command` 或 `--content` |
| block_insert_after | `--command block_insert_after --block-id "xxx" --content "..."` | 缺 `--block-id` |
| docs +fetch 验证结构 | `--detail full` 或 `with-ids` | 默认 `simple`（丢 colgroup width） |
| 改文档标题 | `--command overwrite` 传改过 `<title>` 的完整 XML | `block_replace --block-id -1`（会截断文档） |
| wiki 节点删除 | `--space-id <node-get 返回的>` `--obj-type docx` | `+space-list` 的 space_id / 缺 `--obj-type` |
| 回滚版本 | `--history-version-id <history-list 的>` | `--version-id` / `--revision-id <N>` |

## 2. 格式自检（逐项核对）

### 标题
- [ ] 仅用 `# ## ###`（H1-H3），无 H4+
- [ ] **无手动编号**（飞书自动生成目录）。禁止 `一、` `1.1` `(1)` 等前缀
- [ ] 非正文内容（使用说明、参考数据）用 `>` 引用包裹
- [ ] 章节间无 `<hr/>` 分割线
- [ ] **标题为简单连贯中文短名**（2-6 字），不带「长主语 — 解释副标题」；同一项目的子文档用统一短词风格

#### 标题层级样式（硬约束）
**H1 = 蓝色文字、无底色；H2 及以下 = 默认黑色**。标题本身不加 `<b>`（渲染器自带加粗），不加底色。

```xml
<h1><span text-color="blue">一级标题</span></h1>   <!-- 蓝字，无底色 -->
<h2>二级标题</h2>                                   <!-- 默认黑 -->
<h3>三级标题</h3>                                   <!-- 默认黑 -->
```

- [ ] ❌ `<h1><span background-color="blue">`（蓝底横幅）→ ✅ `<h1><span text-color="blue">`（只染文字）
- [ ] ❌ `<h2><span text-color="...">`（H2 彩色）→ ✅ `<h2>` 裸标签，默认黑
- [ ] ❌ `<h1 text-color="...">`（属性被静默丢弃）→ ✅ 必须用 `<span>` 包裹
- [ ] 飞书 `text-color` **只认 7 个基础色相**（`red orange yellow green blue purple gray`）；RGB/hex/数字/`light-*` 前景全被丢弃或归一成 blue
- [ ] **验色必须导出 docx 看 `w:color`，或 PDF 转 PNG 肉眼看**：`docs +fetch` 只返回存储值，不代表渲染色

### 正文加粗（硬约束：克制）
**正文段落里不撒黑体** —— 满篇加粗"很吵闹"，反而看不出重点。

- [ ] `<p>` 里的 `**x**` 一律**降级为纯文本**（转换器默认行为）
- [ ] 仅**列表项的短术语**（`**优点**：成本低`，术语 ≤12 字且紧跟 `：`/`—`/`-`）保留加粗
- [ ] 表格 `<th>` 单元格里的字段名可加粗（表格内做视觉分隔，不算正文）
- [ ] 若确实要强调，优先考虑**拆成列表**或**改成小标题**，而不是加粗

### 表格 —— 先问「该不该用表」
⚠ **不是所有内容都适合表格**。两列表（术语→说明）用表格可读性很差、手机上尤其。**按内容选形态**：

| 内容形态 | 用什么 | 为什么 |
|---------|--------|--------|
| 术语 → 说明（2 列） | **无序列表** `<li><b>术语</b>：说明</li>` | 定义式列表，手机上最易读 |
| 步骤 / 阶段 / 序号（首列是 Step N、第 N 步） | **有序列表** `<ol>` | 顺序本身是语义 |
| 3–4 列、字段等权、需要横向对比 | **真表格** | 列对齐才有对比价值 |
| ≥5 列 | **嵌套列表**（首列主项 + 其余列为子项） | 5 列时每列仅 164px ≈ 7 字，手机必崩 |
| 单列枚举 | 无序列表 | 表格只有一列毫无意义 |

- [ ] **只有「等权字段横向对比」才用表格**；层次关系（主项→明细）用嵌套列表
- [ ] 2 列一律转定义式列表，**不要**做成两列表格

#### 真表格的写法（3–4 列）
- [ ] **禁止 Markdown 表格**（列宽被固定成 120），全部用 `<table>` XML
- [ ] 结构：`<table><colgroup><col width="N"/>…</colgroup><thead><tr><th><p>…</p></th></tr></thead><tbody><tr><td><p>…</p></td></tr></tbody></table>`
- [ ] **colgroup 列宽之和 = 822**（`round(822/N)` 均分：3列→274×3, 4列→205×2+206×2）
- [ ] 首列约 26–30% 宽，其余均分（总和仍须 822）
- [ ] 单元格内容包 `<p>`；不用 `#` 标题符号
- [ ] ⚠ **勿用 `<lark-table rows= cols= column-widths=>`**（旧写法，实测列宽丢失 + 多行被吞；2026-10-18 更正）

#### 🚨 Markdown 表格分隔行解析坑（必读）
Markdown 分隔行有 **`|-|-|` 与 `|------|` 两种**写法。判定正则若写成 `-{2,}` 会漏掉单横线的那种，**分隔行被当成数据行** → 表格整体错位（首组变成 `-`、表头错配）。这是 2026-10-25 实际踩到的 bug，表现为"表格都是乱的"。

```python
# ✅ 正确：容忍单横线
def is_sep(row):
    cs = _cells(row)
    return all(re.fullmatch(r':?-+:?', c) for c in cs)
# ❌ 错误：re.fullmatch(r':?-{2,}:?', c)  —— 漏掉 `|-|-|`
```

### 列表 → 承载层次与枚举
表格的很多用途其实是列表。飞书支持**两级嵌套**（子列表放进 `<li>` 内）：

```xml
<ul>
  <li>一级项
    <ul><li>二级项</li><li>二级项二</li></ul>
  </li>
  <li>一级项二</li>
</ul>
<ol><li>第一步</li><li>第二步<ol><li>子步</li></ol></li></ol>
```
- [ ] 子列表**必须**放在 `<li>` 内，不能裸放在 `<ul>` 下
- [ ] 层级只可靠支持两级；三层以上改用「小标题 + 列表」
- [ ] `<ol>` 默认 `seq="auto"` 自动编号；需要从指定数字开始时设 `seq="3"`
- [ ] 列表项自带的圆点与数字**不要手写**（不要写 `1. xxx` 文本，用 `<ol>`）

### 图表 → 委托 fdiagram skill
- [ ] 架构图/流程图等由 fdiagram 生成，通过 `block_insert_after` 嵌入
- [ ] 图表在对应内容位置嵌入，不在末尾堆砌

#### 在 XML 内容里直接嵌画板（批量建文档用）
`docs +create` / `docs +update --command overwrite` 的 XML 里可直接写画板，**一步到位**，无需再 block_insert_after：

```xml
<whiteboard type="mermaid">
mindmap
  root((根节点))
    分支一
      叶子甲
</whiteboard>
```
- [ ] `type` 可为 `mermaid` / `plantuml` / `svg` / `blank`；`src=<token>` 表示复制已有画板
- [ ] mindmap 缩进**只可靠支持两级**（H1 → H2），三层以上会渲染异常
- [ ] 节点文本里**不能有** `"` `'` `` ` `` `/` `\`（会破坏 mermaid 语法）→ 生成前过滤
- [ ] 节点文本过长会溢出框 → 截断到 ~14 个中文字符
- [ ] **验证画板是否真的渲染**：`lark-cli whiteboard +export --whiteboard-token <tok> --output-type preview --output b.jpg`
  - ⚠ **PDF 导出不渲染画板**（只显示"画板"占位框），别据此判断画板坏了
  - `+export` 必须带 `--output-type`（`preview` / `svg` / `source` / `raw`）；`preview` 返回 jpg，输出路径扩展名要匹配

### 文本
- [ ] 缩写首次出现用 DFN 格式：`中文全称（English Full Name, ABBR）`
- [ ] 链接域名 `www.feishu.cn`，非 `open.feishu.cn`

### 内联样式嵌套（XML 模式）
- [ ] 顺序（外→内）：`<a>` → `<b>` → `<em>` → `<del>` → `<u>` → `<code>` → `<span>` → text，关闭严格逆序

## 3. 执行安全规则

- [ ] 多步 block 操作**必须串行**，不能并行（并行会触发版本冲突，部分操作静默失败）
- [ ] `str_replace` 只能匹配**单行内**文本，不能跨 block
- [ ] 同一 block 的 `block_replace` **只能执行一次**，多次修改需合并
- [ ] `block_replace` 后 block_id **会变化**，后续操作需重新 fetch
- [ ] `replace_range` **不支持含空行**的内容 → 改用 `delete_range` + `insert_after`
- [ ] lark-cli pipe 前先 `sed '/^\[lark-cli\]/d'` 过滤日志行（`tail -n +2` 不稳定）
- [ ] JSON 文件路径**必须相对**：`cd /tmp && --json @file.json`，不能用 `--json @/tmp/file.json`
- [ ] `docs +create` 返回的 URL 域名是 `www.feishu.cn`，浏览器访问需换成 `my.feishu.cn`
- [ ] **`@file` 只能读当前目录 / `/tmp` / `~/files`**：报 `is outside the built-in allowlist` 时改用 stdin —— `cat file | lark-cli ... --content -`
- [ ] **`docs +create`/`+update --content` 支持 stdin**（`--content -`），批量建文档时这是唯一可靠传大块 XML 的方式
- [ ] **批量 overwrite 必须串行**：生成 shell 脚本逐条 `cat xml | lark-cli docs +update --command overwrite`，不要并行；并行会触发版本冲突静默失败

## 4. 写后验证（必做）

- [ ] fetch 验证：`lark-cli docs +fetch --api-version v2 --doc "{token}" --detail full`
  - `ok: true` **不代表生效**，必须 re-fetch
  - 用 `--detail full` 或 `with-ids`（**默认 `simple` 会丢 `<colgroup>` 的 width，看到 `<col/><col/>` 全是假象**）
- [ ] 表格验证：检查 `<colgroup>` 列宽之和 = 822
- [ ] 嵌入资源验证：grep `<whiteboard token=` 数量是否与编辑前一致
- [ ] 标题验证：grep `^#` 检查无手动编号（`一、` `1.1` 等前缀）

### 块数（大文档必查）

飞书单次写请求上限 **5,000 块**，超了报 `DOC_OPERATION_BLOCK_LIMIT`。

- [ ] `actual` 是**这一次请求**的块数，**不是文档总量** —— 同一文档多次 append 可以累积到上万块
- [ ] 块数换算式（实测标定）：`1 + <p> + <h> + <table> + 2×<td> + 2×<li>`
  - 表格每个单元格算 **2 块**（单元格本身 + 内部段落），`<tr>`/`<colgroup>` 不单独计
- [ ] 长文入库：按顶层块边界切成 <4500 块的多段，逐段 append 到**同一文档**
  - 实测 415 页 / 158 表 / 43 图合并为一篇：17,563 块 / 1.2MB，分 5 段追加全部成功
  - 单段超限时别试图「一次传大文件」——飞书也会 timeout

## 4b. 危险操作黑名单

### ❌ `block_replace --block-id -1` 会截断文档

`--block-id -1` 是「从这个 block 一直到**文档末尾**」，不是「最后一个 block」。
2026-11-03 实测：想改文档标题，用它替换了 19.5KB → 6.2KB，**正文被砍掉八成**。

```bash
# ❌ 会删掉后面所有内容
--command block_replace --block-id -1 --content '<title>新标题</title>'
# ✅ 改标题：本地有完整 XML 时整篇 overwrite
--command overwrite --doc-format xml --content @./doc_fixed.xml
```

### ❌ 含 `<img>` 的文档禁止 overwrite

含嵌入资源（img / whiteboard / sheet / bitable / file）只能用
`str_replace` / `block_*`。唯一例外：**你自己刚建的空文档**可 overwrite。

### ✅ 误操作后的恢复路径

```bash
# 1. 查历史版本（history_version_id 不是 revision_id）
lark-cli docs +history-list --doc <token> --as user --format json
# 2. 回滚（参数名是 --history-version-id）
lark-cli docs +history-revert --doc <token> --history-version-id 5120 --as user
```

- `+fetch --revision-id N` **不能预览历史版本**（返回空），只能回滚后再看
- 回滚是异步任务，返回 `task_id` + `status:done` 即成功
- **回滚前先想清楚**：本地有完整 XML 时，`overwrite` 比回滚更可控

## 5. 输出规范

- [ ] 回复中输出：使用的飞书账号 + 文档链接（`my.feishu.cn` 域名）
- [ ] 追加到 ffeishu SKILL.md 底部「线上文档索引」表格

---

> **研究类报告额外约束** → `../fworch-report/SKILL.md`（全局加载）
> **lark-cli 命令完整速查** → `rules/feishu-cli-cheatsheet.md`
> **增量更新详细工作流** → `references/update-workflow.md`
