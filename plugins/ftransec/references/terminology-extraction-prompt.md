# 术语抽取 Prompt 模板（批量论文，无术语库起步）

> 来源：深度调研 [B] — TBL/BookLLM 的 LLM 结构化抽取。跑 2-3 轮（每轮采样不同片段）直至收敛。

## 用法
1. 从待译文档采样 10 段 × 600 字，跨全文分布。
2. 用下方 prompt 让 LLM 结构化抽取，输出 JSON。
3. 已有术语标 `(already in glossary)` 跳过去重；合并去重后入库 `glossary.csv`。

## System prompt
```
你是科研文献术语抽取引擎。从给定的英文论文片段中提取对所有翻译质量影响最大的专业术语与专有名词。
只输出 JSON，无其他文字。
```

## 输出契约（JSON Schema 语义）
```json
{
  "version": 2,
  "entries": [
    {
      "source": "CRISPR-Cas9",
      "target": "CRISPR-Cas9 基因编辑系统",
      "type": "term",
      "aliases": ["CRISPR", "Cas9"],
      "description": "基因组编辑技术",
      "severity": "high"
    }
  ],
  "doNotTranslate": ["DNA", "RNA", "PCR"],
  "forbiddenTranslations": [
    {"source": "evidence-based", "forbidden": "基于证据的", "prefer": "循证的"}
  ]
}
```

## 决策规则
- **type**: `term`（领域术语）/ `org`（机构）/ `place`（地点）/ `person`（人名）
- **severity**: `high`（专名、技术核心术语，QC 强校验）/ `medium`（常见领域术语）/ `low`（一般词汇）
- **doNotTranslate**: 缩写、符号、公式名、保留原文的术语
- **forbiddenTranslations**: 明确禁止的误译
- 只抽"低歧义、高特异性"的术语，宁缺毋滥
