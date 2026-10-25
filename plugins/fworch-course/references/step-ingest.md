# Mode B: 现有材料课程化（ingest）

> fworch-course 现有材料课程化模式。把一个已下载课程的原始课件整理为飞书结构化文档。
> 与 Mode A 的区别：Mode A 从零调研创作；Mode B 对**已有材料**做课程化 + 现代更新。

## 输入

- 已下载的课程材料目录（PDF 讲义/逐字稿、Excel、案例论文、录屏字幕）
- 课程 slug（课程名全小写英文）、父页 wiki node、课程方向
- 课程缩写（大写字母，如 `BADTI`）——用于复习层目录名

## 输出：三层结构（v2）

父页是一个**入口页**（不是目录页），下挂两个分区节点，各自再做一份内部导航页：

```
memo <slug>                     入口页（课程总结：定位/主线/九周与案例一览/阅读路径）
├── courseref                   课程参考区（导航页 + 18 篇英文原文）
│   ├── <slug>-week<N>-memo     原课程英文材料
│   └── <slug>-<case>-memo
└── <来源> <缩写> refresh         复习课程区（导航页 + 3 篇总览 + 18 篇中文精读）
    ├── <缩写> 课程总结
    ├── <缩写> 课程结构
    ├── <缩写> 知识点列表
    ├── <slug>-week<N>-update
    └── <slug>-<case>-update
```

**命名规则**：

| 实体 | 命名 | 说明 |
|------|------|------|
| 入口页 | `memo <slug>` | 父页即入口页；**内容是课程总结，不是目录** |
| 参考区节点 | `courseref` | 课程原文（英文） |
| 复习区节点 | `<来源> <缩写> refresh` | 来源（如 `Wharton`）+ 课程**大写缩写** + `refresh`。缩写取课程全称首字母，如 Business Analytics: From Data to Insights → `BADTI` |
| 参考区子文档 | `<slug>-week<N>-memo` / `<slug>-<case>-memo` | 保留原课程命名，不改名 |
| 复习区子文档 | `<slug>-week<N>-update` / `<slug>-<case>-update` | 保留原名，不改名 |
| 总览三篇 | `<缩写> 课程总结` / `<缩写> 课程结构` / `<缩写> 知识点列表` | 见 Step 5 |

> **为什么父页是入口页而非目录**：读者从 wiki 侧边栏点进来，需要立刻知道"这套材料是什么、怎么看、从哪开始"；
> 纯链接列表把判断成本推给读者。目录信息放进各分区的导航页（courseref 节点本体 + refresh 节点本体）。

## 步骤

### Step 0: 抽取（本地）

