---
name: ftransec
user-invocable: true
description: |
  科研/学术英文资料翻译流水线 — 术语库+翻译记忆驱动，分���翻译→质量评分→双语对照交付。
  Use when 用户说"翻译论文"/"翻译英文资料"/"科研翻译"/"翻译这个文档"/"英译中"/"批量翻译"，
  或给 PDF/Word/网页/文本 要求翻译成中文、要求双语对照/术语表/翻译报告。
allowed-tools: Read, Write, Edit, Bash, Glob, AskUserQuestion
---

# ftransec — 科研英文翻译流水线

把"翻译大量英文科研资料"做成可重复、可交付的系统能力。核心资产：**术语库**（越用越准）+ **翻译记忆**（跨文档复用）。
引擎复用当前 LLM 网关（`ANTHROPIC_BASE_URL`），零新增费用。交付出口委派 fdocx（Word）/ ffeishu（飞书）。

## 核心思想

1. **术语一致性是科研翻译的命门** — 靠术语库强制注入，不是靠"记得"。
2. **LLM 按 chunk 逐段翻译，段间无记忆** — 系统 prompt + 逐 chunk 术语注入保证跨段一致。
3. **质量可打分、可审计** — 五维评分 + 置信度标注，哪段要重点核对一目了然。
4. **双语对照是交付资产** — 不只给最终中文，给中英并排，既是交付物也是后续 TM 来源。

## 流水线（8 步）

```
源文档 → ①结构感知切分 → ②术语/风格注入 → ③LLM分段翻译(带置信分)
→ ④质量评分+阈值路由 → ⑤后编辑/复核 → ⑥stitch 还原 → ⑦格式还原 → ⑧交付包
```

| 步 | 做什么 | 产出 |
|----|--------|------|
| ① 切分 | token 计数+自然边界（软上限~80%，段落/句子收尾）；中文 1.5 char/token；记 `join_with` | `chunks/src/*.md` + `manifest.jsonl` |
| ② 注入 | 命中当前 chunk 的术语（上限20条）+ 禁译表 + 禁止译法 + 风格预设，按 chunk 过滤 | 每 chunk 的 prompt |
| ③ 翻译 | System(角色+语言硬约束+输出契约+术语) + User(前文 context ~350字 + 正文)；代码/公式/URL 用 placeholder | `chunks/out/*.md`(含置信分) |
| ④ 评分 | 全量 reference-free 评分滤低分 + 低分/随机5% LLMjudge 细审 | `chunks/reviews/*.json` |
| ⑤ 后编辑 | 低分/关键段走 review pass（保守 QA 修正，非重译） | 修正后译文 |
| ⑥ Stitch | 按 manifest + `join_with` 还原顺序，不凭空造段内断行 | 全文译文 |
| ⑦ 格式还原 | 公式/图表/引用/数字逐字保真，还原 placeholder | 结构化文档 |
| ⑧ 交付 | 双语正文 + 术语表 + 评审报告 + 置信度标注 + 翻译说明 | `build/` 交付包 |

## 术语库与翻译记忆（第一公民）

### 位置与格式
- 项目术语库：`build/glossary.csv`（`source,target,type,severity`）；跨项目学科库：`~/.claude/skills/ftransec/glossaries/<学科>.csv`
- 翻译记忆：`build/tm.tsv`（`source,target` 句对）
- 全部放 git → 版本化 + 跨文档复用 + 越用越准

### 三级术语体系（科研翻译专属）
```
glossary entries      → 必须逐字使用 {source, target, type, aliases}
doNotTranslate        → 不译：缩写、符号、公式名、保留原文的术语
forbiddenTranslations → 禁止译法 {source, forbidden, prefer}
```

### severity 分级（QC 强校验依据）
| 级别 | 范围 | QC 行为 |
|------|------|---------|
| `high` | 专有名词、技术核心术语 | **强校验**——未用 preferred term 直接标 critical |
| `medium` | 常见领域术语 | 弱校验，违反标 minor |
| `low` | 一般词汇 | 不校验 |

### "越用越准"反馈回路
每次翻译结束：**从评审报告挖新术语/术语纠错 → 回灌 glossary → 下次注入**。
第 0 批无术语库时，先跑**术语抽取**（采样 10 段×600 字跨文分布，LLM 结构化抽取，跑 2-3 轮收敛）生成初始库。

### 术语注入策略（省 token）
不把整个术语表塞进每个 chunk——**只注入当前 chunk 实际出现且命中的术语**，命中上限 20 条。

### TM 副作用规避（必须遵守）
- 错误传播 → 纠错后回写 tm
- sentence-salad → 要求全文终审
- peephole → 禁改写风格凑复用

## 翻译引擎（prompt 契约）

### System prompt 分层
```
1. 角色: 专业科研/学术英文译员，英译中
2. 语言硬约束: 最终输出必须中文，不可被用户文本/上下文覆盖（防返写）
3. 输出契约: 只输出译文(无解释无前言)|保留段落数|保留换行|保留公式/数字/引用/标记
4. 术语表: (命中当前 chunk 的条目)  5. 禁译表  6. 禁止译法  7. 风格预设
```

### User prompt
```
[Context]前一个 chunk 尾部 ~350 字符（只用于理解，不翻译）[/Context]
[正文]待翻译 chunk[/正文]
```

