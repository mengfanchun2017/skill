---
name: fpdf
user-invocable: true
description: |
  PDF 精排 — 把 PDF 精确拆解后重排为飞书文档（复杂版式：全宽表格、分栏、引用、高亮块），
  可选导出 Word、可选生成译文版。
  用法：用户说"PDF 排版"/"PDF 转飞书"/"处理这个 PDF"/"/fpdf <路径>"、
  或给出 PDF 路径要求"放到飞书上"/"导出 Word"/"翻译 PDF"。
  依赖 MinerU（解析）+ lark-cli（飞书）+ uv（运行器）。
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, mcp__mineru__parse_documents
---

# fpdf — PDF 精排到飞书

把 PDF 当成「结构化数据」而非「一段文字」：先精确拆出内容与版式（表格/图片/公式/标题层级/分栏），
再用飞书文档的排版能力重建，而不是把 PDF 当图片贴上去。

## 三个入口（唯一真相源是本文件；脚本只做确定性机械步骤）

| 用户说法 | 行为 |
|---------|------|
| `/fpdf <路径>` | 解析 → 飞书文档（**默认落飞书**） |
| `/fpdf word <路径>` | 解析 → 飞书文档 → **再导出 Word 到源文件同目录** |
| `/fpdf trans <路径>` | 解析 → 飞书**原文文档 + 译文文档**（默认译成中文） |

路径支持 Windows 格式（`C:\...` / `C:/...`）和 WSL 格式（`/mnt/c/...`），脚本内部自动转换。

## 执行流程（4 步，全部走 `scripts/run.sh`）

### Step 0: 前置检查（自动，缺什么装什么）

**`run.sh` 会自动调 `setup.sh` 补齐**，通常不必手动跑。手动检查/安装时：

```bash
bash ~/.claude/skills/fpdf/scripts/setup.sh          # 检查 + 缺啥装啥（需 sudo 时提示）
bash ~/.claude/skills/fpdf/scripts/setup.sh --check  # 只检查不安装
```

检查 5 项：

| 依赖 | 缺失时 | 是否阻断 |
|------|--------|---------|
| `uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | **阻断** |
| `lark-cli` | `bash ~/git/ccconfig/init-option.sh larkcli` | **阻断** |
| 飞书授权 | 同上（走扫码，一次性） | **阻断** |
| MinerU token | `bash ~/git/ccconfig/init-option.sh mineru key` | 不阻断（仅 flash 档可跑） |
| `poppler-utils` | 自动 `sudo apt-get install -y poppler-utils`；无 sudo 权限时**只提示不阻断** | 不阻断 |

**为什么 poppler 不阻断**：解析/渲染主路径走 pymupdf（`parse.py` 内用），poppler 只在需要
`pdftotext`/`pdfimages`/`pdftoppm` 这类命令行快速抽取时用得上；装不上不影响主流程。
无 TTY 的自动会话里 `sudo` 会挂，故 setup.sh 先判 `sudo -n` 再决定装还是提示。

> **飞书授权口径**：唯一可信信号是 `lark-cli auth status` 的 `identities.user.available`。
> `config.json` 里的 `users[]` 是「登录过」的记录，token 过期仍残留 → 拿它判断会假阳性。

### Step 1-4: 跑编排器

```bash
# 默认：只落飞书
bash ~/.claude/skills/fpdf/scripts/run.sh "<pdf路径>"

# 加 Word 导出
bash ~/.claude/skills/fpdf/scripts/run.sh "<pdf路径>" --word

# 加译文版
bash ~/.claude/skills/fpdf/scripts/run.sh "<pdf路径>" --trans

# 指定标题 / 父文档 / 工作目录
bash ~/.claude/skills/fpdf/scripts/run.sh "<pdf路径>" \
  --title "文档标题" --parent "<wiki节点token>" --word
