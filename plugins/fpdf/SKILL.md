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

把 PDF 当成「结构化数据」而非「一段文字」：先精确拆出内容与版式（表格/图片/公式/标题层级/分栏），
再用飞书文档的排版能力重建，而不是把 PDF 当图片贴上去。

## 四个入口（唯一真相源是本文件；脚本只做确定性机械步骤）

| 用户说法 | 行为 |
|---------|------|
| `/fpdf <路径>` | 解析 → 飞书文档（**默认落飞书**） |
| `/fpdf word <路径>` | 解析 → 飞书文档 → **再导出 Word 到源文件同目录** |
| `/fpdf trans <路径>` | 解析 → 飞书**原文文档 + 译文文档**（默认译成中文） |
| `/fpdf deps`（或"安装依赖"/"检查依赖"） | **只装/查依赖**，不处理任何 PDF |

路径支持 Windows 格式（`C:\...` / `C:/...`）和 WSL 格式（`/mnt/c/...`），脚本内部自动转换。

### `/fpdf deps` — 依赖安装

识别词："安装依赖"/"装依赖"/"检查依赖"/"deps"/"环境检查"。**不带 PDF 路径**。

```bash
bash ~/.claude/skills/fpdf/scripts/setup.sh          # 检查 + 缺啥装啥
bash ~/.claude/skills/fpdf/scripts/setup.sh --check  # 只检查不安装
```

执行后**逐项报告**每个依赖的状态（✓/✗），并明确区分两类：

- **需你本人动手的**：`poppler-utils` 若自动装失败，setup.sh 会**按平台**给出可复制的
  安装命令（apt / brew / dnf / pacman / apk），必须把该行**原样**给用户自行执行。
  自动会话里 sudo 常因无 TTY 不可用 → 提示用户用 `! <该行命令>` 在本会话内跑，输出回到对话。
- **我能自动搞定的**：`uv`、`lark-cli` 可自动装；MinerU token / 飞书授权需引导用户走扫码或填 key。

> 其他三个入口（处理 PDF 时）`run.sh` 也会**自动**调 setup.sh 补齐依赖，
> 所以 `deps` 主要用于**提前安装**或**排查环境问题**。

## 执行流程（4 步，全部走 `scripts/run.sh`）

### Step 0: 前置检查（自动，缺什么装什么）

**`run.sh` 会自动调 `setup.sh` 补齐**，通常不必手动跑。手动检查/安装时：

```bash
bash ~/.claude/skills/fpdf/scripts/setup.sh          # 检查 + 缺啥装啥（需 sudo 时提示）
bash ~/.claude/skills/fpdf/scripts/setup.sh --check  # 只检查不安装
```

检查 5 项：

| 依赖 | 缺失时怎么装 | 是否阻断 |
|------|-------------|---------|
| `uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | **阻断** |
| `lark-cli` | `npm i -g @larksuite/cli`，装入 PATH（或落 `~/.local/bin`） | **阻断** |
| 飞书授权 | `lark-cli auth login`（走扫码，一次性） | **阻断** |
| MinerU token | https://mineru.net → API 管理 → 建 token；plugin 用户填 `~/.claude/skill-config/fpdf.yaml`，clone 用户填 `<skill目录>/config.yaml` 的 `mineru.token` | **阻断**（默认 precision 档） |
| `poppler-utils` | 自动按平台装（apt / brew / dnf / pacman / apk）；装不上**只提示不阻断** | 不阻断 |

> **token 口径**：`run.sh` 默认走 precision 档（排版必需），缺 token 时 `parse.py` 直接
> `exit 3`。所以 MinerU token 标为**阻断**——不是"能跑 flash 档"就算过。
> 真要跑纯文本降级版，得显式 `--tier flash`。
>
> **cccconfig 用户**：上面两条（lark-cli / MinerU token）在 ccconfig 环境里有一键命令
> `bash ~/git/ccconfig/init-option.sh larkcli` 和 `... mineru key`，可用可不用；
> 独立用户直接用 `npm i -g` / 网页建 token 即可，不依赖 ccconfig。

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

父文档 token 存在**配置文件**的 `wiki_nodes.default`。配置文件按以下顺序查找
（`run.sh` 的 `_cfg_path`）：

```
1. $FPDF_CONFIG                     （环境变量显式指定）
2. ~/.claude/skill-config/fpdf.yaml （plugin 安装的用户写这里；cache 之外，跨更新稳定）
3. <skill目录>/config.yaml          （自行 git clone 的用户；也是 ccconfig 用户的
                                     apply-config.sh symlink 落点）
