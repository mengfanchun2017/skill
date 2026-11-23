---
name: fresmethod
user-invocable: true
description: |
  研究维度方法论 — 按调研主题自动判断维度（customer / generic / market / technical），
  委派 fsearch 收集数据，再按对应维度框架（references/frame-*.md）解读输出。
  4 个维度是稳定的研究视角，不常变；新增维度 = 加 references/frame-<name>.md + 判断表一行。
  搜索工具调用委派 fsearch，本 skill 不直接调 API。
  用法：用户说"调研 XX"/"研究 XX"/"分析 XX 用户"/"市场趋势"时触发。
allowed-tools: Read, Write, Glob, Bash, AskUserQuestion
---

# fresmethod — 研究维度方法论

收到调研主题 → 判断维度 → 委派 `fsearch` 收集数据 → 读对应 `references/frame-<维度>.md` → 按框架解读输出。

**本 skill 不直接调搜索 API**，搜索一律委派 fsearch。

## 何时用

| 触发 | 行为 |
|------|------|
| "调研 XX" / "研究 XX" / "分析 XX 用户" | 判断维度 → 派 fsearch → 按框架解读 |
| forch-report 需要调研素材 | 委派本 skill（不在模式 1 中直接调 fsearch） |
| Batch Mode（批量研究） | 委派本 skill 做单 item 的维度判断 + 框架 |

## 维度判断

| 维度 | 触发关键词 | 框架文件 |
|------|-----------|----------|
| `generic` | 调研/研究/分析/对比 | `references/frame-generic.md` |
| `customer` | 用户/客户/竞品/JTBD/饮水点 | `references/frame-customer.md` |
| `market` | 市场/TAM/份额/趋势 | `references/frame-market.md` |
| `technical` | 技术/框架/库/选型 | `references/frame-technical.md` |

- 拿不准用 `generic`
- **新增维度**：加 `references/frame-<name>.md`，再在上表加一行即可（维度稳定、变化慢，通常只扩不删）

## 流程

### Step 1: 判断维度
按上表关键词判断；拿不准用 `generic`。

### Step 2: 委派 fsearch 收集数据
调 fsearch 收集数据（中英语言路由 + 额度耗尽 fallback），拿回搜索结果 + 搜索清单。

### Step 3: 读框架并解读
读对应 `references/frame-<维度>.md`，按该框架的字段/镜头/提取步骤处理数据。

### Step 4: 输出
输出结构化维度数据 + 置信度标注，交给调用方（forch-report / Batch Mode / 用户）。

## 输出契约

- 字段结构按对应框架文件
- 附置信度：High / Medium / Low（判定规则见 `frame-customer.md`）
- 附 fsearch 产出的搜索清单（调用方决定是否附加）

## Batch Mode（原 f-research-deep）

批量研究模式，用于 outline.yaml 驱动的多项研究。

### 流程

1. 定位当前工作目录下的 `*/outline.yaml`
2. 检查 `output_dir` 中已完成的 JSON，跳过已完成 items
3. 每批 `batch_size` 个 items（默认 3），逐个调用本 skill 的维度判断 + 搜索流程
4. 输出到 `{output_dir}/{item_name_slug}.json`

### JSON 结构

```json
{
  "name": "...",
  "domain": "generic|customer|market|technical",
  "_sources": ["[tavily] ...", "[exa] ...", "[websearch] ..."],
  "_confidence": "High|Medium|Low",
  "uncertain": []
}
```

> `_domain`/`_confidence`/`_sources` 是 Batch Mode 的 JSON 键名，保持兼容；其余字段按框架文件。

### 验证

完成后检查每个 JSON 的字段覆盖完整性。

## 关联 Skills

- `fsearch` — 搜索原语（必调用）
- `forch-report` — 报告生成（用本 skill 输出做素材）
- `flogme` / `ffeishu` — 行业调研 / 文档调研