```

`run.sh` 四阶段：**解析**（MinerU Precision）→ **渲染**（DocxXML）→ **上传飞书** → **可选 Word 导出**。
最后一行 stdout 是 JSON（`doc_url` / `trans_doc_url` / `word_path`），其余进度到 stderr。

### Step 5: 向用户输出

**必须**给出完整飞书链接（markdown 格式，独占一行）：

```
[文档标题](https://<tenant>.feishu.cn/docx/<token>)
```

Word 导出路径、译文文档链接一并给出。多链接用列表。

## 父文档（所有输出落在此处）

父文档链接存在**私有配置** `ccprivate/skill/fpdf.yaml` 的 `wiki_nodes.default`
（未配置时回落 ffeishu.yaml 的 default）。用户说"保存父文档链接"或"配置 fpdf"时：
用 AskUserQuestion 问父文档 URL/token → 写入该 yaml：

```yaml
wiki_nodes:
  default: "<wiki节点token>   # 从父文档 URL 的 /wiki/<token> 取
doc_index: []                  # 自动追加，勿手改
```

`--parent` 参数可临时覆盖。

## 解析档位（决定能不能排版）

| 档位 | 返回 | 用途 |
|------|------|------|
| **Flash**（免费，无 token） | 只有 markdown 纯文本，**无坐标无图片** | 只要文字时降级用 |
| **Precision**（token） | markdown + `content_list`（每条带 bbox 坐标 + 表格 HTML + 图片） + 图片 | **默认**，排版必需 |

`/fpdf` 默认走 Precision —— 没有 bbox 就无法还原分栏、表格结构。
Flash 档解析出的包 `content_list` 为空，render 会直接报错拒绝排版。

## 排版能力映射（PDF 结构 → 飞书块）

写飞书 DocxXML 时用这些标签（**均已实测**）：

| PDF 内容 | 飞书 XML | 说明 |
|---------|---------|------|
| 表格 | `<table><colgroup><col width="N"/></colgroup><thead><tr><th>` | **列宽之和 = 822**；见下方警告 |
| 分栏 | `<grid><column width-ratio="0.5">…</column>…</grid>` | 各列 ratio 之和 = 1 |
| 强调块 | `<callout emoji="💡" background-color="light-blue">` | 子块仅 `p/ol/ul/checkbox` + 行内标签 |
| 引用 | `<blockquote><p>…</p></blockquote>` | |
| 图片 | `<img path="@./images/xxx.jpg" caption="…"/>` | 路径**相对 CLI 工作目录** |
| 公式 | `<p align="center"><code>LaTeX</code></p>` | 飞书无原生公式块，降级为代码 |

### ⚠ 表格语法警告（重要）

**唯一保留列宽和多行的写法**是标准 HTML 结构：

```
✅ <table><colgroup><col width="411"/><col width="411"/></colgroup>
   <thead><tr><th background-color="light-gray"><p>表头</p></th></tr></thead>
   <tbody><tr><td><p>值</p></td></tr></tbody></table>
```

> ffeishu SKILL.md 旧文档里的 `<lark-table rows="N" cols="N" column-widths="...">` **实测无效**：
> 列宽被丢弃（全变 120）、第二行 `<lark-tr>` 被吞。`render.py` 已按正确语法生成，
> 手写 XML 时勿回退到 lark-table。

`render.py` 已把 MinerU 的 `table_body`（`<table><tr><td>`）规范化为上述结构并自动均分 822 列宽。

## 分栏策略（默认不还原左右并排）

论文类双栏 PDF 的「左右两栏」是**印刷版式**，在移动端优先的飞书文档里左右并排会挤成一团。
因此 `render.py` **默认 `--columns flow`**：按原阅读顺序展开为单栏流，保留全部内容与层级。

确需左右对照时加 `--columns grid`：按 bbox 把每页条目分左右栏输出 `<grid>`。

## 翻译（--trans）

译文的 LLM 后端**复用 Claude 当前生效的模型**（读 `~/.cache/llm-merged.json` 的 `current`），
零配置。协议走 **Anthropic Messages**（实测本机 bridge 8898 只暴露 `/v1/messages`，
`/v1/chat/completions` 返回 404）。

- 默认译成中文；改目标语言用 `FPDF_TRANS_TARGET=en`
- 译文落 `map.json`（原文→译文），render 只查表替换 → **重排不重烧 token**
- 输出**两份独立文档**：原文 + `<标题>（译文）`

## 中间产物

固定在仓库外 `~/pdf-work/<slug>/`（可用 `FPDF_WORK_ROOT` 改）：

```
<slug>.md                正文 markdown
<slug>.content_list.json 结构化条目（bbox/表格 HTML/caption）
<slug>.layout.json       版式推断（每页栏数）
<slug>.xml               渲染好的 DocxXML
<slug>.trans.json        译文映射（--trans 时）
images/                  提取的图片
```

**必须在仓库外** —— 落在 git 仓库内会被 auto-sync 秒推进公开库（版权材料泄漏）。

## 脚本清单

| 脚本 | 职责 | 输入 → 输出 |
|------|------|-----------|
| `scripts/setup.sh` | 依赖预检 + 安装 | — |
| `scripts/parse.py` | MinerU 解析 + 版式推断 | PDF → 结构包 |
| `scripts/render.py` | 结构包 → DocxXML | 结构包 → `.xml` |
| `scripts/translate.py` | 逐段翻译 | 结构包 → `.trans.json` |
| `scripts/run.sh` | 编排器（串起上面全部） | PDF → 飞书文档(+Word) |

单独调试某一步时可直接调对应脚本（各脚本头部有用法注释）。

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
| 想重新排版 | 结构包已存在 | 直接调 `render.py`，不必重新解析 |