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

解决「大量报告读不完」。核心不是存结论也不是存全文，而是**存可定位的事实层**：
每条论断带文件、页码、章节坐标，结论从事实层投影，事实在就能重算。

| 相邻 skill | 它要什么 | 本 skill 要什么 |
|---|---|---|
| fpdf | 单篇 PDF 精排上飞书 | — |
| fworch-report | 从素材写出结构化报告 | — |
| fresearchframe | 网上找外部信息 | — |
| **fdigest** | — | **读得少、找得到** |

## 三层结构

```
主题档案层（横向，跨报告复用）
  公司档案 / 赛道与财务基准
        ↑ 报告里链接，不复制

报告归档层（纵向，一份报告一套）
  YYYYMMDD 类型 主体 详情          ← 父文档（分节详解）
    ├── …中文版                    ← 全文一篇，真图嵌入
    ├── 来源、图表与原文索引        ← 出处 + 页码定位 + 真实图表
    └── 原档 PDF                   ← 仅 PDF 来源

检索索引层（本地派生物）
  ~/digest-work/index.db  SQLite FTS5
    ├── chunks     英文（unicode61，按词）
    └── zh_chunks  中文（trigram，按字符子串）
```

**为什么主题档案独立**：公司说明、赛道分析、财务基准是横向背景，不是某份报告的内容。
每份报告各存一份会各自分叉、各自过期；独立后读得越多档案越厚，是复利。

**为什么索引在本地**：飞书 Base 搜不了段落，飞书文档搜索只能命中文档级。
索引是派生物，丢了可从飞书 fetch 重建，不违反「内容存飞书」。

**命名**：日期一律 `YYYYMMDD` 无分隔符。中文全文就叫「`<父文档名>中文版`」，不分卷。
完整命名规则与归档形态 → `references/ops.md`。

## 工作流

```
源文件 → 抓取 → extract.py 结构化 → index.py 建索引
                ↓
           写父文档（详解）→ 建子文档（翻译/来源/图表）
                ↓
           主题档案增量更新 → Base 登记
```

每步的命令、产出物、判据 → `references/workflow.md`。要点：

- **源文件落 `~/digest-work/`，绝不落 `~/git/`** —— auto-sync 会秒推进公开库，版权材料直接泄漏
- **检索定位，不整篇进上下文**：`search.py "关键词" --limit 5`
- **块数上限是单次请求不是文档总量**：同一文档多次 append 累积到 17,563 块实测成功
- **HTML 有文本层就直抽，不丢给 OCR**（文本层免费，OCR 贵 100 倍）

## 关键约束

| 约束 | 原因 |
|---|---|
| 全部中间产物落 `~/digest-work/` | 落 `~/git/` 会被 auto-sync 推上公开库 |
| lark-cli 路径参数用 `~/files/fdigest/` | `--content @file`/`<img path=>` 有 allowlist，放别处静默失败 |
| 子文档 parent-token 用 **wiki node token** | 用 docx obj_token 报 `Parent node not found` 3380002 |
| 中文 FTS5 必须 `trigram` | `unicode61` 对中文不分词，命中恒 0 |
| 图片压缩后再上传 | 实测 142MB → 10MB |
| 翻译按需 | 415 页全文约 25 分钟，不是每份都要做 |

完整约束与成本控制 → `references/constraints.md`。

## 什么时候走 workflow

`fdigest-build` 承担确定性重活：预检 → 索引 → 翻译 → 排版 → 格式断言，跑完**停在交付前**。

```bash
Workflow({name: "fdigest-build", args: "<slug>"})
```

**为什么拆出去**：首战 S-1 实测 445 次 Bash 里只有 18% 走到脚本，49% 是现场手写 python
和格式返工 —— 那些环节没有判断空间，该由代码编排。

**为什么停在交付前**：详解要论断可复核，上传删除不可逆，这两件必须人看。

留在主上下文的：抓取源文件（判断 URL 可信度）、写分节详解（判断什么值得说）、
决定传哪个父节点、删哪些旧节点。

## 飞书落点与配置

| 层 | 配置键 |
|---|---|
| 根节点 digestlib（bitable） | `digestlib_wiki_node` / `digestlib_base` |
| 报告档案表 | `table_archive` |
| 阅读说明与索引 | `index_wiki_node` |
| 主题档案（横向复用） | `topic_wiki_node` |
| 报告归档（按份存） | `archive_wiki_node` |

真实 token 不进公开仓库：

```bash
~/.claude/skills/fcore/bin/fcore --plugin fdigest conf path digestlib_wiki_node
~/.claude/skills/fcore/bin/fcore --plugin fdigest conf require digestlib_wiki_node
```

**未配置时不阻断**：只做本地抽取/索引/检索，跳过飞书归档，并按 `conf require` 的
提示让用户填到 `~/.claude/skill-config/fdigest.yaml`（`/plugin update` 不覆盖）。

## 脚本清单

| 脚本 | 职责 |
|---|---|
| `extract.py` | 结构化抽取 → pages/heads/tables/images/text + manifest |
| `index.py` | 建段落级索引 → SQLite FTS5 |
| `search.py` | 中英文检索 → 页码 + 章节 + 片段 + 飞书链接 |
| `llm.py` | **公共 LLM 层**（与 fpdf / transliter 共用）：预设+协议自适应+flock 并发闸+429 退避 |
| `prepare_images.py` | 下载 + 压缩原文图片 |
| `build_zh.py` | 版面还原 + 嵌图 + 按块数切段 |
| `translate_blocks.py` | 块级翻译（推荐） |
| `translate.py` / `render_zh.py` | 逐行翻译（旧，拼回段落会断裂） |

## 常见故障

→ `references/ops.md`（含与 fpdf 的边界、故障排查表、归档命名定案）。
