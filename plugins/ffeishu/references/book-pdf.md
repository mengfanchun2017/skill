# 飞书文档树 → 合订本 PDF（反向导出）

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