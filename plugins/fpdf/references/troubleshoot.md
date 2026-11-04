# fpdf 与 ffeishu 的边界、常见故障

## 返工（用户说"效果不对"时）

**不要重跑解析**（烧 MinerU 额度），直接按症状改渲染层：

```bash
cd ~/pdf-work/<slug>          # 结构包所在目录
# 只重渲染（原文 + 译文），改 render.py 后立刻见效
python3 ~/.claude/skills/fpdf/scripts/render.py <slug> --workdir . \
  --title "标题" --keep-refs --out o.xml
python3 ~/.claude/skills/fpdf/scripts/render.py <slug> --workdir . \
  --title "标题（译文）" --translate-map <slug>.trans.json --keep-refs --out z.xml
# 覆盖已有文档（不新建、不产生重名副本）
lark-cli docs +update --doc <doc_token> --as user --command overwrite \
  --doc-format xml --content "@./o.xml"
```

**改译文用 `<slug>.trans.json` 查表替换**，不重烧 token（除非要加译新段落）。
**只有解析层的问题**（内容缺失/结构错）才重跑 `parse.py`。

## 与 ffeishu 的关系（解耦）

fpdf **不依赖** ffeishu 的运行时，只在两处复用其成果：

1. **父文档回落**：fpdf.yaml 未配 `wiki_nodes.default` 时读 ffeishu.yaml 的同名字段
2. **格式规范**：排版遵循 ffeishu 的格式约定（标题层级、表格列宽 822、无手动编号）

反之，ffeishu 遇到 PDF 输入时**委托 fpdf**（见 ffeishu SKILL.md 的 `PDF 处理` 路由），
不再自己用 MCP/外部工具临时对付。

## 常见故障

| 症状 | 原因 | 处理 |
|------|------|------|
| `content_list 为空` | 跑了 Flash 档 | 确认 MinerU token 已配，重跑（默认 Precision） |
| `Parent node not found` | 父文档 token 无效/无权限 | 检查 `fpdf.yaml` 的 `default`，或显式 `--parent` |
| `unsafe output path` | lark-cli 导出路径沙箱 | 已内置：先导 /tmp 再 move（勿绕过） |
| 图片 0 字节 | MinerU SDK 的 `images` 是 dataclass 非 bytes | 已修（取 `.data`）；见 memory `mineru-sdk-image-write-bug-20261018` |
| **图糊/被切成多块** | MinerU 把一张 figure 切碎成低清截图 | 已修：抽 PDF 原图 + `page_ok` 合并（见「图片」节） |
| **公式裸露成 `$...$`** | 用了 v1 content_list（无公式条目） | 已修：render 默认读 v2；确认 `*.content_list_v2.json` 存在 |
| **`<sup>` 裸露成字面量** | `esc()` 把角标转义了 | 已修：角标转 `<latex>^{}`（含图注误判还原） |
| **文献被强加 "1."** | 一律用 `<ol>` | 已修：源无编号的用 `<ul>`（见「参考文献」节） |
| **文档出现重名副本** | 用了 `docs +create` 而非 `+update` | 改文档一律 `docs +update --command overwrite`；副本用 `drive +delete` 清 |
| 想重新排版 | 结构包已存在 | 直接调 `render.py`，不必重新解析 |