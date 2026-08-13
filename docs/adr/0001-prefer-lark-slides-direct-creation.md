---
status: accepted
date: 2026-08-13
deciders: Francis Meng
---
# ADR-001: PPT 优先直接生成飞书在线 Slides，而非先制 PPTX 再上传

## 背景

fpptx skill 早期采用「OfficeCLI 生成 PPTX → 上传飞书 wiki」的流程。理由当时是：**直接 lark-cli 生成的飞书 PPT 不可编辑**，只能先做可编辑的 PPTX 文件，再上传。

2026-08 实测发现该前提已过时：`lark-cli slides +create / +add-slide` 已支持直接生成**原生可编辑**的飞书在线 Slides，且支持：
- `<img src="@./local.png">` 占位符自动上传图片（**最多 20MB**）
- 原生 `<chart>` / `<table>` / `<shape>` / `<icon>` 元素
- 完整 XML 排版控制（960×540 画布）

同时验证：飞书文档图片经 `docs +media-download` 下载原始 PNG（scale=1.0），嵌入 Slide 后**逐字节无损**。

## 决策

**生成 PPT 时优先直接创建飞书在线 Slides（lark-cli slides），PPTX 仅作为备选或交付给不需要在线编辑的场合。**

| 维度 | 飞书 Slides 直出 | PPTX + 上传 |
|------|-----------------|-------------|
| 可编辑性 | ✅ 原生元素，在线可改 | ✅ 但需重新导入 |
| 图片 | `<img src="@./path">` 自动上传，≤20MB | 逐字节无损，但多一步 |
| 交付链接 | 直接 `url` | wiki shortcut |
| 协作 | 在线实时协作 | 需导入 |

## 流程

```
写 PPT
  → fpptx 判断：优先 slides 直出（lark-cli slides +create/+add-slide）
  → 图片用 @ 占位符自动上传 或 +media-upload
  → 图表委托 fdiagram / 原生 <chart>
  → 回读验证 + 截图检查
  → 挂 wiki shortcut → 返回链接
```

## 后果

### 正向
- 交付物直接可编辑，无「先上传再导入」冗余
- 图片自动上传，无需手动管理 file_token
- 在线协作体验更好

### 代价
- Slides XML 语法较复杂（`<slide>` 根元素、无 ns 前缀），需严格遵循 lark-slides skill
- 图片上限 20MB（无法分片）
- `<chart>` 不支持漏斗/散点等复杂图

### 触发重估
- lark-cli slides API 行为变更
- 需要 20MB 以上大图嵌入
- 用户明确要求本地 .pptx 文件交付
