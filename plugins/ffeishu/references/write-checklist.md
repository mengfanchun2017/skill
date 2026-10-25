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
| docs +fetch 验证结构 | `--detail full` 或 `with-ids` | 默认（隐藏 colgroup/block ID） |

## 2. 格式自检（逐项核对）

### 标题
- [ ] 仅用 `# ## ###`（H1-H3），无 H4+
- [ ] **无手动编号**（飞书自动生成目录）。禁止 `一、` `1.1` `(1)` 等前缀
- [ ] 非正文内容（使用说明、参考数据）用 `>` 引用包裹
- [ ] 章节间无 `<hr/>` 分割线
- [ ] **标题为简单连贯中文短名**（2-6 字），不带「长主语 — 解释副标题」；同一项目的子文档用统一短词风格

#### 标题层级配色（可选，长文档建议启用）
飞书 `text-color` **只认 7 个基础色相**（`red orange yellow green blue purple gray`）——RGB / hex / 数字 / `light-*` 前景**全被丢弃或归一成 blue**（2026-10-25 实测）。标题标签本身**不支持** `text-color` 属性，必须用 `<span>` 包裹。三级方案：

```xml
<h1><span background-color="blue"><b>一级标题</b></span></h1>   <!-- 深蓝底白字，章节横幅 -->
<h2><span text-color="blue"><b>二级标题</b></span></h2>          <!-- 蓝字加粗 -->
<h3><span text-color="gray"><b>三级标题</b></span></h3>          <!-- 灰字加粗，弱化 -->
```
- [ ] 想要真正的深蓝/中蓝两级区分 → **做不到**，飞书没有细分蓝。用「底/字」差异代替
- [ ] ❌ `<h1 text-color="...">`（属性被静默丢弃）→ ✅ `<h1><span ...>` 
- [ ] **验色必须导出 PDF 转 PNG 肉眼看**：`docs +fetch` 只返回存储值，不代表渲染色

### 表格 → 标准 HTML `<table>` XML
- [ ] **禁止 Markdown 表格**（列宽被固定成 120），全部用 `<table>` XML
- [ ] 结构：`<table><colgroup><col width="N"/>…</colgroup><thead><tr><th><p>…</p></th></tr></thead><tbody><tr><td><p>…</p></td></tr></tbody></table>`
- [ ] **colgroup 列宽之和 = 822**（`round(822/N)` 均分：2列→411×2, 3列→274×3, 4列→205×2+206×2, 5列→164×4+166）
- [ ] 单元格内容包 `<p>`；不用 `#` 标题符号
- [ ] ⚠ **勿用 `<lark-table rows= cols= column-widths=>`**（旧写法，实测列宽丢失 + 多行被吞；2026-10-18 更正）

#### 手机竖屏优化（4 列以上必须转换）
5 列时每列仅 164px ≈ 7 个中文字，手机上必然折行成"豆腐块"。规则：

- [ ] **列数 ≤ 3** → 保持横向表；首列约 26–30% 宽，其余均分（总和 822）
- [ ] **列数 ≥ 4** → 转「分组竖排」两列表：
  ```xml
  <table><colgroup><col width="240"/><col width="582"/></colgroup><tbody>
    <tr><td colspan="2" background-color="light-blue"><p><b>第 1 列的值（作为分组标题）</b></p></td></tr>
    <tr><td><p>第 2 列表头</p></td><td><p>第 2 列值</p></td></tr>
    …（其余表头/值逐行配对）
  </tbody></table>
  ```
- [ ] 转换逻辑：原表每行 → 一个跨列蓝底标题行 + N−1 个「表头 / 值」行
- [ ] 效果：手机竖屏下每行只有两列，不折行；分组标题提供视觉分段

### 图表 → 委托 fdiagram skill
- [ ] 架构图/流程图等由 fdiagram 生成，通过 `block_insert_after` 嵌入
- [ ] 图表在对应内容位置嵌入，不在末尾堆砌

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

## 4. 写后验证（必做）

- [ ] fetch 验证：`lark-cli docs +fetch --api-version v2 --doc "{token}" --detail full`
  - `ok: true` **不代表生效**，必须 re-fetch
  - 用 `--detail full`（不用 `keyword`/默认，会隐藏 colgroup 和 block 属性）
- [ ] 表格验证：检查 `<colgroup>` 列宽之和 = 822
- [ ] 嵌入资源验证：grep `<whiteboard token=` 数量是否与编辑前一致
- [ ] 标题验证：grep `^#` 检查无手动编号（`一、` `1.1` 等前缀）

## 5. 输出规范

- [ ] 回复中输出：使用的飞书账号 + 文档链接（`my.feishu.cn` 域名）
- [ ] 追加到 ffeishu SKILL.md 底部「线上文档索引」表格

---

> **研究类报告额外约束** → `../fworch-report/SKILL.md`（全局加载）
> **lark-cli 命令完整速查** → `rules/feishu-cli-cheatsheet.md`
> **增量更新详细工作流** → `references/update-workflow.md`