- PDF → 文本/**结构**：**委托 fpdf 解析层** `uv run ~/.claude/skills/fpdf/scripts/parse.py "<路径>" --outdir <仓库外目录>`
  （统一走 fpdf，PDF 解析能力单点维护；产出 `<slug>.md` 纯文本 + `.content_list.json` 结构 + 图片）
  - 只需讲义文字 → 加 `--tier flash`（免费、快）；要保留表格/图片结构 → 默认 Precision
  - 旧法 `pymupdf get_text()` 仅在极简场景（纯文字讲义）下可直接用
  - **纯文本批量提取**用 `pdftotext -layout` 最快（几十篇一次跑完），结构化解析才走 fpdf
- Excel/PPT：另存或转 CSV
- 录屏：字幕文件直接用
- 产出物放仓库**外**目录（避免 auto-sync 把版权材料推进公开库）

### Step 1: memo（原始记录）

按「学习周期（周）/ 单个案例」为单元合并材料：

- 周 memo = 该周全部讲稿类材料合并（要点讲稿 + 讲义卡片 + 视频逐字稿），清洗页眉页脚、重排段落
- 案例 memo = 该案例原文全文
- 命名 `<slug>-week<N>-memo`，一个单元一个子文档

### Step 2: 骨架（spine）

从材料抽取要点骨架（每节标题 + 要点），供 Step 4 复用；`-memo` 是详细原文，spine 是压缩版。

### Step 3: 现代演进（2024—2026）

按单元主题搜最新发展（调 `fsearch` / `fresearchframe`），产出「现代演进」片段（工具/方法/数据/案例），供 update 嵌入。可并行多单元。

### Step 4: update（课程化精读）

`memo 骨架 + 演进` → 按 `fwstd-course/references/lesson-template.md` 组装：

```
# Week N: <英文主题>
> 本部分基于 <课程/来源> 讲稿整理，并补充 2024—2026 年公开资料更新。
# 学习目标（细粒度可衡量）
# 导入
# 核心框架 / 核心知识点（讲透原理，关键处用表格）
# 现代演进（2024—2026）
# 本章小结
# 课后练习提示
```

案例 update 结构：`案例背景 / 核心方法 / 关键结论与启示 / 现代演进 / 讨论问题`。

### Step 5: 总览三篇（复习区）

| 文档 | 内容 | 硬要求 |
|------|------|--------|
| `<缩写> 课程总结` | 课程定位表、课程主线（含流程图白板）、九周模块一览、案例一览、学完能达到什么、阅读路径建议 | 至少 1 张白板 |
| `<缩写> 课程结构` | 三层结构：模块层（九周表格）/ 知识层（每周核心概念）/ 能力层（对照 baframework） | **含结构 mindmap 白板** |
| `<缩写> 知识点列表` | 按 baframework 一级能力归位的全部知识点；末尾列"课程未覆盖但框架包含"的领域 | **含能力→技能全图白板**（15 一级 + 64 二级） |

知识点列表的归位依据 = framework 表的 `关联课程` 字段（每个二级技能挂在哪一周）。

### Step 6: 归集（Base 写回）

**courselist 表**（课程 → 学习周期）
- 课程根行 1 条（`课程名称`=课程原名；`父记录` 空）
- 每学习周期（周）1 条子记录：`课程名称`=`Week N: <主题>`（**主字段必须区分行**，否则网格平铺看不出层级）、`周次`(整数)、`父记录`→课程根
- `关联知识点` 只挂**周子记录**（课程根不挂）；`参考附件` = 该周 PDF；`课程链接` = 总 module/课表页
- **分组展示**：`base +view-set-group --view-id <v> --json '{"group_config":[{"field":"父记录"}]}'`（飞书无原生树视图，靠分组看层级）

**framework 表**（能力地图，SFIA 三层）
- capability 行（能力域）`父记录` 空；skill 行 `父记录`→其 capability
- `关联课程`→courselist **周子记录**（n-n，双向自动生成 courselist.关联知识点）；`相关课程`(文本) 冗余记录对应单元名
- knowledge 不入表（写进 skill 文档）；命名用名词短语
- 同样 `view-set-group` by 父记录

结构细则与可复用步骤见 `fwstd-course/references/framework-template.md`。

## 搬运既有文档（不重建）

课程化 v1 → v2 时，已有子文档**用 `wiki +move` 搬移**，不要重建后重新写入（重建会丢评论、丢协作者、丢修订历史）：

```bash
lark-cli wiki +move --node-token <子节点 node_token> --target-parent-token <新父节点> \
  --target-space-id <space_id> --as user
```

- `--node-token` 用 **wiki node_token**（不是 `docx/<obj_token>`）
- 结果里 `parent_node_token` 变为目标即成功
- **ve 后立刻 `+node-list` 可能返回 0 条**（最终一致性延迟），等 5 秒再查
- **wiki 无 rename 命令**：子节点标题改不了，故搬移前就该定好命名；`courseref` / `refresh` 这类**新建节点**标题可控

## 命名规则（硬约束）

- slug 全小写英文，`-memo` / `-update` 后缀固定
- 入口页 `memo <slug>`
- 复习区 `<来源> <缩写> refresh`（缩写为课程全称首字母大写）
- 周/案例关键字小写；如 `wharton-business-analytics-week1-memo`

## 坑

- **版权材料禁止进公开仓库**：输出目录必须在 `~/git/` 之外（如 `~/inbox/<course>/`）；否则 auto-sync 会推送
- lark-cli `+create --parent-token` 用 wiki node token；返回 `docx/<id>` 即已挂到 wiki 节点
- `--content @file` 只接受 cwd//tmp/~/files 下的路径；越界用 stdin（`--content -`）
- 附件上传 `base +record-upload-attachment` 同样限于 cwd//tmp/~/files
- `wiki +node-list` 返回的数组键是 `data.nodes`（**不是** `data.items`）；`--page-size` 上限 **50**
- `wiki +node-delete` 必须传 `--obj-type docx` + `--yes`
- 批量 HTML→DocxXML 转换脚本见 ffeishu 编排层：`references/md2docxxml.py`
  （标题样式：H1 蓝字无底色 / H2 及以下默认黑；正文不撒黑体；表格按内容选型 2列→定义式列表、步骤→有序列表、3–4列→真表格、≥5列→嵌套列表；从大纲自动生成结构 mindmap）
- **Markdown 表格分隔行有 `|-|-|` 与 `|------|` 两种**，判定正则必须容忍单横线，否则分隔行被当数据、整表错位
- 排版细则与硬约束唯一真相源：`ffeishu/references/write-checklist.md` §2
- 写飞书前**必调 ffeishu skill**（格式约束只在 skill 调用时加载）