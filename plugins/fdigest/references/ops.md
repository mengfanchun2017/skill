# fdigest 运维 — 与 fpdf 的关系、常见故障、归档命名

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
| **风险条目被切成两半**（「…我们的业务、财务 / 状况和经营业绩…」） | 段落合并判据 `abs(x差) > 8pt` 太紧。SEC 项目符号 `•` 在 x=90、正文 x=108，**差 18pt** | 阈值放宽到 20pt。实测 p27 抽出 31 块实际只有 16 个条目 |
| **H1 出现残句**（`and Selling Stockholders`/`of Capital Stock`/`Matters`） | `FONT_RE` 用 `([^<]*)` 匹配不到嵌套 `<font>`。SEC 把大标题**逐字母拆成独立 font 标签** | 改 `(.*?)` 跨标签。实测找回 6,921 字符，H1 从 29（含 4 残句）变 33 完整标题 |
| **目录层级扁平**（MD&A 一个 H1 下挂 115 个 H3） | `HEAD_SIZES` 旧表把 12pt 归 H3 | 改 `[(18,1),(12,2),(9.9,3)]`。实测 SEC 字号分层：20pt=章 / 12pt=节 / 10pt=小节 |
| **中文版结构散乱、学 AI 用不上** | IPO 程序性章节（承销/税务/法律意见/附件索引）占篇幅 | `--drop-legal` 剔除 p315-343、p407-415；`--skip-front-matter` 弃 p1-15 |
| fetch 看到 `<colgroup><col/><col/>` 宽度全 0 | 用了 `--detail simple`（默认），它不返回 width | 校验必须用 `--detail with-ids` 或 `full` |
| append 报 `DOC_OPERATION_BLOCK_LIMIT actual:8313 limit:5000` | `actual` 是**这一次** append 的块数，不是文档总量。表格每格算 2 块 | 用 `split_by_cost()` 切成 <4500 块的多段，逐段 append 到同一文档 |
| `wiki +node-delete` 报 `--obj-type is required` | 必须显式给文档类型 | 加 `--obj-type docx`（或 file/sheet） |
| `wiki +node-delete` 报 `--space-id does not match` | 用了 `+space-list` 的 space_id，不是节点真实所属 | 用 `wiki +node-get` 返回的 `space_id` |
| `wiki ... update_title` 报 `missing_scope` | 缺 `wiki:wiki wiki:node:update` 授权 | 别走 wiki API；直接 `docs +update --command overwrite` 传带新 `<title>` 的 XML，文档标题与 wiki 标题会同步 |
| `block_replace --block-id -1` 把文档截断成只剩首页 | `-1` 是「替换到文档末尾」，不是「最后一个块」 | **别用它改标题**。改标题一律 `overwrite` 整篇（本地有完整 XML 时） |

### 改父文档标题的正确做法（实测踩过）

```bash
# ❌ block_replace --block-id -1 会把从该块到末尾全部替换 → 文档只剩一小段
# ✅ 本地有完整 XML 时，改 <title> 后整篇 overwrite
python3 -c "
s=open('parent.xml').read().replace('<title>旧名</title>','<title>新名</title>')
open('parent_fixed.xml','w').write(s)"
lark-cli docs +update --api-version v2 --doc <doc_token> --as user \
  --command overwrite --doc-format xml --content @./parent_fixed.xml
```

文档标题与 wiki 节点标题会同步，不需要单独的 wiki 改名 scope。

### 误操作后的恢复

`lark-cli docs +history-list --doc <token> --as user --format json` 拿 `history_version_id`，
再 `+history-revert --doc <token> --history-version-id <id> --as user` 回滚。
注意 fetch 的 `--revision-id` 不能用来预览历史版本（返回空），只能靠回滚后再看。

## 归档结构与命名（用户定案）

```
20261026 xxx 详解          ← 唯一文件来源与出处记录（父文档）
  ├── 20261026 xxx 中文内容   ← 不含案例；案例单独成文
  ├── 20261026 xxx 图表及索引  ← 只有图，无来源信息；有图才建
  ├── 20261026 xxx 案例        ← 有案例才建，每页一图 + 图下中文解读
  └── 20261026 xxx 原版报告    ← PDF/docx 直接上传；md 等转在线但内容不动；
                                  网页版**不建此文档**，在详解里放链接
```

| 项 | 规则 |
|---|---|
| 日期格式 | `YYYYMMDD` 无分隔（`20261026`），不用 `2026-10-26` |
| 中文内容 | **一篇**，不分卷；内部按块数切段依次 append |
| 前置页 | p1-15（封面/免责/目录/术语表）**不收录**，从正文开始 |
| 案例页 | 从正文剔除，单独成文 |
| 章节扉页 | 纯装饰扫描图，**不收录**（实测零文本层，无内容可保） |
| 图表文档 | **去掉来源信息**（来源在详解里），只放正文插图 |
| HTML 来源 | **不转 PDF**，在父文档写明「原始提交为 HTML，无官方 PDF」 |

### 正文结构化规则（用户多次反馈）

