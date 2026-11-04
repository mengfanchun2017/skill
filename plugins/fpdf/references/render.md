# fpdf 排版细则 — 父文档 / 解析档位 / 能力映射 / 图片 / 翻译 / 返工

## 父文档（所有输出落在此处）

父文档 token 存在配置的 `wiki_nodes.default.token`。读写走 `fcore conf`：

```bash
F=~/.claude/skills/fcore/bin/fcore
$F --plugin fpdf conf get wiki_nodes.default.token
$F --plugin fpdf conf set wiki_nodes.default.token "<wiki节点token>"
$F --plugin fpdf conf path wiki_nodes.default.token      # 看当前从哪读
```

⚠️ 路径必须写到 `.token`：`wiki_nodes.default` 本身是 `{token: ...}` 结构，
`fcore conf get` 遇到嵌套 dict 会报错并提示子键。

> 脚本层（`parse.py`）暂时仍走旧配置层 `ffeishu/references/config_env.py`（经
> `_skillconf_boot.py` 定位），只为不破坏已在跑的机器。**文档层与新增代码一律用 fcore**；
> 等脚本也迁完再删旧层。

用户自填落 `~/.claude/skill-config/fpdf.yaml`（`/plugin update` 不覆盖）。
未配置时回落 ffeishu 的 default；`--parent` 参数可临时覆盖。

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