# fworch-case 调用协议

fworch-course 子 skill 调 fworch-case 注入案例的契约。

> **字段来源**：`professional` 参数 = 飞书 Base caselib 多维表的「专业领域」字段枚举（**非**本地 YAML，案例库已全量迁飞书 Base，详见 fworch-case SKILL.md 迁移记录）。
> 课程配置 `caselib_direction` 字段名保持不变，值取 Base「专业领域」单选枚举。

## 调用

子 skill 持有 `caselib_direction: [str]`（来自课程配置，可选，限定案例专业领域），按需调用：

```
fworch-case(query=<当前章主题关键词>, professional=<可选专业领域>)
```

- `professional` = Base 的「专业领域」字段枚举（数字转型/客户细分/个性化推荐/预测性维护/增长策略/运营效率/风险管理/数字化营销/供应链/组织管理/其他），单选。
- 调用方不确定专业领域时可省略 `professional`，fworch-case 全局检索。

## 返回

fworch-case 返回：

```yaml
query: "RFM"
professional: "个性化推荐"
chunks:
  - id: "case-001"
    title: "Starbucks-RFM与客户分层-忠诚度"
    summary: "RFM 模型应用..."
    content: "..."       # 节选自案例主文档
    url: "..."           # 案例主文档 wiki url
    record_id: "recXXX"
  - id: "case-002"
    title: "..."
    summary: "..."
    content: "..."
```

## 注入策略

子 skill 在文档中插入时使用 `> [案例引用: <chunk.title>](<chunk.url>#<chunk.id>)` 格式，
保留可点击跳转到源案例的位置。

## 失败处理

- 无命中 → 子 skill 提示"该案例库无匹配内容"，不注入（不阻断主流程）
- chunk 数为 0 → 提示无匹配，跳过该案例
- auth/fetch 失败 → 警告，跳过案例不阻断

---
**迁移记录**：
- 2026-09-24：从 YAML 迁至飞书 Base，`slug` → `direction`。
- 2026-09-26：fworch-case 结构重构，「方向」字段改名「专业领域」并合并主题领域；调用参数改为 `professional`。课程配置 `caselib_direction` 语义 = 专业领域枚举，保持字段名不变。