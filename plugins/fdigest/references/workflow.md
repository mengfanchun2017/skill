# fdigest 手工参考

> ⚠️ 流水线已由 `wf-fdigest` workflow 自动执行：`Workflow({name:"wf-fdigest", args:{slug:"..."}})`
> 本文件只记录 workflow 不覆盖的步骤和异常处理。常规操作走 workflow 即可。

## workflow 不做的（留在主上下文）

- 抓取源文件（判断 URL 可信度）
- 写分节详解（判断什么值得说）
- 决定传哪个父节点、删哪些旧节点
- 上传到飞书（不可逆操作）

## 手工回退（workflow 崩了再参考）

**Step 1 抓取：**
```bash
curl -s -A "Mozilla/5.0 (research your@email)" -o ~/digest-work/src/<slug>.htm "<URL>"
```
源文件落 `~/digest-work/src/`，不落 `~/git/`。

**Step 2 结构化抽取：**
```bash
python3 ~/.claude/skills/fdigest/scripts/extract.py <源文件> --workdir ~/digest-work --slug <slug> --source-url "<原始URL>"
```
产出 → `~/digest-work/<slug>/`:{pages,heads,tables,images}.json + text.txt + manifest.json

混合态判断：manifest 的 `full_page_scans` 多但 `tables` 也有 → 正文在文本层、案例在图里。文本层直抽，扫描页走 OCR。

**零文本层扫描页 → 先试 MinerU（三部曲）：**
```bash
python3 ~/.claude/skills/fdigest/scripts/ocr_cases.py <slug> <压缩后图片目录> /tmp/cases_ocr.json
setsid nohup python3 ~/.claude/skills/fdigest/scripts/translate_cases.py /tmp/cases_ocr.json /tmp/cases_ocr_zh.json 8 > /tmp/tc.log 2>&1 &
python3 ~/.claude/skills/fdigest/scripts/build_cases.py <slug> --images-dir <压缩后图片目录> --ocr /tmp/cases_ocr.json --ocr-zh /tmp/cases_ocr_zh.json --out /tmp/cases.xml
```
⚠️ MinerU 预签名 PUT 必须发空 Content-Type（`headers={'Content-Type': ''}`），否则 403。

**案例版式由 `build_cases.py` 固定，别在飞书里手改**。每页顺序：
原图 → 蓝色高亮块（案例名居中加粗 + 成果无序列表，**不用表格**）
→ 引用块（引文 + 署名同行内，署名 `<p align="right">`）→ 背景/影响 H3。
生成时自动跑 `layout_check()` 断言这三条，输出里 `layout.errors` 非空即违规。
来由与反例 → `ops.md §案例文档版式`。
⚠️ `align` 只在 fetch `--detail full` 可见；默认 `simple` 会丢，用它验证会误判成没生效。

**Step 3 索引（workflow 自带，手工补跑）：**
```bash
python3 ~/.claude/skills/fdigest/scripts/index.py <slug> --meta '{"title":"...","subject":"...","doc_kind":"...","disclosed_at":"...","feishu_url":"..."}'
```

**Step 4 详解 → 检索定位不整篇进上下文：**
```bash
python3 ~/.claude/skills/fdigest/scripts/search.py "关键词" --limit 5
```

**Step 5 翻译+排版（workflow 自动）：**
```bash
LLM_MAX_INFLIGHT=8 python3 ~/.claude/skills/fdigest/scripts/translate_blocks.py <slug> --workers 12
python3 ~/.claude/skills/fdigest/scripts/build_zh.py <slug> --title "…中文版" --images-dir images-web --split-cost 4500
```

**Step 6 归档到飞书：**
```bash
cd ~/files/fdigest
lark-cli docs +create --api-version v2 --title "<父文档名>中文版" --parent-token <wiki_node_token> --as user
for i in 01 02 03 04 05; do
  lark-cli docs +update --api-version v2 --doc <doc_token> --as user --command append --doc-format xml --content @./work/part$i.xml
done
```
子文档 parent-token 必须是 wiki node token，不是 docx token。HTML 来源不转 PDF。

## 关键约束

| 约束 | 原因 |
|---|---|
| `~/digest-work/` 存全部中间产物 | 落 `~/git/` 会被 auto-sync 推上公开库 |
| lark-cli allowlist: cwd / `/tmp` / `~/files` | 放别处静默失败 |
| 中文 FTS5 必须 trigram | unicode61 对中文不分词，命中恒 0；trigram 最少 3 字，2 字中文用 LIKE 兜底 |
| 块数上限 5000 是单次请求，非文档总量 | 多次 append 可累积到 17,563 块 |
| 飞书格式：H1 蓝字无底色、无 `<hr/>`、无手动编号、colgroup 和=822 | 否则格式校验不通过 |
| HTML 有文本层就直抽，不丢 OCR | OCR 贵 100 倍 |
| 翻译按需 | 415 页约 25 分钟 |
