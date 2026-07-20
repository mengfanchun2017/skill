---
name: fpptx
user-invocable: true
description: |
  PPTX 总控 — 从 md/wiki 到 PPTX。
  OfficeCLI 引擎（原生 OpenXML），支持批量 JSON、模板合并、autofit 后处理。
allowed-tools: Read, Write, Bash, Glob
---

# f-pptx — OfficeCLI PPTX 生成

从 wiki 文档或 Markdown 生成飞书 PPTX。OfficeCLI 单引擎，零外部依赖。

## 配置

> 📖 完整说明 → [config.aiagt.dev](https://config.aiagt.dev/f-pptx)

**ccconfig 用户**：真实值放 `ccprivate/skill-config/f-pptx.yaml`，`init-skill.sh sync` 自动覆盖。
**独立用户**：OfficeCLI 免费安装即可使用，无需额外配置。

## 安装

```bash
curl -fsSL https://d.officecli.ai/install.sh | bash
```

---

# OfficeCLI 引擎

## 核心命令

```bash
# 创建空白 PPTX
officecli create deck.pptx

# 打开文件（启动常驻进程，加速后续操作）
officecli open deck.pptx

# 添加幻灯片
officecli add deck.pptx / --type slide --prop title="标题" --prop text="副标题" --prop background=#1E2761

# 添加形状
officecli add deck.pptx "/slide[1]" --type shape \
  --prop text="关键指标" --prop font=Georgia --prop size=36 --prop bold=true \
  --prop color=#FFFFFF --prop fill=#4472C4 --prop preset=roundRect \
  --prop x=2cm --prop y=4cm --prop width=12cm --prop height=3cm

# 批量模式（推荐 — 一次创建整个 deck）
officecli batch deck.pptx --input deck_commands.json

# 关闭 + 验证
officecli close deck.pptx
officecli validate deck.pptx

# 查看结构
officecli query deck.pptx slide --json
officecli get deck.pptx "/slide[1]" --depth 1 --json
```

## 批量模式示例

```json
[
  {"command": "add", "parent": "/", "type": "slide", "props": {"title": "封面", "text": "副标题", "background": "#1E2761"}},
  {"command": "add", "parent": "/", "type": "slide", "props": {"title": "内容页", "text": "正文内容"}},
  {"command": "add", "parent": "/slide[2]", "type": "shape", "props": {"text": "要点1", ...}},
  {"command": "add", "parent": "/", "type": "slide", "props": {"title": "结束", "text": "谢谢"}}
]
```

**注意**：批量模式需要文件先存在（先 `create` 再 `batch`）。用 `--input` 传 JSON 文件避免 stdin 冲突。

## 设计系统

OfficeCLI 内置设计规范，生成 deck 时直接引用：

### 色板速查

| 主题 | 主色 | 辅色 | 强调色 | 正文 | 适用场景 |
|------|------|------|--------|------|---------|
| Midnight Executive | `1E2761` | `CADCFC` | `FFFFFF` | `333333` | 金融、高管报告 |
| Coral Energy | `F96167` | `F9E795` | `2F3C7E` | `333333` | 产品发布、营销 |
| Forest & Moss | `2C5F2D` | `97BC62` | `F5F5F5` | `2D2D2D` | 可持续、ESG |
| Charcoal Minimal | `36454F` | `F2F2F2` | `212121` | `333333` | 极简企业风 |
| Ocean Gradient | `065A82` | `1C7293` | `21295C` | `2B3A4E` | 科技、数据 |

### 字号规范

| 元素 | 最小 | 典型 |
|------|------|------|
| 幻灯片标题 | ≥ 36pt bold | 36-44pt |
| 段落标题 | ≥ 20pt | 20-24pt |
| 正文 | ≥ 18pt | 18-22pt |
| 脚注/标签 | ≥ 10pt muted | 10-12pt |

### 字体配对

| 标题 | 正文 | 适用 |
|------|------|------|
| Georgia | Calibri | 正式商务、金融 |
| Arial Black | Arial | 营销、产品发布 |
| Trebuchet MS | Calibri | 科技、SaaS |
| Consolas | Calibri | 开发者工具 |

### 布局网格

Widescreen 16:9 = `33.87 × 19.05cm`，12 列网格：
- 边距 ≥ 1.27cm
- 卡片间距 ≥ 0.76cm
- 3 卡布局：`col = (33.87 - 3 - 1.52) / 3 = 9.78cm`

## 模板合并

```bash
# 创建模板（含 {{key}} 占位符）
officecli create template.pptx
officecli add template.pptx / --type slide --prop title="{{title}}" --prop text="{{subtitle}}"

# 合并数据
officecli merge template.pptx output.pptx --data '{"title":"Q4报告","subtitle":"营收增长18%"}'
```

## QA 检查清单

```bash
officecli validate deck.pptx                      # Schema 验证
officecli view deck.pptx issues                    # 溢出/格式问题
officecli view deck.pptx text | grep -iE 'xxxx|lorem|<todo>'  # 占位符残留
officecli query deck.pptx 'picture:no-alt'         # 缺 alt 文本的图片
```

---

# 飞书 Slides API 操作

## 仓库

`config.yaml` → `slides_base_url`

| 表 | ID | 说明 |
|---|----|------|
| Presentations | `config.yaml` → `tables.presentations` | PPT 元数据：名称、Wiki URL、Presentation ID |
| Slides | `config.yaml` → `tables.slides` | 每页内容：Slide ID、页码、标题、文本、图片 |

## 可行操作

### 读取
| 操作 | 命令 |
|------|------|
| 读完整 PPT XML | `lark-cli slides xml_presentations get --params '{"xml_presentation_id":"<pid>"}' --format json` |
| 读单页 XML | `lark-cli slides xml_presentation.slide.get` |
| 提取文本 | 正则 `<p>(.*?)</p>` 去标签 |

### 创建/上传
| 操作 | 命令 |
|------|------|
| 新建空 PPT | `lark-cli wiki +node-create --space-id <id> --obj-type slides --title "<name>"` |
| 新建页 | `lark-cli slides xml_presentation.slide.create` |
| PPTX 上传为 wiki 子文件 | `lark-cli drive +upload --file ./out.pptx --wiki-token <token>` |

### 更新/删除/复制
| 操作 | 命令 |
|------|------|
| 替换整页 | `lark-cli slides xml_presentation.slide.replace` |
| 删除页 | `lark-cli slides xml_presentation.slide.delete` |
| 复制 PPT（保留图片） | `lark-cli drive files copy --params '{"file_token":"<src>"}' --data '{"type":"slides","name":"<name>"}'` |

## 不可行操作

| 操作 | 原因 |
|------|------|
| 跨 PPT 复制图片页 | 图片使用内部 media token → relation mismatch |
| PPTX 导出为在线 Slides | `export_tasks` 仅支持 doc/sheet/bitable/docx |
| PPTX 导入为在线 Slides | `import_tasks` 不支持 slides |

---

# OfficeCLI 测试记录

测试文件位于 `/tmp/ppt-tests/officecli/`：

| 文件 | 内容 | 结果 |
|------|------|------|
| `test1_blank.pptx` | 空白创建 + 添加 slides/shapes | ✅ |
| `test2_batch.pptx` | 批量 6 页创建 | ✅ 6/6 |
| `test3_merged.pptx` | 模板合并 `{{key}}` 替换 | ✅ 3 keys |
| `test5_table.pptx` | CSV → 表格，含样式 | ✅ |
| `test6_chart.pptx` | 图表 + 图片嵌入 | ✅ |
| `demo_full.pptx` | 8 页全功能演示 deck | ✅ 41/41 validate 通过 |

### 已确认的 OfficeCLI 注意事项

1. **文件锁定**：`create`/`add` 自动启动常驻进程锁定文件。批量操作后记得 `close`，或先 `pkill officecli` 清理。
2. **批量输入**：用 `--input file.json` 而非 `--commands "$(...)"` 避免 stdin 冲突警告。
3. **表格数据**：用 `data="H1,H2;R1,R2;R3,R4"` 格式（分号分行，逗号分列），首行为表头。
4. **图表数据**：用 `series1.name=... series1.values="1,2,3" series1.color=...` 格式，不能用 `data=`
5. **图片**：用 `--prop src=/path/to/file.png` 而非 `--prop image=...`
6. **路径引用**：zsh/bash 必须引用 `"/slide[1]"`，防止 glob 展开
7. **`$` 符号**：`--prop text='$15M'` 必须单引号，双引号会被 shell 展开
8. **幻灯片尺寸**：默认 16:9 = 33.87 × 19.05cm
9. **形状 ID**：自定义形状从 `@id=10000` 起，模板占位符用 `@id=2,3,...`
10. **MCP 模式**：`officecli mcp claude` 注册为 MCP server，但在当前 session 中不需要（直接 CLI 调用更高效）
11. **不支持属性**：`borderRadius`（圆角）不被 shape 支持；图表的 `series1.color`/`series2.color`/`legendPos` 不被支持，用默认图表颜色即可
12. **close 失败保护**：`officecli close` 失败会导致文件截断（如 137KB→8KB），此时文件不可恢复。构建完成后必须 `close && validate && ls -lh` 三连确认
13. **常驻进程冲突**：如果上一次 `close` 失败，残留的 officecli 进程仍锁住文件。新 `create` 会成功但实际写入旧文件。重建前必须 `pkill -9 officecli` 清理

### 大 deck 构建策略

50+ 页 PPT 的生成分两个阶段：

| 阶段 | 耗时占比 | 可并行 | 方法 |
|------|---------|--------|------|
| 内容分析 + 脚本编写 | ~90% | **可以** | 按章节拆分，多个 subagent 各自写 section 的 shell 脚本 |
| 脚本执行 | ~10% | 不能 | 单文件单进程，5 个 Part 脚本顺序执行，共约 30 秒 |

**并行化工作流**（以 50 页为例）：

```
1. 读取源文档 → 按章节拆分为 5 个 section
2. 并行启动 5 个 subagent，每个负责 1 个 section 的脚本编写
3. 收集所有脚本 → 顺序执行 Part 1-5
4. officecli close → validate → 确认文件 > 100KB
5. python3 post-process（autofit 等）
```

注意事项：
- 并行前先 `create` + `open` 好文件，所有 subagent 共用同一个文件路径
- subagent 输出 shell 脚本即可，不直接调 officecli（避免进程冲突）
- 每个 Part 脚本 ≤ 10 页，方便调试

### 文本溢出与 autofit

**核心问题**：OfficeCLI 创建 shape 时指定的 `size` 是固定字号，文本多了会溢出 shape 边界。

**OfficeCLI 的 `autoFit` 属性**（`officecli help pptx shape`）：

```
autoFit=normal  →  Shrink text on overflow（对应 OpenXML normAutofit）
autoFit=shape   →  Resize shape to fit text（对应 spAutoFit）
autoFit=none    →  Do not autofit（对应 noAutofit）
```

**关键坑**：`autoFit=normal` 写入的 `<a:normAutofit/>` **不带 `fontScale` 属性时默认值为 100000（100%）**，等于不缩小。PowerPoint 首次打开时不会自动计算缩放比例——文本仍按原大小显示，只有用户点击编辑该形状后才触发重新计算。

**正确做法**：用 python-pptx 后处理，写入带 `fontScale` 的 `normAutofit`：

```python
from pptx import Presentation
from pptx.oxml.ns import qn
from lxml import etree

prs = Presentation("output.pptx")
for slide in prs.slides:
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        bodyPr = shape.text_frame._txBody.find(qn('a:bodyPr'))
        # 清除已有 autofit
        for tag in [qn('a:normAutofit'), qn('a:spAutoFit'), qn('a:noAutofit')]:
            for el in bodyPr.findall(tag):
                bodyPr.remove(el)
        # fontScale=55000 = 允许缩到 55%，只在溢出时触发
        norm = etree.SubElement(bodyPr, qn('a:normAutofit'))
        norm.set('fontScale', '55000')
prs.save("output.pptx")
```

**为什么不用 `fit_text()`**：python-pptx 的 `TextFrame.fit_text()` 会预计算并写入固定缩小字号，导致文本即使能撑满也被缩小、留大量空白。

**fontScale 取值指南**：

| fontScale | 最小字号比例 | 适用场景 |
|-----------|------------|---------|
| `80000` | 80% | 标题/大字，略微溢出 |
| `65000` | 65% | 卡片正文，中等密度 |
| `55000` | 55% | 列表/表格/高密度内容 |
| `40000` | 40% | 极端密集（此值以下可读性差） |

### 示例文件（`C:\unified-ppt\`）

| 文件 | 页数 | 主题 | 亮点 |
|------|------|------|------|
| `demo1_executive_report.pptx` | 5 | Midnight Executive | 柱状图 + 两栏布局 |
| `demo2_product_launch.pptx` | 5 | Coral Energy | KPI 大数字 + 时间线 |
| `demo3_data_dashboard.pptx` | 6 | Ocean Gradient | 折线图 + 环形图 |
| `系统分析师备考完全指南.pptx` | 50 | Academic Navy | 14 章全覆盖，488 形状 |

### 自定义主题：Academic Navy

用于学术/备考类 deck：
- 主色 `1E3A5F`（深海军蓝）、辅色 `E8EDF2`（浅灰）、强调色 `C4A35A`（金）、正文 `2D2D2D`、弱化 `7A8A94`
- 变体 `2A6291`（中蓝）用于二级卡片
- 警告卡片用 `990011`（深红）+ `FFFFFF` 文字