| 原文形态 | 转成 | 原因 |
|---|---|---|
| 脚注（8pt 小字 + 数字开头） | `<blockquote>` 引用块 | 让学习者分清「正文论断」和「注释」 |
| 术语表条目（`"agent loop" refers to…`） | `<ul><li><p><b>术语</b><br/>定义</p></li></ul>` | 词条要能一眼扫到，软换行分术语与释义 |
| 项目符号行（`•Rapid Revenue Growth. …`） | `<ul><li>` | 原文的项目符号要变成真列表 |
| 括号缩写（`（MCP）`） | `<code>MCP</code>` | 满屏括号吵，行内代码更清晰 |
| 10pt 不加粗独立短行 | H3 标题 | **此前整档漏识别**，见下方「标题丢失」 |

### 标题丢失的根因（用户反复反馈过）

用户三次反馈「标题丢了」。根因不是 PDF 太长，是判据漏了一整档：

- SEC 有些小节标题是 **10pt 不加粗**（`Internal Governance and Decision-Making`、`Electrical Power and Fuel Constraints`）
- 旧判据只认「≥12pt 加粗」和「10pt 加粗」→ 这一档全被当正文段落吞掉
- 修法是 `_is_standalone_heading()`：**前后行距都 ≥ 段落分界（17pt）**的短行才算独立标题
  - 只看「短」会误判：正文断行（`efficient training methodologies;`）也短
  - 关键在于段落内部的断行只有 11.4pt 行距，独立标题前后都是 20.4pt
- 修完标题数 **137 → 543**（H1 27 / H3 496）

### 案例文档版式（用户三次反馈后定案，已固化为 build_cases.py）

每页一节，顺序固定：

```
<h2>第 N 页 · 案例名</h2>
<img .../>                                   ← 原图，核对英文用
<callout background-color="blue">            ← 蓝色高亮块
  <p align="center"><b>案例名</b></p>         ← 居中加粗
  <ul>
    <li><p><b>数字</b>　说明</p></li>          ← 无序列表，左对齐，不用表格
  </ul>
</callout>
<blockquote>                                  ← 引文 + 署名同一个引用块
  <p>引文正文</p>
  <p align="right">姓名，职务</p>              ← 署名右对齐
</blockquote>
<h3>背景</h3> <p>…</p>
<h3>影响</h3> <p>…</p>
```

**四条硬规则**（每条都对应一次用户纠错）：

| 规则 | 错误形态 | 后果 |
|---|---|---|
| 高亮块在引言**之前** | 引言漂在高亮块上面 | 读者看不到成果就先读无关的话 |
| 引文与署名在**同一个 blockquote** | 署名单独成段，漂在正文中间 | 看不出这话是谁说的 |
| 署名 `align="right"` | 署名字号/颜色无法区分 | 用户明确要求右对齐 |
| 指标不用表格 | 原表格直接转 `<table>` | 「成果」不是子标题，表格割裂阅读 |

⚠️ **`align` 属性只在 `--detail full` 可见**。`--detail simple`（fetch 默认）会丢掉
`align`，用它验证会误判成「对齐没生效」。实测：线上 18 个署名全部 `align="right"` 落盘。

**署名判定**（`_is_attr`）：长度 ≤ 60、不含引号、含「，」、末尾落在职务词
（`ATTR_TAIL`：董事长/总裁/创始人/董事/主席/执行官/副总裁/CEO/CTO/官/合伙人…）。
用「末尾命中」而不是正则列全部职务，因为 OCR 会写「联合创始人」这类复合词。

**引文判定**（`_is_quote`）：长度 ≥ 20 且含 `「」""…`。无引号但与署名紧邻的段落
也当引文（译文常把引文改写成转述），靠「下一项是署名」这个条件兜住。

### 指标提取的限制（OCR 碎片，已知不完美）

指标来自「## 成果 / ## 结果」节。两种形态：

1. **表格形态**（14/20 案例）：`<tr><td>数字</td><td>说明</td></tr>` → 直接取两列，
   去掉末位脚注数字（`业务线1` → `业务线`）
2. **纯文本形态**（6/20）：逐行匹配 `数字+说明` 或 `说明+百分比`

**已知失败形态**——OCR 把一行指标切成三段时无解（实测 p232 SAP：
`高达` / `面向顾问的 Joule 项目交付` / `提速 14%` 三行分开，只能取到 `14% 提速`）。
这类留残缺也比瞎猜强，用户看原图核对。

### 重译触发条件（踩过的坑）

`build_zh.py` 的结构判据一变，块数就变，旧译文会**张冠李戴**贴到新块上。

`translate_blocks.py` 的缓存判断必须是**块数一致**，不能只看「文件存在」：

```python
if os.path.exists(out):
    cached = json.load(open(out))
    if len(cached.get('blocks') or []) == len(blocks):
        continue
    os.remove(out)     # 块数变了 → 删掉重译
```

**为什么图表只留一份**：拆成「来源与原文索引」+「关键图表」两份，用户要在两个文档
之间跳；且「图表只有文件名和页码」等于没给信息，要判断这张图值不值得处理还得回原文翻。
合成一份并嵌真图后，一屏之内就能决定「这个图我要不要细看」。

## 变更摘要