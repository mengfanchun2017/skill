# fdigest 六步工作流（完整步骤与命令）

> SKILL.md 只留流程总览；本文件是每步的命令、产出物、判据。
> 命令走 `fcore`，`lark-cli` 直接调用仅在脚本内部。

## 工作流

### 流程总览

```
源文件 → 抓取 → extract.py 结构化 → index.py 建索引
                ↓
           写父文档（详解）→ 建子文档（翻译/来源/图表）
                ↓
           主题档案增量更新（如有新信息）
                ↓
           Base 登记记录
```

### Step 1：抓取源文件

```bash
# SEC 文件必须带 User-Agent，否则 403
curl -s -A "Mozilla/5.0 (research your@email)" -o ~/digest-work/src/<slug>.htm "<URL>"
```

源文件必须落 `~/digest-work/src/`，**绝不落 `~/git/`**（auto-sync 会秒推进公开库，版权材料直接泄漏）。

### Step 2：结构化抽取

```bash
python3 ~/.claude/skills/fdigest/scripts/extract.py <源文件> \
  --workdir ~/digest-work --slug <slug> --source-url "<原始URL>"
```

产出（`~/digest-work/<slug>/`）：

- `pages.json` 逐页行结构，每行带字号和加粗标记
- `heads.json` 章节标题与页码
- `tables.json` 表格行列
- `images.json` 图片清单，标记整页扫描图
- `text.txt` 全文本
- `manifest.json` 元数据与源哈希

**混合态文件的关键判断**：先看 `manifest.json` 的 `full_page_scans` 与 `tables` 数量。若扫描页多但表格也有内容，说明正文在文本层、案例在图里——文本层直抽，扫描页单独走 OCR，不无脑全量 OCR。

**零文本层的扫描页 → 先试 MinerU，不要停成「等人工」**。MinerU 收图片输入
（png/jpg/webp/gif/bmp/tiff/jp2），输出带版面结构的 markdown（标题层级/表格/段落），
比通用 vision 模型"描述这张图"更贴近文档本身的结构。三步：

```bash
# 1. OCR — 配置在 ~/.claude/skill-config/mineru.json（api_base + token），token 不进公开库
python3 ~/.claude/skills/fdigest/scripts/ocr_cases.py <slug> <压缩后图片目录> /tmp/cases_ocr.json

# 2. 译中文 — 按页分片落盘可续跑；必须 setsid 脱离会话，否则 session 挂掉整轮白跑
setsid nohup python3 ~/.claude/skills/fdigest/scripts/translate_cases.py \
  /tmp/cases_ocr.json /tmp/cases_ocr_zh.json 8 > /tmp/tc.log 2>&1 &

# 3. 排版 — 每节：原图 → 中文译文（需核对英文就看原图）
python3 ~/.claude/skills/fdigest/scripts/build_cases.py <slug> \
  --images-dir <压缩后图片目录> \
  --ocr /tmp/cases_ocr.json --ocr-zh /tmp/cases_ocr_zh.json --out /tmp/cases.xml
```

⚠️ **MinerU 预签名 PUT 必须发空 Content-Type**（`headers={'Content-Type': ''}`）。
URL 用空串签名，客户端带任何值都 403 `SignatureDoesNotMatch`（MinerU issue #5393）。

**零文本层的扫描页 → 先试 MinerU，不要停成「等人工」**。MinerU 收图片输入
（png/jpg/webp/gif/bmp/tiff/jp2），输出带版面结构的 markdown（标题层级/表格/段落），
比通用 vision 模型"描述这张图"更贴近文档本身结构。三步：

```bash
# 1. OCR（配置在 ~/.claude/skill-config/mineru.json：api_base + token）
python3 ~/.claude/skills/fdigest/scripts/ocr_cases.py <slug> <图片目录> /tmp/cases_ocr.json
# 2. 译中文（按页分片落盘，中断可续跑；必须 setsid 脱离会话）
setsid nohup python3 ~/.claude/skills/fdigest/scripts/translate_cases.py \
  /tmp/cases_ocr.json /tmp/cases_ocr_zh.json 8 > /tmp/tc.log 2>&1 &
# 3. 排版：图 → 中文 → （英文核对看原图）
python3 ~/.claude/skills/fdigest/scripts/build_cases.py <slug> \
  --images-dir <压缩后图片目录> --ocr /tmp/cases_ocr.json --ocr-zh /tmp/cases_ocr_zh.json --out /tmp/cases.xml
```

⚠️ MinerU 预签名 PUT 的 URL 用**空 Content-Type 签名**，客户端带任何 Content-Type
都 403 `SignatureDoesNotMatch` → `headers={'Content-Type': ''}`。

### Step 3：建索引

```bash
python3 ~/.claude/skills/fdigest/scripts/index.py <slug> --meta '{"title":"...","subject":"...","doc_kind":"...","disclosed_at":"...","feishu_url":"..."}'
```

### Step 4：读原文写详解

用检索定位关键内容，不整篇进上下文：

```bash
python3 ~/.claude/skills/fdigest/scripts/search.py "compute commitment" --limit 5
python3 ~/.claude/skills/fdigest/scripts/search.py "净收入留存" --limit 5
```