4. $CCPRIVATE_HOME/skill/fpdf.yaml
5. ~/git/ccprivate/skill/fpdf.yaml
```

**为何第 2 顺位存在**：用 `/plugin install` 装时，`<skill目录>` 是
`~/.claude/plugins/cache/<market>/<plugin>/<版本号>/` —— 版本化只读副本，
`/plugin update` 即整目录替换，写在那里的 `config.yaml` **会丢**。所以
plugin 用户把配置写在 `~/.claude/skill-config/fpdf.yaml`（cache 之外，更新不碰）。

未在 fpdf 配置中找到时，回落 ffeishu 配置的 default。文档索引 `doc_index` 写回
**同一个命中的配置文件**——plugin 用户写 `~/.claude/skill-config/`，clone 用户写
自己的 config.yaml，都不碰 ccprivate。

用户说"保存父文档链接"或"配置 fpdf"时：
用 AskUserQuestion 问父文档 URL/token → 写入**命中文件**（同上第 1 顺位命中项）：

```yaml
wiki_nodes:
  default: "<wiki节点token>   # 从父文档 URL 的 /wiki/<token> 取
doc_index: []                  # 自动追加，勿手改
```

`--parent` 参数可临时覆盖。

## 解析档位（决定能不能排版）

走 **MinerU 云端 API**（`mineru.net/api/v4`，非本地包），Precision 档 `model=vlm`。

| 档位 | 返回 | 用途 |
|------|------|------|
| **Flash**（免费，无 token） | 只有 markdown 纯文本，**无坐标无图片** | 只要文字时降级用 |
| **Precision**（token） | markdown + `content_list` + `content_list_v2` + 图片 + 版面树 | **默认**，排版必需 |

`/fpdf` 默认走 Precision —— 没有 bbox 就无法还原分栏、表格结构。
Flash 档解析出的包 `content_list` 为空，render 会直接报错拒绝排版。

### 两个 content_list：v1 与 v2（render 默认用 v2）

MinerU 的结果 zip 里同时有 v1 和 v2 两份，**结构不同**：

| | v1 `content_list.json` | v2 `content_list_v2.json` |
|---|---|---|
| 组织 | 全文档扁平数组 | **按页数组**（天然版面顺序） |
| 行内公式 | ❌ 没有（以 `$...$` 混在正文里） | ✅ `equation_inline` 片段 |
| 参考文献 | 散落 `ref_text` | `list` + `list_type: reference_list` |
| 标题层级 | `text_level` | `title` + `level` |
| 表格 | `table_body`（html 串） | `html` + `table_caption` + footnote |

`render.py` 默认 `--source auto`：有 v2 用 v2，否则回落 v1。
**v2 是解决行内公式裸露（`$25^{\circ}C$`）的关键** —— 实测 55 号 4 处、88 号 54 处
公式在 v1 里是纯文本，v2 才还原成公式片段 → 渲染为 `<latex>`。

解析同时落 `*.blocks.json`（MinerU 版面树，行级 span + 置信度）与 `*.html`（MathML），
供后续更细的版式还原取用。这些都从结果 zip 里取 —— SDK 的 `ExtractResult`
只暴露 v1 markdown/content_list/图片三样，不 `save_all` 就永远拿不到。

## 排版能力映射（PDF 结构 → 飞书块）

写飞书 DocxXML 时用这些标签（**均已实测**）：

| PDF 内容 | 飞书 XML | 说明 |
|---------|---------|------|
| 表格 | `<table><colgroup><col width="N"/></colgroup><thead><tr><th>` | **列宽之和 = 822**；见下方警告 |
| 行内公式 / 上下标 | `<latex>E = mc^2</latex>` / `<latex>^{1,2}</latex>` | **飞书无 `<sup>`/`<sub>`**，上标一律 latex |
| 分栏 | `<grid><column width-ratio="0.5">…</column>…</grid>` | 各列 ratio 之和 = 1（默认不用，见下） |
| 强调块 | `<callout emoji="💡" background-color="light-blue">` | 子块仅 `p/ol/ul/checkbox` + 行内标签 |
| 引用 | `<blockquote><p>…</p></blockquote>` | 首页信息区用它包住元信息 |
| 分隔线 | `<hr/>` | 论文信息区与正文之间 |
| 图片 | `<img path="@./images/xxx.jpg" caption="…"/>` | 路径**相对 CLI 工作目录** |

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

## 分栏策略（`--columns`，**默认不用**）

**结论：论文转飞书默认不分栏**（`--columns flow`）。实测 `<grid>` 左右并排在飞书里
挤成一团、移动端更差，用户明确弃用。

- `--columns flow`（**默认**）：按原阅读顺序展开为单栏流。内容与层级全保留。
- `--columns grid`：仍保留该能力但**不推荐** —— 按 bbox 把每页分左右栏输出 `<grid>`，
  只对真双栏页生效（判据：x0 左边界双峰且两簇间距 > 页宽 25%）。

## 图片（用 PDF 原图，不切碎）

MinerU 会把一页里的一张 figure（含 A/B/C/D 子图）**切成多块低清截图** ——
实测 55 号一张 5099x3390 的图被切成 3 块 617x429 的缩略图，分辨率掉 8 倍、拼接关系丢失。

`parse.py` 直接从 PDF 抽**原始嵌入图**（pymupdf `get_images`/`extract_image`），落
`<slug>.figure_map.json` 记录「原图 ↔ 页面 bbox」；`render.py` 按**页内出现顺序**把多个
MinerU 图块归到同一张原图、只输出一次（合并碎片）。

- 只对**真被切碎**的页生效：判据是 **MinerU 图块数 > 该页 PDF 原图数**（写进
  `figure_map` 的 `page_ok`）。55 号 `3 图块 / 1 原图` → 换原图；88 号 `1 图块 / 1 原图`
  → 不换（那种 figure 本身由多元素拼成，MinerU 切分反而语义正确）。
- 同内容多 xref（PDF 重复嵌入）按 md5 去重；小图标（<800 宽）和极扁装饰条
  （`1456x30` 这类）不算 figure。

## 参考文献（`--keep-refs`）

`ref_text` / `reference_list` 默认**丢弃**（长文献表会淹没正文）。要完整结构加 `--keep-refs`：

- **编号**：源自带编号的（88 号式 `1. Jiang…`）用 `<ol>` 自动编号并去掉原文前缀；
  源无编号的（55 号式悬挂缩进）用 `<ul>` —— 不能一律 `<ol>`，否则飞书会给原本
  无编号的文献**强加 "1."**。
- **合并**：v2 里每条文献是一个 list 块（55 号 69 条 = 69 块），渲染时按「同栏 + 相邻」
  归组，避免散成 69 个列表。
- **顺序**：双栏页里左右栏条目在数组里交错（左栏 A–D、右栏 D–F），归组后顺序自然
  正确（字母序 A→Y）。

## 首页信息区（引用块 + 分隔线）

论文首页的作者/OPEN ACCESS/Edited by/Received/Keywords 等元信息，渲染成
`<blockquote>` 引用块，并在正文（INTRODUCTION）前插 `<hr/>` 分隔线区分。

PDF 里这些标签用 Bold/BdIt 字体排（MinerU 丢掉了字体信息），`_bold_labels()` 按标签名补
`<b>` —— 中英标签都列（译文版标签会变成"编辑："/"关键词："）。只匹配**段首**，避免正文中
的 "引用：" 被误加粗。

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
<slug>.md                  正文 markdown
<slug>.content_list.json   v1 结构条目（平铺数组）
<slug>.content_list_v2.json v2 结构条目（按页，含 equation_inline）★ render 默认用
<slug>.blocks.json         MinerU 版面树（行级 span + 置信度）
<slug>.html                full.html（MathML 公式），备用
<slug>.figure_map.json     「PDF 原图 ↔ 页面 bbox + page_ok」映射
<slug>.layout.json         版式推断（每页栏数）
<slug>.xml / .zh.xml       渲染好的 DocxXML（原文 / 译文）
<slug>.trans.json          译文映射（--trans 时）
images/                    图片（MinerU 裁切图 + fig_* 原图）
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
| 依赖报缺想一次性装 | — | `/fpdf deps`（或"安装依赖"）跑 setup.sh；`poppler-utils` 若装不上按平台提示用户自行执行 |