# 质量评分 Rubric（LLM-as-judge，科研翻译）

> 来源：深度调研 [B/D] — TBL JUDGE_RUBRIC_V2 + ISO 17100 五维。temperature=0.1，输出长度约束 ≤200 字符。

## 五维评分（ISO 17100 权重）
| 维度 | 权重 | 检查 |
|------|------|------|
| 准确性 Accuracy | 25% | 误译/漏译/增译/意义漂移 |
| 术语 Terminology | 25% | 违反术语表/前后不一/缩略语未标全称 |
| 流畅度 Fluency | 20% | 翻译腔/不符合中文科研语体（见 chinese-academic-style.md）|
| 保真度 Format Fidelity | 15% | 公式/图表/引用/数字/标签保留 |
| 完整性 Completeness | 15% | 漏段/未译 |

**通过：总分 ≥ 85 且无 critical。**

## Judge system prompt
```
你是资深科研翻译质检员。比较源文本与译文，按五维评分。
锚定"专业人类译者"为参照，每维 1-10 分，用扣分法从 10 起逐项扣。
只输出 JSON，无其他文字。
```

## 扣分表（从 10 起）
| 问题 | 扣分 |
|------|------|
| 关键句反义（误译为相反意思） | -2.0 |
| 虚构事实/幻觉 | -2.0 |
| 源语言词未译（非专名） | -1.5 |
| 专名/专业术语错误 | -0.5 ~ -1.0 |
| 机器味僵译 | -0.5 ~ -1.0 |
| 轻微漏译细节 | -0.5 |

## 硬约束
- `accuracy < 6` → `overall ≤ 6`（准确性是底线）
- 无参考译文时 overall 硬上限 9.0
- 每 50 次重测校准一次评分稳定性

## 输出 JSON
```json
{
  "scores": {"accuracy": 8, "terminology": 8, "fluency": 7, "fidelity": 9, "completeness": 8},
  "overall": 8.0,
  "critical": [],
  "errors": [
    {"type": "terminology", "severity": "minor",
     "description": "Preferred term not used",
     "location": "chunk 7 para 2",
     "source": "climate change",
     "translation": "气候变化",
     "suggested_fix": "气候变迁"}
  ],
  "feedback": "术语一处前后不一 (−1.0); register 略塌 (−1.0)"
}
```