详解文档必须带页码回溯表，所有论断可复核。

### Step 5：翻译 + 排版（可选，按需）

**翻译不是本 skill 的能力，是复用的公共层。** LLM 预设解析、协议调用、并发治理
统一走 `scripts/llm.py`（与 fpdf / transliter 同源），本 skill 只负责「翻什么粒度」。

`llm.py` 里的并发治理是从 transliter 移植的（一份代码两处用）：
- `acquire_slot()` / `release_slot()` — flock 槽位池，**跨进程**在途上限。多份报告并行时
  不会各开一个线程池叠成 N 倍打爆端点
- `backoff()` — 尊重 `Retry-After`，否则指数退避加抖动。无脑 `sleep(1.5*n)` 在 429 下会拖死
- `FALLBACK_FAIL_RATIO` — 失败率超 5% 才判「模型不行」整批重做。单段失败就重烧整轮代价极高
- `RETRY_STATS` — 调并发唯一的依据就是 429 计数，以前只写 stderr 被 tail 掉

```bash
# 块级翻译（推荐）：按还原后的结构块翻，段落/标题不断裂
LLM_MAX_INFLIGHT=8 python3 ~/.claude/skills/fdigest/scripts/translate_blocks.py <slug> --workers 12

# 排版 + 嵌图 + 按飞书块数切段（一次产出全部段落）
python3 ~/.claude/skills/fdigest/scripts/build_zh.py <slug> \
  --title "…中文版" --images-dir images-web --split-cost 4500
# → <workdir>/zh-parts/part01.xml … part05.xml
```

- 译文缓存 `zh-blocks/NNNN.json`，按页可续跑
- 表格保持「表格→行→单元格」三层，拍平会让每行变成独立表格（实测踩过）
- **图片先压缩再嵌**：SEC 原图 142MB，缩到 1600px/quality85 后 10MB。不压直接传很慢
- **块数换算**（实测标定，不是标签数）：`1 + <p> + <h> + <table> + 2×<td> + 2×<li>`。
  单次 append 超 5,000 块被拒（`DOC_OPERATION_BLOCK_LIMIT`），按顶层块边界切段

`translate.py`（逐行）+ `render_zh.py` 是早期实现，**逐行译文拼回段落会断裂**，仅保留给需要逐行对照的场景。

### Step 6：归档到飞书

父文档挂到「报告归档」节点下，得到 wiki node token 后再建子文档（**子文档的 parent-token 必须是父文档的 wiki node token，不是 docx token**）。

**全文中文化**：建**一个**子文档，逐段 `--command append` 直到全部段落。

```bash
cd ~/files/fdigest   # lark-cli 的 allowlist 是 cwd / /tmp / ~/files
lark-cli docs +create --api-version v2 --title "<父文档名>中文版" --parent-token <wiki_node_token> --as user
for i in 01 02 03 04 05; do
  lark-cli docs +update --api-version v2 --doc <doc_token> --as user \
    --command append --doc-format xml --content @./work/part$i.xml
done
```

**不要 overwrite**：含 `<img>` / 白板 / 表格的文档禁 overwrite，只能 append 或 block_*。

**HTML 来源不转 PDF**：源文件本来就是 HTML/网页时，**不强行先生成 PDF 再纳管**，
在根文档（父文档）里写明「本报告原始提交为 HTML，无官方 PDF」即可。
只有 PDF 来源才附原档 PDF。

## 关键约束

### 硬约束

- **源文件、索引库、中间产物全部落 `~/digest-work/`**，绝不落 `~/git/` 任何仓库
- **lark-cli 的 `--content @file` / `<img path=>` 有路径 allowlist**（cwd / `/tmp` / `~/files`）。放别处 → 静默失败。统一用 `~/files/fdigest/` 中转
- **子文档 parent-token 用 wiki node token**，用 docx obj_token 会报 `Parent node not found`（3380002）
- **飞书文档格式**：H1 蓝字无底色、H2 及以下默认黑、无 `<hr/>`、无手动编号、colgroup 宽度和 = 822、正文不撒黑体、≥4 列表格转两列竖排
- **块数上限是「单次请求」不是「文档总量」**：`DOC_OPERATION_BLOCK_LIMIT` 报的 `actual` 是这一次 append 的块数，上限 5,000。同一文档多次 append 累积到 17,563 块实测成功

### 检索层注意

- 中文 FTS5 必须用 `tokenize='trigram'`，`unicode61` 对中文不分词，命中恒为 0
- trigram 最少 3 字符，2 字中文查不到 → search.py 有 LIKE 兜底
- 英文用 `unicode61` 按词切，多词查询走 OR 展开

### 成本控制

- **HTML 有文本层就直抽，不丢给 OCR**：文本层免费，OCR 贵 100 倍
- **只对整页扫描图做 vision**，且只做需要引用的页
- **翻译按需**：415 页全文翻译约 25 分钟，不是每份都必须做
- **图片压缩后再上传**：`thumbnail((1600,1600), LANCZOS)` + `quality=85`，实测 142MB→10MB

## 什么时候走 workflow（fdigest-build）