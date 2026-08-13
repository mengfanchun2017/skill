---
name: fpptx
user-invocable: true
description: |
  PPT/X 总控 — 从 md/wiki/材料到 PPTX 或飞书 Slides。
  OfficeCLI 引擎（原生 OpenXML），也支持 lark-cli 生成飞书在线幻灯片。
  内置 6 套设计主题，图表委托 fdiagram，内容规范委托 freportstd。
allowed-tools: Read, Write, Bash, Glob
---

# fpptx — PPT / 飞书幻灯片生成

从材料文档/会议纪要/调研资料/方案草稿/主题大纲生成正规演示文稿。
输出前**问用户**：PPTX 文件 / 飞书在线 Slides / 都要。

图表委托 `fdiagram` 生成可编辑 SVG 嵌入。

## 配置

> 📖 完整说明 → [config.aiagt.dev](https://config.aiagt.dev/fpptx)

**ccconfig 用户**：真实值放 `ccprivate/skill/fpptx.yaml`，`init-skill.sh sync` 自动覆盖。
**独立用户**：OfficeCLI 免费安装即可使用（`curl -fsSL https://d.officecli.ai/install.sh | bash`），无需额外配置。

> ⚠ OfficeCLI 是 .NET 应用，依赖 libicu。缺库启动即报 `Couldn't find a valid ICU package`。安装：`sudo apt-get install -y libicu78`（Ubuntu 26.04；其他版本 `apt-cache search libicu`）。ccconfig 用户 `init-skill.sh sync` 会自动装（deps.txt 已声明）。无 sudo 环境可用 `DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1` 绕过。

---

## 执行流程

### 1. 判断模式
- **材料模式**：用户提供文档、链接、笔记、会议纪要、大纲
- **演示模式**：用户只说"演示一下""看看效果"——走[演示兜底](#演示兜底) 9 页默认 deck

### 2. 分析材料
提取：受众、目的、核心观点、关键论据、章节结构、必须保留的名词和数字

### 3. 规划叙事
默认 8-12 页。每页确定：页标题、单一核心信息、页型（封面/目录/内容/数据/对比/流程/收尾）、模板主题

### 4. 选择风格
从 6 套设计主题中选 1-2 套形成风格家族（封面/章节/收尾页用大胆的，内容页用克制的）

### 5. 生成幻灯片
- 图表委托 `fdiagram` → 生成可编辑 SVG → 嵌入 slide
- 正文用 OfficeCLI 原生元素（文本框/形状/表格）
- 禁止整页截图，禁止把提示词/模板名/生成过程写进页面

### 6. 校验
逐页检查：文字溢出、元素重叠、字号可读、边距、颜色对比、风格统一

### 7. 问用户输出方式
```
你要怎么交付？
A) PPTX 文件
B) 飞书在线 Slides
C) 都要
```
- 选 B/C 前先检查 lark-cli 在线生成能力 → [飞书 Slides 前提检查](#飞书-slides-前提检查)
- 若选 B/C 但 lark-cli 无法在线生成 → 仅输出 A 并说明原因

### 8. 交付
- PPTX：`close && validate && ls -lh` 三连确认 → 输出文件路径
- 飞书 Slides：返回 slides 链接
- 输出：页数 + 风格主题 + 校验结果

---

## 演示兜底

用户要求演示且无材料时，生成 9 页示例 deck：

**《AI Agent 如何把零散材料变成可交付成果》**

默认受众：业务、产品、运营、管理者。

| 页 | 内容 |
|----|------|
| 1 | 封面：核心承诺和典型场景 |
| 2 | 目录：从问题到交付的叙事路径 |
| 3 | 问题：信息分散、人工整理慢、交付格式不稳定 |
| 4 | 方法：读取、抽取、规划、生成、验证、交付 |
| 5 | 能力地图：文档、数据、视觉、协作、自动化 |
| 6 | 应用场景：会议纪要、方案、质量报告、培训 deck |
| 7 | 示例流程：从一份材料到一套成品演示稿 |
| 8 | 价值证明：速度、一致性、可追溯、可编辑 |
| 9 | 收尾：适合什么时候使用，用户最终拿到什么 |

---

## PPT 设计规则

### 基本要求
- 默认 16:9，语言跟随用户材料
- 页面元素必须可编辑（文本框、形状、表格、图表、图片占位）
- 禁止整页截图，禁止把提示词/模板名/生成过程写进页面
- **每页只讲一个核心观点**
- 标题要像结论（"营收增长 18%" 而非 "营收情况"）

### 版式规范
| 页型 | 约束 |
|------|------|
| 封面 | 一个强标题 + 副标题，最多 2-3 个辅助标签 |
| 目录 | 不超过 5 个章节 |
| 内容页 | 3-5 个信息块，禁止长段落 |
| 数据页 | 突出一个主数字/主判断，图表只服务这个判断 |
| 流程页 | 步骤 ≤ 6 个，连接关系清晰 |
| 对比页 | 左右结构或表格结构明确 |
| 收尾页 | 总结或下一步，不写"谢谢" |

### 字号建议
| 元素 | 字号 |
|------|------|
| 封面标题 | 44-64 pt |
| 页面标题 | 28-40 pt |
| 章节标题 | 36-52 pt |
| 正文 | 18-24 pt（投影场景低于 16pt 不可读） |
| 注释/标签 | 12-16 pt，谨慎使用 |

### 内容压缩
- 不机械搬运原文，每页 1 个标题观点 + 2-5 个要点 + 1 个主视觉
- 长材料放入演讲者备注或拆页

### 视觉校验清单
- 页面主次明确
- 标题和正文对齐
- 文本无溢出
- 元素无重叠
- 边距足够
- 颜色对比可读
- 同级元素大小一致
- 页间风格统一
- 无无意义装饰
- 无元信息/生成过程

---

## 飞书 Slides 前提检查

选择飞书 Slides 输出前，检查 lark-cli 在线生成能力：

```bash
# 1. lark-cli 是否可用
which lark-cli 2>/dev/null || (echo "lark-cli 未安装，降级为 PPTX" && exit 1)

# 2. auth 是否有效
export LARKSUITE_CLI_CONFIG_DIR="${LARKSUITE_CLI_CONFIG_DIR:-$HOME/.lark-cli}" && export PATH="$HOME/.local/bin:$PATH"
lark-cli drive +search --query test --page-size 1 --as user 2>&1 | sed '/^\[lark-cli\]/d' | grep -q '"ok":true' || (
  echo "lark-cli auth 过期。降级为 PPTX"
  exit 1
)

# 3. 飞书 Slides API 是否支持在线创建
lark-cli --version | grep -qE 'slides|3\.' && echo "✅ 支持飞书 Slides" || echo "⚠️ 当前版本可能不支持 slides，将尝试"
```

检查失败则仅输出 PPTX，并说明阻塞原因。

---

## 与 fdiagram 协作

图表委托 `fdiagram` 生成：

```
fpptx 判断"这页需要图表"
  → 输出 Mermaid 描述或数据给 fdiagram
  → fdiagram 生成可编辑 SVG
  → SVG 嵌入 slide（OfficeCLI: --prop src=/path/to/diagram.svg）
  → fdiagram 负责 SVG 视觉样式（配色匹配当前主题）
```

- 架构/流程/时序/ER/类/状态/甘特图 → `fdiagram` Mermaid 模式
- 数据图表（柱状/折线/饼图）→ `fdiagram` SVG 或 OfficeCLI chart
- 白板/示意图 → `fdiagram` whiteboard-cli

---

## OfficeCLI 引擎

### 核心命令
```bash
officecli create deck.pptx
officecli open deck.pptx
officecli add deck.pptx / --type slide --prop title="标题" --prop text="副标题" --prop background=#1E2761
officecli add deck.pptx "/slide[1]" --type shape \
  --prop text="关键指标" --prop font=Georgia --prop size=36 --prop bold=true \
  --prop color=#FFFFFF --prop fill=#4472C4 --prop preset=roundRect \
  --prop x=2cm --prop y=4cm --prop width=12cm --prop height=3cm
officecli batch deck.pptx --input deck_commands.json
officecli close deck.pptx && officecli validate deck.pptx && ls -lh deck.pptx
officecli query deck.pptx slide --json
officecli get deck.pptx "/slide[1]" --depth 1 --json
```

### 批量模式示例
```json
[
  {"command": "add", "parent": "/", "type": "slide", "props": {"title": "封面", "text": "副标题", "background": "#1E2761"}},
  {"command": "add", "parent": "/", "type": "slide", "props": {"title": "内容页", "text": "正文内容"}},
  {"command": "add", "parent": "/slide[2]", "type": "shape", "props": {"text": "要点1"}}
]
```

### 模板合并
```bash
officecli create template.pptx
officecli add template.pptx / --type slide --prop title="{{title}}" --prop text="{{subtitle}}"
officecli merge template.pptx output.pptx --data '{"title":"Q4报告","subtitle":"营收增长18%"}'
```

---

## 设计系统

### 6 套设计主题

| 主题 | 主色 | 辅色 | 强调色 | 正文 | 适用场景 |
|------|------|------|--------|------|---------|
| Midnight Executive | `1E2761` | `CADCFC` | `FFFFFF` | `333333` | 金融、高管报告 |
| Coral Energy | `F96167` | `F9E795` | `2F3C7E` | `333333` | 产品发布、营销 |
| Forest & Moss | `2C5F2D` | `97BC62` | `F5F5F5` | `2D2D2D` | 可持续、ESG |
| Charcoal Minimal | `36454F` | `F2F2F2` | `212121` | `333333` | 极简企业风 |
| Ocean Gradient | `065A82` | `1C7293` | `21295C` | `2B3A4E` | 科技、数据 |
| Academic Navy | `1E3A5F` | `E8EDF2` | `C4A35A` | `2D2D2D` | 学术、备考 |

选择策略：封面/章节/收尾页用大胆主题，信息密集页用克制/均衡主题。全套 deck 风格统一。

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
- 边距 ≥ 1.27cm，卡片间距 ≥ 0.76cm
- 3 卡布局：`col = (33.87 - 3 - 1.52) / 3 = 9.78cm`

---

## QA 检查清单

```bash
officecli validate deck.pptx                      # Schema 验证
officecli view deck.pptx issues                    # 溢出/格式问题
officecli view deck.pptx text | grep -iE 'xxxx|lorem|<todo>'  # 占位符残留
officecli query deck.pptx 'picture:no-alt'         # 缺 alt 文本的图片
```

---

# 飞书 Slides API 操作

## PPTX → 飞书 Slides（已验证 ✅）

```bash
# 本地 PPTX 直接导入为飞书在线 Slides
lark-cli drive +import --file ./deck.pptx --type slides --name "标题" --as user

# 挂到 wiki 节点下（import 的 folder-token 只收 Drive folder token，用 shortcut 挂 wiki）
lark-cli wiki +node-create --node-type shortcut --obj-type slides \
  --origin-node-token <slide_token> --parent-node-token <wiki_parent> --title "标题" --as user
```

已验证：PPTX 导入 Slides 后 **图片完整保留**（`<img>` 引用 file_token），页数/顺序/文本全部保留。

## 其他可行操作

| 操作 | 命令 |
|------|------|
| 读完整 PPT XML | `lark-cli slides +xml-get --presentation <id> --as user` |
| 新建空 PPT | `lark-cli slides +create --title "<name>" --as user` |
| 新建页 | `lark-cli slides +add-slide --presentation <id> --slide @page.xml --as user` |
| 替换整页 | `lark-cli slides +replace-slide --presentation <id> --slide-id <sid> --slide @page.xml --as user` |
| PPTX 上传为 wiki 子文件 | `lark-cli drive +upload --file ./out.pptx --wiki-token <token> --as user` |
| 上传图片到 Slides | `lark-cli slides +media-upload --presentation <id> --image @./img.png --as user` |

## 从飞书文档提取图片（已验证 ✅）

飞书文档（docx）中的图片可无损下载原图：

```bash
# 1. 读文档 XML 拿图片 block 的 src token
lark-cli docs +fetch --doc <doc_token> --doc-format xml --detail full --as user \
  | grep -oE '<img[^>]*src="[^"]+"'

# 2. 用 src token 下载原图（无损，原分辨率，scale=1.0）
lark-cli docs +media-download --token <src_token> --type media --output ./img.png --as user
```

**已验证结论**：文档图片以原始 PNG 下载（如 2400×1100 原图），嵌入 PPTX 后内嵌字节与原图**逐字节一致**（无损），飞书 Slides 同样完整保留。

---

## OfficeCLI 注意事项

1. **文件锁定**：`close` 后残留进程会锁文件，重建前 `pkill -9 officecli`
2. **批量输入**：用 `--input file.json` 而非 `--commands "$(...)"`
3. **表格数据**：`data="H1,H2;R1,R2"`（分号分行，逗号分列）
4. **图表数据**：`series1.name=... series1.values="1,2,3"`
5. **路径引用**：zsh/bash 必须引号 `"/slide[1]"`
6. **`$` 符号**：`--prop text='$15M'` 单引号
7. **close 失败保护**：`close && validate && ls -lh` 三连确认。close 失败→文件截断不可恢复
8. **形状 ID**：自定义形状从 `@id=10000` 起
9. **不支持属性**：`borderRadius` 不被 shape 支持；图表 `seriesX.color`/`legendPos` 不支持

### autofit 后处理
OfficeCLI 的 `autoFit=normal` 不带 `fontScale` 默认 100%（不缩小）。用 python-pptx 后处理：

```python
from pptx import Presentation
from pptx.oxml.ns import qn
from lxml import etree

prs = Presentation("output.pptx")
for slide in prs.slides:
    for shape in slide.shapes:
        if not shape.has_text_frame: continue
        bodyPr = shape.text_frame._txBody.find(qn('a:bodyPr'))
        for tag in [qn('a:normAutofit'), qn('a:spAutoFit'), qn('a:noAutofit')]:
            for el in bodyPr.findall(tag): bodyPr.remove(el)
        norm = etree.SubElement(bodyPr, qn('a:normAutofit'))
        norm.set('fontScale', '55000')
prs.save("output.pptx")
```

fontScale 取值：`80000`(80%) / `65000`(65%) / `55000`(55%, 推荐) / `40000`(40%)

### 大 deck 并行策略
50+ 页：按章节拆分→ subagent 并行写脚本→ 顺序执行。

---

## 内容规范委托

PPT 内容结构委托 `freportstd` 的 4 套模板：

| 模板 | 用途 | PPT 场景 |
|------|------|---------|
| research.md | 调研报告 | 调研结论类 PPT |
| analysis.md | 分析复盘 | 分析/复盘类 PPT |
| comparison.md | 对比选型 | 竞品对比类 PPT |
| proposal.md | 方案规划 | 方案/规划类 PPT |

每章 3 要素：数据支撑 + 因果链条 + 不确定项标注。

---

## 关联 Skills
- `ffeishu` — 编排层，统一入口，飞书上传/分发
- `fdiagram` — 图表生成（架构/流程/数据 SVG）
- `freportstd` — 内容结构模板
- `fsearch` — 素材搜索