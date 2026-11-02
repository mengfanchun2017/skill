---
name: fdigest
user-invocable: true
description: |
  大宗报告阅读与归档 — 处理大量报告/披露/统计文件（PDF/HTML），降低阅读负载：
  结构化抽取 → 段落级检索 → 分节详解 → 归档到飞书（父文档 + 子文档包）。
  已归档内容的横向背景（公司档案/赛道/财务基准）走主题档案层，跨报告复用不复制。
  用法：用户说"读这份报告"/"资料归档"/"披露文件分析"/"降低阅读负载"、
  给出 SEC/年报/研报链接或 PDF 说"帮我总结归档"、
  或问"我之前存的那份报告里说了什么"（= /fdigest search）触发。
  与 fpdf 分工：fpdf 是单篇精排上飞书，本 skill 是批量消化出结论。
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, mcp__mineru__parse_documents, mcp__tavily__tavily_search, mcp__tavily__tavily_extract
---

# fdigest — 大宗报告阅读与归档

## 定位

解决「大量报告读不完」的问题。核心思路不是存结论也不是存全文，而是**存可定位的事实层**：每条论断带文件、页码、章节坐标，结论从事实层投影，事实在就能重算。

与相邻 skill 的分工：

- **fpdf**：单篇 PDF 精排成飞书文档（还原版式、表格列宽、公式、图片）。要的是「排版好看」。
- **fworch-report**：从素材产出结构化报告。要的是「写出来」。
- **fresearchframe**：外部网络信息调研。要的是「网上找」。
- **fdigest**（本 skill）：一堆文件读出结论、能反查原文。要的是「读得少、找得到」。

## 飞书落点

| 层 | 节点 |
|---|---|
| 根节点 digestlib（bitable） | `GQktwgQRaiVMtpkwJvacmH6gn4f` / base `FJb6bh2XkamxbEsEki6ceXBinEI` |
| 报告档案表 | table `报告档案` |
| 阅读说明与索引 | wiki `TYwcwsj0siT7Q8kQoNxcsku1n3E` |
| 主题档案（横向复用） | wiki `OsXQwe8QBiFoe5kL5ywcpKGxnfb` |
| 报告归档（按份存） | wiki `MQb1wnB3fiCbKykZSoFczvErncd` |

真实 token 属于私有配置，不放公开仓库；运行时从 `ccprivate/conf/fdigest.yaml` 读，缺失时用 `lark-cli drive +search --query digestlib` 现查。

## 能力边界

**做什么**：大宗文件（SEC 文件、年报、研报、白皮书）的结构化抽取、段落级检索、
分节详解、全文中文化、飞书三层归档。

**不做什么**：不做论文精排（那是 fpdf，复杂公式/双栏/原图提取）；不做报告撰写
（那是 fworch）；不做外部调研（那是 fresearchframe）；**不自己实现翻译**——
LLM 调用统一走 `scripts/llm.py`（与 fpdf 同源），本 skill 只决定「翻什么粒度」。

**对华限制分析**：写公司档案时必须单列「对中国的限制与不友好」一节，区分
(a) 招股书原文直接披露（可复核、标页码）与 (b) 外部可查证的公开政策事实。
两者不混用、不互相背书。

## 三层结构

```
主题档案层（横向，跨报告复用，增量更新）
  公司档案 / 赛道与财务基准
        ↑ 报告里链接，不复制

报告归档层（纵向，一份报告一套）
  YYYY-MM-DD 类型 主体 文档种类详解        ← 父文档：Falcon 视角分节详解
    ├── 中文全文 · 章节（pN-M）             ← 按章节分卷，扁平挂，不套中间层
    ├── 来源与原文索引
    ├── 关键图表
    └── 原档 PDF                            ← SEC 只给 HTML 时本地转排生成

检索索引层（本地，派生物）
  ~/digest-work/index.db  SQLite FTS5
    ├── chunks     英文段落（unicode61，按词）
    └── zh_chunks  中文段落（trigram，按字符子串）
```

**为什么要主题档案层**：公司说明、赛道分析、财务基准不是某一份报告的内容，是横向背景。做完一份 Anthropic 报告存一份公司说明，下一份再存一份，就会各自分叉各自过期。拆成独立档案层后，读得越多档案越厚，是复利。

**为什么索引是本地的**：飞书 Base 搜不了段落，飞书文档搜索只能命中文档级。索引是派生物，丢了可从飞书 fetch 重建，不违反「内容存飞书」。

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

**混合态文件的关键判断**：先看 `manifest.json` 的 `full_page_scans` 与 `tables` 数量。若扫描页多但表格也有内容，说明正文在文本层、案例在图里——文本层直抽，扫描页单独走 vision，不无脑 OCR。

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

### Step 5：翻译（可选，按需）

**翻译不是本 skill 的能力，是复用的公共层。** LLM 预设解析与协议调用统一走
`scripts/llm.py`（与 fpdf 同源），本 skill 只负责「翻什么」。

```bash
# 块级翻译（推荐）：按还原后的结构块翻，段落/标题不断裂
python3 ~/.claude/skills/fdigest/scripts/translate_blocks.py <slug> --workers 12

# 拼装为飞书文档（长文按页区间分卷）
python3 ~/.claude/skills/fdigest/scripts/build_zh.py <slug> \
  --title "章节名" --page-start 41 --page-end 143 --out ~/files/fdigest/vol-41.xml
```

- 译文缓存 `zh-blocks/NNNN.json`，按页可续跑
- 表格保持「表格→行→单元格」三层，拍平会让每行变成独立表格（实测踩过）
- **长文档必须分卷**：4,000 块以上飞书 API 会超时（实测 1.4MB XML 直接 timeout），按章节切 5 卷各 350-1,100 块

