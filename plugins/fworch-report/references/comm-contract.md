# forchreport 通信契约

> 通用编排器契约 → `fwriteorch/references/orchestrator-contract.md`（统一返回格式 / 真相源 / 进度）。
> 本文件只列报告线专属补充。

## 报告线进度

- **无本地进度 yaml**：进度以飞书文档为准，真值配置在 `ccprivate/conf/writing/report.yaml`。
- 分轮迭代（v1 → 评审 → v2）时，`aux_docs` 记录各版本 URL，`purpose` 用 `v1` / `v2` / `final`。

## 子产物

| 产物 | purpose | 说明 |
|------|---------|------|
| 报告卡片 | `card` | Step 0 前置确认清单 |
| 报告正文 | `doc_url` | 主产出 |
| 图子文档 | `figure` | 每图独立子文档（工作流 G） |

## 返回示例

```yaml
status: "ok"
doc_url: "https://<tenant>.feishu.cn/docx/xxxx"
aux_docs:
  - url: "https://<tenant>.feishu.cn/docx/fig1"
    purpose: "figure"
notes:
  - "3 图子文档已建并嵌入"
```