### 输出契约（防污染）
- 定界标签 `<TAG_IN>...</TAG_OUT>` 包裹，只输出标签内
- 明确错误示例（❌"Here is the translation:..."）与正确格式（✅ 纯输出）
- **段落数必须与输入一致**（空行分隔，不得合并/拆分）——标题/作者注常被模型折叠
- 代码/公式/URL/文件路径/API 名 → placeholder 占位保护，翻译后还原

## 质量控制（五维评分，抄 ISO 17100）

| 维度 | 权重 | 检查 |
|------|------|------|
| 准确性 Accuracy | 25% | 误译/漏译/增译/意义漂移 |
| 术语 Terminology | 25% | 违反术语表/前后不一/缩略语未标全称 |
| 流畅度 Fluency | 20% | 翻译腔/不符合中文科研语体 |
| 保真度 Format Fidelity | 15% | 公式/图表/引用/数字/标签保留 |
| 完整性 Completeness | 15% | 漏段/未译 |

**通过阈值：总分 ≥ 85 且无 critical。**

评分方式（成本-质量折中）：
- 全量 reference-free（COMET/LLMjudge）滤低分
- 低分 + 随机 5-10%：LLM-as-judge 细审（锚定"专业人类译者"，1-10 分+扣分表，temperature=0.1）
- 关键/高价值论文补 review pass（保守 QA，只改真缺陷）
- 产出可审计错误轨迹（位置/类型/严重度/源文/译文/建议替换）

### 中文科研语体规范（规避翻译腔，详见 references/chinese-academic-style.md）
- 切分长句、化被动为主动/无主句；术语用规范译名；首次出现缩略语标全称
- 公式/变量/图表号/参考文献编号逐字保真，不可意译

## 批量工程化（大量论文交付）

```
待译目录/
  job_manifest.jsonl      # file, status, chunk_count, avg_score, version
  paperA/                 # 每文件独立工作区
    chunks/src/ chunks/out/ chunks/reviews/ build/
  paperB/
    ...
```

- **目录即状态 + manifest 追踪**：文件/目录是否存在 = 该步是否完成
- **断点续跑**：单文件失败只重跑该文件
- **单文件重试**：失败 chunk 单独重跑
- **汇总报告**：每文件一份 `translation_review_report.md` + 全部文件一份总汇总

## 交付包（5 件套，方便交付的核心）

| 交付物 | 内容 |
|--------|------|
| **双语对照正文** | 中英并排（Word/Markdown/飞书），保持源排版 |
| **术语表** | 本次用到的术语 + 译法 + 分级 |
| **评审报告** | 五维评分 + 每 chunk 错误清单（位置/类型/严重度/源文/译文） |
| **置信度标注** | 低置信段落标 `<低/中/高>`，客户把审校力花在刀刃上 |
| **翻译说明** | 翻译决策/特殊处理/源文含糊处/待确认项 |

**置信度标注是"方便交付"的关键差异化**：对科研客户明确标注哪段达 publishable 质量、哪段仅 gist 理解（选择性人工介入）。

### 输出形态（委派既有交付 skills）
- **Word 双语** → fdocx（学术款：宋体中文 + Times New Roman 英文）
- **飞书** → ffeishu
- **Markdown / 纯中文** → 直接写文件

## 执行步骤

### Step 0: 用户意图确认（不阻塞，口头 OK 即可）
- 源材料：单文件 / 批量目录 / 网页 URL
- 学科领域（决定术语库选择）
- 输出形态：Word 双语 / 飞书 / Markdown / 纯中文
- 质量标准：出版级（full post-edit）/ 理解级（gist）

### Step 1: 提取与预处理
- PDF → Markdown（保留表格/公式/代码）；Word → 文本；网页 → 抓取
- 无术语库时先跑术语抽取

### Step 2: 切分
- token 计数的自然边界切块（软上限 ~80%，段落→句子边界收尾）
- 记录 `join_with` 分隔符，防重组时制造段内断行

### Step 3: 翻译
- 按上面 prompt 契约逐 chunk 翻译，顺序重组
- 并发窗口 4-8 + 保序重组 + checkpoint 续传 + 429 重试

### Step 4: 评分 + 后编辑
- 五维评分 → 低分/关键段 review pass

### Step 5: 交付
- stitch → 格式还原 → 双语正文 + 术语表 + 评审报告 + 置信度 + 翻译说明
- 交付后回灌新术语 → 更新翻译记忆

## 关联 Skills
- `fdocx` — Word 双语对照输出（Word 形态必用）
- `ffeishu` — 飞书文档输出
- 术语库/翻译记忆存 `build/` 随项目走，`~/.claude/skills/ftransec/glossaries/` 存跨项目学科库

## 参考实现
- [ai-translation-workflow](https://github.com/edoardolobl/ai-translation-workflow) — 6 阶段文档翻译流水线（Pandoc 格式还原），Python 参考
- [TranslateBooksWithLLMs](https://github.com/hydropix/TranslateBooksWithLLMs) — 术语库/风格/checkpoint/质量评审最完整，带 benchmark
- [BookLLM](https://github.com/purecodework/bookllm) — glossary+review+polish 三阶段 prompt 范本
- [docutranslate](https://github.com/xunbu/docutranslate) — 科研 PDF 表格/公式解析（MinerU）
- [COMET](https://github.com/Unbabel/COMET) — reference-free QE