`translate.py`（逐行）+ `render_zh.py` 是早期实现，**逐行译文拼回段落会断裂**，仅保留给需要逐行对照的场景。

### Step 6：归档到飞书

父文档挂到「报告归档」节点下，得到 wiki node token 后再建子文档（**子文档的 parent-token 必须是父文档的 wiki node token，不是 docx token**）。

## 关键约束

### 硬约束

- **源文件、索引库、中间产物全部落 `~/digest-work/`**，绝不落 `~/git/` 任何仓库
- **lark-cli 的 `--content @file` 有路径 allowlist**（cwd / `/tmp` / `~/files`）。放别处 → 静默失败。统一用 `~/files/fdigest/` 中转
- **子文档 parent-token 用 wiki node token**，用 docx obj_token 会报 `Parent node not found`（3380002）
- **飞书文档格式**：H1 蓝字无底色、H2 及以下默认黑、无 `<hr/>`、无手动编号、colgroup 宽度和 = 822、正文不撒黑体、≥4 列表格转两列竖排

### 检索层注意

- 中文 FTS5 必须用 `tokenize='trigram'`，`unicode61` 对中文不分词，命中恒为 0
- trigram 最少 3 字符，2 字中文查不到 → search.py 有 LIKE 兜底
- 英文用 `unicode61` 按词切，多词查询走 OR 展开

### 成本控制

- **HTML 有文本层就直抽，不丢给 OCR**：文本层免费，OCR 贵 100 倍
- **只对整页扫描图做 vision**，且只做需要引用的页
- **翻译按需**：415 页全文翻译约 25 分钟，不是每份都必须做

## 脚本清单

| 脚本 | 职责 | 输入 → 输出 |
|---|---|---|
| `extract.py` | 结构化抽取 | 源文件 → pages/heads/tables/images/text + manifest |
| `index.py` | 建段落级索引 | 结构包 → SQLite FTS5 |
| `search.py` | 中英文检索 | 查询 → 页码 + 章节 + 片段 + 飞书链接 |
| `llm.py` | **公共 LLM 层**（与 fpdf 共用） | 预设 + 协议自适应调用 |
| `build_zh.py` | 版面结构还原 | 结构包 → 带标题层级/段落/表格的 DocxXML |
| `translate_blocks.py` | 块级翻译（推荐） | 结构包 → zh-blocks/NNNN.json |
| `translate.py` | 逐行翻译（旧） | 结构包 → 逐页逐行 JSON |
| `render_zh.py` | 逐行译文拼装（旧） | 逐行 JSON → DocxXML |
| `parents_tpl.xml` 等 | 文档模板 | 占位符 → 可上传 XML |

## 与 fpdf 的关系

不重复实现 PDF 解析。**PDF 输入先走 fpdf 的 `scripts/parse.py` 拿结构包**（MinerU Precision 档），再复用本 skill 的 index/search。

```bash
# PDF → 结构包（fpdf 负责）
bash ~/.claude/skills/fpdf/scripts/run.sh --parse-only <pdf>
# 结构包 → 索引（本 skill 负责）
python3 ~/.claude/skills/fdigest/scripts/index.py <slug>
```

HTML（SEC 披露、网页年报）走本 skill 的 extract.py；PDF 走 fpdf。两者产出的结构包格式需要对齐，见 index.py 的 `pages.json` 读取逻辑。

## 常见故障

| 现象 | 根因 | 修法 |
|---|---|---|
| `--content @file` 静默失败 | 文件不在 allowlist（cwd/`/tmp`/`~/files`） | 复制到 `~/files/fdigest/` 再传 |
| 子文档报 `Parent node not found` | parent-token 用了 docx obj_token | 用 `wiki +node-list --parent-node-token` 查真正 node_token |
| 中文检索恒 0 命中 | tokenizer 用了 unicode61 | 重建索引为 trigram |
| 翻译报 `Invalid URL (POST /v1/v1/messages)` | base_url 已带 `/v1`，又拼了一层 | translate.py 已按 base_url 结尾自适应协议 |
| 翻译空内容 | 内网网关已知故障 | translate.py 重试 + 重跑补缺页 |
| 建表报 `validation_error` | 表名重复（同名表已存在） | 先改名或删旧表 |
| 删除字段报 `unsafe_operation_blocked` | 不能删表里唯一字段 | 新建正确表后删旧表 |
| 表格列宽全变 120 | 用了废弃的 `<lark-table>` 语法 | 改标准 `<table>` + `<colgroup>`，宽度和 822 |

## 变更摘要

| 文件 | 变更 |
|---|---|
| `SKILL.md` | 新增 — 定位、三层结构、六步工作流、约束与故障表 |
| `scripts/extract.py` | 新增 — HTML 结构化抽取（逐页行 + 字号 + 加粗 + 表格 + 图片扫描页标记） |
| `scripts/index.py` | 新增 — SQLite FTS5 段落索引，带章节路径 |
| `scripts/search.py` | 新增 — 中英双语检索，中文 trigram + LIKE 兜底 |
| `scripts/translate.py` | 新增 — 并行分段翻译，按页缓存可续跑，协议自适应 |
| `scripts/render_zh.py` | 新增 — 译文拼装 DocxXML，自动分卷 |
| `scripts/parent_tpl.xml` | 新增 — 报告父文档模板 |
| `scripts/child_source_tpl.xml` | 新增 — 来源索引子文档模板 |
| `scripts/child_figures_tpl.xml` | 新增 — 关键图表子文档模板 |
| `scripts/topic_company_tpl.xml` | 新增 — 公司档案模板 |
| `scripts/topic_market_tpl.xml` | 新增 — 赛道档案模板 |
| `scripts/topic_finance_tpl.xml` | 新增 — 财务基准模板 |
