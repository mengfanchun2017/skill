# fworch-case 通信契约

> 通用编排器契约 → `fworch/references/orchestrator-contract.md`（统一返回格式 / 真相源 / 进度）。
> 本文件只列案例线专属补充。

## 案例线进度

- **无本地进度 yaml**：真值 = 飞书 Base 记录 + wiki 三层，注册表真值在 `ccprivate/conf/writing/case.yaml`。
- 新增/更新案例后回填 Base 即完成，无独立进度文件。

## 返回（检索与建库两种）

**检索**（被 fworch-course 等调用）：

```yaml
query: "RFM"
professional: "个性化推荐"
chunks:
  - id: "case-001"
    title: "Starbucks-RFM与客户分层-忠诚度"
    summary: "..."
    url: "https://<tenant>.feishu.cn/wiki/xxxx"
    record_id: "recXXX"
```

**建库**（新增/更新案例）：

```yaml
status: "ok"
doc_url: "https://<tenant>.feishu.cn/wiki/<主文档 node>"
aux_docs:
  - url: "https://<tenant>.feishu.cn/wiki/<子文档 node>"
    purpose: "figure"            # 第3层子文档
notes:
  - "Base 记录已回填 recXXXX；编号 auto_number 自动生成"
```
