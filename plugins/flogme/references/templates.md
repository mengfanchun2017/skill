# flogme 内置模板

## 周期总结模板

```markdown
## {周期} {分类}总结（{时间范围}）

### OKR 达成
| O | KR | 状态 | 评分 |
|----|-----|------|------|
{从 OKR 表拉取}

### 核心成果
{从 Worklog 按成果类型分组，STAR 格式重写 top 5}
- 成果类型分布：项目交付 X 项 / 技术调研 Y 项 / 学习输入 Z 项

### 量化总览
- 总记录数：X
- 涉及 KR：Y 个
- 完成率：Z%

### 反思
{从 Reflect 提取关键洞察}

### 下阶段计划
{从 Reflect 的下阶段聚焦 + OKR 的下一周期目标}
```

## 领域总结模板

```markdown
## {年度} {领域} 专项总结

### 概述
{领域标签下的 worklog 总量、时间分布、KR 覆盖}

### 关键里程碑
{按时间线列出该领域最重要的 3-5 个成果}

### 能力积累
{从 Reflect 和 Worklog 的成果类型提取}

### 明年规划
{关联到该领域的下一年 OKR}
```

## OKR 复盘模板

```markdown
## {周期} OKR 复盘

### O1: {标题}
| KR | 类型 | 评分 | 备注 |
|----|------|------|------|
| KR1: xxx | Aspirational | 0.7 | |
| KR2: xxx | Committed | 1.0 | |

### 总体评估
- 平均评分：X
- Committed 达成率：Y%
- Aspirational 达成率：Z%

### 做得好的

### 待改进的

### 下周期调整
```

## 综合年报

年度综合报告由 `sum_generate.py --type annual` 程序化生成，结构见 `generate_annual_report()` 函数。
