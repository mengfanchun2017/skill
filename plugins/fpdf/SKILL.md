---
name: fpdf
user-invocable: true
description: |
  PDF 精排 — 把 PDF 精确拆解后重排为飞书文档：还原表格列宽、行内公式、高清原图、
  参考文献、论文首页信息区，可选导出 Word、可选生成译文版，可安装/检查运行依赖。
  用法：用户说"PDF 排版"/"PDF 转飞书"/"处理这个 PDF"/"/fpdf <路径>"、
  给出 PDF 路径要求"放到飞书上"/"导出 Word"/"翻译 PDF"、
  说"排版不对"/"图不清楚"/"公式没渲染"/"文献编号不对"（返工重排）、
  或说"安装依赖"/"检查依赖"（= /fpdf deps）。
  依赖 MinerU 云端 API（解析）+ lark-cli（飞书）+ uv（运行器）。
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, mcp__mineru__parse_documents
---

# fpdf — PDF 精排到飞书

把 PDF 当成「结构化数据」而非「一段文字」：先精确拆出内容与版式（表格/图片/公式/
标题层级/分栏），再用飞书文档的排版能力重建，而不是把 PDF 当图片贴上去。

## 四个入口

| 用户说法 | 行为 |
|---------|------|
| `/fpdf <路径>` | 解析 → 飞书文档（**默认落飞书**） |
| `/fpdf word <路径>` | 解析 → 飞书文档 → 再导出 Word 到源文件同目录 |
| `/fpdf trans <路径>` | 解析 → 飞书**原文 + 译文**两份文档（默认中文） |
| `/fpdf deps` | **只装/查依赖**，不处理 PDF |

路径支持 Windows（`C:\...` / `C:/...`）与 WSL（`/mnt/c/...`），脚本自动转换。

## 执行

```bash
# 默认：只落飞书
bash ~/.claude/skills/fpdf/scripts/run.sh "<pdf路径>"

# 变体
bash ~/.claude/skills/fpdf/scripts/run.sh "<pdf路径>" --word     # 加 Word 导出
bash ~/.claude/skills/fpdf/scripts/run.sh "<pdf路径>" --trans    # 加译文版
bash ~/.claude/skills/fpdf/scripts/run.sh "<pdf路径>" --title "标题" --parent "<wiki节点token>"
```

`run.sh` 四阶段：解析（MinerU Precision）→ 渲染（DocxXML）→ 上传飞书 → 可选 Word 导出。
最后一行 stdout 是 JSON（`doc_url` / `trans_doc_url` / `word_path`），进度到 stderr。
`run.sh` 会自动调 `setup.sh` 补齐依赖，通常不必手动装。

**交付必须给完整链接**（markdown 格式，独占一行）：`[文档标题](https://<tenant>.feishu.cn/docx/<token>)`

## 依赖

| 依赖 | 装法 | 阻断 |
|---|---|---|
| `uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | 是 |
| `lark-cli` | `npm i -g @larksuite/cli` | 是 |
| 飞书授权 | `lark-cli auth login`（扫码） | 是 |
| MinerU token | mineru.net → API 管理 → 建 token，`fcore conf set mineru.token <token>` | 是（默认 precision 档） |
| `poppler-utils` | 自动按平台装；装不上只提示 | 否 |

`poppler` 不阻断因为主路径用 pymupdf，它只在需要 `pdftotext`/`pdfimages` 时用。

```bash
bash ~/.claude/skills/fpdf/scripts/setup.sh          # 检查 + 缺啥装啥
bash ~/.claude/skills/fpdf/scripts/setup.sh --check  # 只检查
~/.claude/skills/fcore/bin/fcore auth                # 飞书授权预检
```

**需你本人动手的**（无 TTY 时 `sudo` 会挂）：setup.sh 会按平台给出可复制的安装命令，
用 `! <该行命令>` 在本会话内跑。

## 关键约束

| 约束 | 说明 |
|---|---|
| 默认 **Precision 档** | Flash 免费但无 bbox 无图片，`content_list` 为空 → render 直接拒排 |
| render 默认用 **content_list v2** | v1 行内公式裸露成 `$...$` 纯文本；v2 才还原为 `<latex>`（实测 55 号 4 处、88 号 54 处） |
| 图片用 PDF 原图 | 不切碎 |
| 分栏 `--columns` **默认不用** | 只在原始 PDF 确实是双栏且版面还原失败时才开 |
| 译文文档独立 | 不改原文档 |

## 排版细则

父文档配置、解析档位对比、PDF 结构 → 飞书块映射、图片/参考文献/首页信息区、
翻译、返工流程 → `references/render.md`。

## 参考

| 文件 | 内容 |
|---|---|
| `references/pipeline.md` | 4 步执行流程、依赖检查 5 项、4 阶段详解 |
| `references/render.md` | 父文档配置、档位对比、排版能力映射、图片/文献/翻译/返工 |
| `references/troubleshoot.md` | 与 ffeishu 的边界、常见故障 |
| `scripts/run.sh` | 编排器（解析→渲染→上传） |
| `scripts/setup.sh` | 依赖检查与安装 |
