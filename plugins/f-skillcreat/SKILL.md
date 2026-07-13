---
name: f-skillcreat
description: Skill 写作参考手册 — 从 invocation 选择到信息层级到常见失败模式，让 skill 行为可预测。
disable-model-invocation: true
---

Skill 的本质是给随机系统注入确定性。**Predictability** — agent 每次走同样的_process_，不是产出同样的_output — 是根美德；所有其他 lever 都服务于它。

**Bold terms** 的定义见 [`GLOSSARY.md`](GLOSSARY.md)。

## Invocation

两个选择，花不同的成本：

- **Model-invoked** skill 保留 **description**，agent 可自动触发、其他 skill 可引用。代价是 **context load** — description 每轮都占窗口。做法：不加 `disable-model-invocation`，写 model-facing description 配丰富触发词。
- **User-invoked** skill 去掉 description，只有用户输入名字才能触发，其他 skill 也无法引用。零 context load，但花 **cognitive load**：你得记住它存在。做法：设 `disable-model-invocation: true`。

只在 agent 必须自主触达时才用 model-invoked。只在手动调用时用 user-invoked。

当 user-invoked skill 多到记不住时，用 **router skill**：一个 user-invoked skill 列出所有其他的及何时用。

## Writing the description

Model-invoked **description** 两件事：说明 skill 做什么 + 列出触发 **branches**。每个词都增加 context load：

- **Leading word 前置** — description 是它做 invocation 工作的地方。
- **一个 branch 一个 trigger。** 同义词重命名同一 branch = duplication。
- **去掉已在 body 里的身份信息。** description 只留 triggers + "其他 skill 需要时可达" 的 reach clause。

## Information hierarchy

Skill 由两种内容组成 — **steps** 和 **reference** — 自由混合。核心决策：哪种内容放在信息层级的哪一层：

1. **In-skill step** — 有序动作，primary tier。每步以 **completion criterion** 结尾，告诉 agent 工作做完的条件。要 _checkable_（agent 能判断做完/没做完），重要的地方要 _exhaustive_（"每个修改过的 model 都计入"而非"产出变更列表"）。
2. **In-skill reference** — 定义、规则、事实，按需查阅。经常是平级集合（review 的每条规则同层）— 合理的安排，不是 smell。
3. **External reference** — 推到 SKILL.md 之外，通过 **context pointer** 触达。分 disclosed reference（同目录文件，仍属 skill）和 fully external reference（skill 系统之外）。

一个 demanding completion criterion 驱动 thorough **legwork** — agent 在步骤内做的挖掘工作 — 无论 skill 有没 steps。

**Progressive disclosure** 是沿层级下移 — 移出 SKILL.md 到链接文件 — 让顶层可读。**Branching** 是最干净的 disclosure 测试：inline 所有 branch 都需要的东西，只把某些 branch 用到的推到 pointer 后面。**Context pointer** 的 _措辞_，不是目标，决定 agent 何时及多可靠地触达材料。

**Co-location**：同一概念的定义、规则、caveats 放在同一标题下，不散落各处。

## When to split

**Granularity** 是 skill 拆分粒度。每次切分花一种 load，只在值得时才切：

- **By invocation** — 有独立的 **leading word** 需要自触发，或其他 skill 需要引用时，分出 model-invoked skill。付出 context load，独立可达性必须值得。
- **By sequence** — 当前 step 的 **post-completion steps** 诱惑 agent 匆忙完成当前步时，隐藏后续 steps。切走它们让 agent 在当前位置做更多 legwork。

## Pruning

保持每个含义在 **single source of truth**：一个权威位置，改行为是一处编辑。

检查每行 **relevance**：它是否仍影响 skill 的功能？

然后 hunting **no-ops** 逐句：每个句子独立做 no-op 测试，失败时删整句而非修剪词。激进 — 大部分没通过的 prose 应该删掉，不是重写。

## Leading words

**Leading word** 是一个已存在模型预训练中的紧凑概念（如 _lesson_, _fog of war_, _tracer bullets_），agent 在运行 skill 时用这个概念思考。贯穿全文重复，累积分布式定义，用最少 token 锚定一整块行为。

两次服务于 predictability。Body 里锚定 _execution_：agent 每次遇到这个词都走到相同行为。Description 里锚定 _invocation_：当同一个词出现在你的 prompts、docs、code 里，agent 链接共享语言到 skill，触发更可靠。

找机会用 leading words 重构 skill。三个地方拼出来的 triad（duplication）、一个 description 句子指着一个概念 — 每个都是 collapse 成单个 token 的机会：

- "fast, deterministic, low-overhead" → _tight_
- "你相信能过测的循环" → _green_ / _red_

赢两次：更少 token，更锋利的 hook。假设每个 skill 都有 leading words 能消掉的 restatements — 去找。

## Failure modes

诊断用户可能遇到的 skill 问题：

- **Premature completion** — 步骤没真完成就结束。防御依次：先 sharpen completion criterion（便宜、局部）；只在 bound 不可约模糊 _且_ 真观察到 rush 时，才 hide post-completion steps。
- **Duplication** — 同一含义在多处。花维护成本 + token，膨胀 prominence。
- **Sediment** — stale layers 堆叠因为 add 感觉安全 remove 感觉危险。无 pruning 纪律时的默认命运。
- **Sprawl** — skill 就是太长，即使每行都 live 且唯一。伤可读性、可维护性、浪费 token。疗法：沿层级下移 reference、split by branch。
- **No-op** — model 默认就会的行。测试：改行为了吗？弱 leading word（_be thorough_ 当 agent 已默认 thorough）是 no-op；fix 是更强的 word（_relentless_），不是换技术。
- **Negation** — 禁止式引导回火：_don't think of an elephant_ 把 elephant 放进来了。治好：prompt **positive** — 描述目标行为让被禁的从未出现。只在无法正面表达时保留禁止，且必须配正面替代。
