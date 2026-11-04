# ffeishu 文档工作流细则

> SKILL.md 只留决策树与主路径；本文件是各工作流的完整步骤与命令。
> 格式硬约束仍以 `write-checklist.md` 为准。

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
- `grep '<colgroup'` → 列宽之和 = 822（**默认 `simple` 会丢 width，别用它验）**
- `grep '^#'` → 无 `一、` `1.1` `(1)` 等手动编号前缀
- 白板/嵌入资源数量与预期一致

创建后追加到「线上文档索引」表格。

### 超长文档（>5,000 块）

单次写请求上限 5,000 块，但**同一文档可多次追加累积到上万块**。
块数换算：`1 + <p> + <h> + <table> + 2×<td> + 2×<li>`（表格单元格算 2 块）。

```bash
# 按顶层块边界切段，逐段 append 到同一文档
lark-cli docs +create --api-version v2 --title "…" --parent-token <parent> --as user
for i in 01 02 03 04 05; do
  lark-cli docs +update --api-version v2 --doc <doc> --as user \
    --command append --doc-format xml --content @./part$i.xml
done
```

报 `DOC_OPERATION_BLOCK_LIMIT actual:8313 limit:5000` 时，`actual` 是**这一段**的块数，切细即可。

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
- 🚨 **`block_replace --block-id -1` 会截断文档**：`-1` 表示「到文档末尾」，会把后面的内容全部替换掉。
  2026-11-03 实测用它改标题，19.5KB 正文只剩 6.2KB

### 改文档标题（唯一可行路径）

```bash
# 本地有完整 XML → 改 <title> 后整篇 overwrite。文档标题与 wiki 节点标题同步
lark-cli docs +update --api-version v2 --doc <doc_token> --as user \
  --command overwrite --doc-format xml --content @./doc_fixed.xml
```

- ❌ `block_replace --block-id -1`（截断风险）
- ❌ wiki `update_title` API（缺 `wiki:wiki wiki:node:update` scope，报 99991679）
- 改 `<title>` 同步 wiki 节点标题，不需要额外 scope

### 误操作恢复

```bash
lark-cli docs +history-list --doc <token> --as user --format json   # 取 history_version_id
lark-cli docs +history-revert --doc <token> --history-version-id <id> --as user
```

`+fetch --revision-id N` 不能预览历史版本（返回空），只能回滚后看。

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
