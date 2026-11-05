---
name: fpptx
user-invocable: true
description: |
  PPT/X 总控 — 从 md/wiki/材料到 PPTX 或飞书 Slides。
  OfficeCLI 引擎（原生 OpenXML），也支持 lark-cli 生成飞书在线幻灯片。
  内置 6 套设计主题，图表委托 fdiagram，内容规范委托 fstander-report。
allowed-tools: Read, Write, Bash, Glob
---

# fpptx — PPT / 飞书幻灯片生成

从材料文档/会议纪要/调研资料/方案草稿/主题大纲生成正规演示文稿。
输出前**问用户**：PPTX 文件 / 飞书在线 Slides / 都要。

图表委托 `fdiagram` 生成可编辑 SVG 嵌入。

## 配置

**独立用户**：OfficeCLI 免费安装即可（`curl -fsSL https://d.officecli.ai/install.sh | bash`），
无需额外配置。**ccconfig 用户**：真值在 `<ccprivate>/conf/fpptx.yaml`，`sync` 自动接上。

⚠️ OfficeCLI 是 .NET 应用，依赖 libicu，缺库报 `Couldn't find a valid ICU package`。
装 `libicu78`（Ubuntu 26.04；其他版本 `apt-cache search libicu`）。无 sudo 可用
`DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1` 绕过。

## 执行流程

| 步 | 做什么 |
|---|---|
| 1 判模式 | 有材料 → 材料模式；只说"演示一下" → 演示兜底 9 页默认 deck |
| 2 分析材料 | 提取受众、目的、核心观点、关键论据、章节结构、必须保留的名词和数字 |
| 3 规划叙事 | 默认 8-12 页。每页：页标题 + 单一核心信息 + 页型 + 模板主题 |
| 4 选风格 | 6 套主题选 1-2 套成风格家族（封面/章节/收尾用大胆的，内容页用克制的） |
| 5 生成 | 图表委托 fdiagram 出 SVG；正文用 OfficeCLI 原生元素；**禁止整页截图**，禁止把提示词/模板名/生成过程写进页面 |
| 6 校验 | 逐页查：文字溢出、元素重叠、字号可读、边距、颜色对比、风格统一 |
| 7 输出 | **默认飞书在线 Slides**；PPTX 为备选（用户明确要本地文件时） |
| 8 交付 | 飞书：`wiki +node-create --obj-type slides` → `+add-slide` 逐页 → 返回链接；PPTX：`close && validate && ls -lh` 三连 → 文件路径 |

## 飞书 Slides 前提检查

选择飞书 Slides 输出前先确认可用性：

```bash
~/.claude/skills/fcore/bin/fcore auth || (
  echo "lark-cli 不可用或未授权 → 降级为本地 PPTX"
  exit 1
)
```

不可用时**降级为 OfficeCLI PPTX 并说明原因**，不要卡住。

## 委托边界

| 需求 | 走哪 |
|---|---|
| 内容结构（章节骨架/论证） | `fstander-report` 4 套模板 |
| 图表（架构/流程/数据） | `fdiagram` → 可编辑 SVG 再嵌入 |
| 素材搜索 | `fsearch` |
| 交付与飞书上传 | `fcore doc` / `ffeishu` |
| PPTX 引擎命令 | 本 skill（`references/engine.md`） |

## 参考

| 文件 | 内容 |
|---|---|
| `references/design.md` | 演示兜底 + PPT 设计规则（版式/字号/内容压缩/校验清单） |
| `references/engine.md` | OfficeCLI 命令、6 套设计主题、QA、Slides 操作、9 条注意事项、autofit 后处理 |
| `references/lark-slides.md` | 飞书 Slides 能力检查、fdiagram 协作细节 |
