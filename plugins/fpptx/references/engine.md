# OfficeCLI 引擎、设计系统与 Slides 操作

> OfficeCLI 命令、6 套设计主题、QA 清单、PPTX→飞书 Slides 流程、注意事项在此。
> 设计主题与 fdocx/fxlsx 共享同一套（各自参数略有差异）。

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

# 注：PPTX import 到 drive 后再挂 wiki 需 shortcut；但新流程直接用 wiki +node-create --obj-type slides 在父 wiki 下 origin 创建，无需 import
lark-cli wiki +node-create --obj-type slides --parent-node-token <wiki父节点> --title "标题" --as user
# → 返回 node_token + obj_token（obj_token 即 xml_presentation_id），随后 +add-slide 逐页添加
```

已验证：PPTX 导入 Slides 后 **图片完整保留**（`<img>` 引用 file_token），页数/顺序/文本全部保留。

## 其他可行操作

| 操作 | 命令 |
|------|------|
| 读完整 PPT XML | `lark-cli slides +xml-get --presentation <id> --as user` |
| 新建空 PPT | `lark-cli slides +create --title "<name>" --as user` |
| 新建页 | `lark-cli slides +add-slide --presentation <id> --slide @page.xml --as user` |
| 替换整页 | `lark-cli slides +replace-slide --presentation <id> --slide-id <sid> --slide @page.xml --as user` |
| 父 wiki 下创建 origin slides | `lark-cli wiki +node-create --obj-type slides --parent-node-token <父节点> --title ... --as user` |
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
