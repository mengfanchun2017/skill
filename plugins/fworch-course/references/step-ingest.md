# Mode B: 现有材料课程化（ingest）

> fworch-course 现有材料课程化模式。把一个已下载课程的原始课件整理为飞书结构化文档。
> 与 Mode A 的区别：Mode A 从零调研创作；Mode B 对**已有材料**做课程化 + 现代更新。

## 输入

- 已下载的课程材料目录（PDF 讲义/逐字稿、Excel、案例论文、录屏字幕）
- 课程 slug（课程名全小写英文）、父页 wiki node、课程方向

## 输出

父页 `memo <slug>` 下的两层子文档：

| 层 | 命名 | 内容 |
|----|------|------|
| memo | `<slug>-week<N>-memo` / `<slug>-<case>-memo` | 原始记录（官方多源合并 / 原文全文） |
| update | `<slug>-week<N>-update` / `<slug>-<case>-update` | 课程化精读（中文）+ 现代演进 |

## 步骤

### Step 0: 抽取（本地）

- PDF → 文本/**结构**：**委托 fpdf 解析层** `uv run ~/.claude/skills/fpdf/scripts/parse.py "<路径>" --outdir <仓库外目录>`
  （统一走 fpdf，PDF 解析能力单点维护；产出 `<slug>.md` 纯文本 + `.content_list.json` 结构 + 图片）
  - 只需讲义文字 → 加 `--tier flash`（免费、快）；要保留表格/图片结构 → 默认 Precision
  - 旧法 `pymupdf get_text()` 仅在极简场景（纯文字讲义）下可直接用
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

### Step 5: 归集（Base 写回）

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

## 命名规则（硬约束）

- slug 全小写英文，`-memo` / `-update` 后缀固定
- 父页 `memo <slug>`
- 周/案例关键字小写；如 `wharton-business-analytics-week1-memo`

## 坑

- **版权材料禁止进公开仓库**：输出目录必须在 `~/git/` 之外（如 `~/inbox/<course>/`）；否则 auto-sync 会推送
- lark-cli `+create --parent-token` 用 wiki node token；返回 `docx/<id>` 即已挂到 wiki 节点
- `--content @file` 只接受 cwd//tmp/~/files 下的路径；越界用 stdin（`--content -`）
- 附件上传 `base +record-upload-attachment` 同样限于 cwd//tmp/~/files
