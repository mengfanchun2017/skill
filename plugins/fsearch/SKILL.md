---
name: fsearch
user-invocable: true
description: |
  搜索活动统一原语 — 分语言路由搜索（中文→MiniMax、英文→Tavily，额度耗尽切 Exa）、
  聚合去重、来源标注、搜索清单输出。
  何时用本 skill 而非裸 Tavily/Exa MCP：需要①中英语言路由 ②额度耗尽自动 fallback
  ③聚合去重 ④来源标签 ⑤搜索清单 时；单源单次简单搜索可直接用 MCP。
  被 fresearchmethod / flogme / ffeishu 等需要外部调研的 skill 委托调用。
  不含研究维度方法论（解读由 fresearchmethod 负责）。
allowed-tools: Read, Write, Bash,
  mcp__tavily__tavily_search, mcp__tavily__tavily_research,
  mcp__tavily__tavily_extract, mcp__tavily__tavily_crawl, mcp__tavily__tavily_map,
  mcp__exa__web_search_exa, mcp__exa__web_fetch_exa,
  mcp__mineru__parse_documents
---

# fsearch — 搜索活动统一原语

query 规划（判语言选源）→ 主力搜索（额度耗尽切 Exa）→ extract 全文 → 聚合去重 → 来源标注 → 搜索清单输出

**不含研究维度方法论**（解读由 `fresearchmethod` 负责）。
实现细节（三源对比 / MiniMax 调用 / 提取流程 / 参数速查 / 去重代码 / 缓存）见 `references/search-internals.md`。

## 何时用（含与裸 MCP 的边界）

| 场景 | 走哪 |
|------|------|
| 单源、单次、简单搜索 | 直接用 Tavily / Exa MCP |
| 中英语言路由、额度耗尽自动 fallback | **fsearch** |
| 多源聚合去重 + 来源标签 + 搜索清单 | **fsearch** |
| 中文搜索（MiniMax REST，无 MCP schema） | **fsearch** |
| 任何 skill 需要外部调研 | 委派 fsearch |

| 触发 | 调用方 |
|------|--------|
| "调研 XX" / "搜 XX 资料" | 任何 skill / 用户直接调用 |
| fresearchmethod 调方法论前的数据收集 | fresearchmethod |
| flogme 行业调研 | flogme |
| ffeishu 文档调研 | ffeishu |

## 配置

- **Tavily / Exa**：通过 Claude Code 的 MCP 配置管理
  - **ccconfig 用户**：真实 key 放 `ccprivate/conf/claude.json`（symlink）
  - **独立用户**：`~/.claude/settings.json` 的 `mcpServers` 中配置 Tavily + Exa
- **MiniMax**：`ccprivate/conf/llm.json` 的 `llms.minimax31`（与 LLM 预设同一把 key，REST 直调，无需 MCP）

## 搜索策略预设

搜索分三层，调用方按需选择，**不是必跑所有层**：

| 策略 | 耗时 | 调用的源 | 适用场景 |
|------|------|---------|---------|
| `fsearch:fast` | ~1s | 主力源 fast/单源快速探查 | 快速事实确认、简单查询 |
| `fsearch:standard` | ~3s | 按语言路由的主力源（额度耗尽→Exa） | **默认**，大多数场景 |
| `fsearch:deep` | ~30-150s | standard → Tavily Research | 深度调研、报告型需求 |
| `fsearch:code` | ~3s | Tavily Search (advanced, 特定域名) → 耗尽切 Exa | 技术选型、代码库搜索 |
| `fsearch:news` | ~3s | Tavily Search (topic=news, time_range=week) → 耗尽切 Exa | 近期动态追踪 |

## 分语言路由（标准搜索核心）

标准搜索**按 query 语言选主力源，主力无额度时切 Exa 兜底**，不默认双源并行：

| query 语言 | 主力源 | 主力失败（额度耗尽/报错） |
|-----------|--------|--------------------------|
| 英文 | **Tavily Search** | → Exa Search |
| 中文 | **MiniMax 搜索**（REST） | → Exa Search |

- 判断依据是 query 主体语言；中英混合优先按中文路由（MiniMax 中文强），拿不准可两源都跑
- **Tavily 超限特征**：`exceeds your plan's set usage limit` → 本次及后续直接切 Exa
- **MiniMax 失败特征**：HTTP 非 200 / `base_resp.status_code != 0`（额度/鉴权）→ 切 Exa
- 执行后**必须逐条标注来源标签**：`[tavily]`、`[minimax]`、`[exa]`、`[tavily-research]`
- 调用细节与三源对比见 `references/search-internals.md`

## Tavily Research（深度综合）

**不是并行搜索源**，而是标准搜索后的按需步骤。

- **何时用**：标准搜索有效结果 <5 条 / 调用方指定 `fsearch:deep` / 用户确认要深度报告
- **执行**：标准搜索完成 → 收集已有 URL + query → 调 Tavily Research → 结果 append 到数据集，不覆盖
- **速度**：`mini` ~10-30s（简版摘要）；`pro` ~60-150s（完整报告）。走 MCP 后台 Task 有排队延迟，交互等待中不建议用 `pro`

## WebSearch（已禁用，勿调用）

`WebSearch` 是 Claude Code 内置搜索工具，在 `settings.json` `permissions.deny` 中被禁用（中国区域 US-only 不可用 + bridge 路由事故后恢复禁用）。fsearch **禁止调用 WebSearch**。

## 搜索清单（必须输出到调用方）

每次搜索完成后，**必须输出搜索清单**，由调用方决定是否附加：

```markdown
## 搜索清单

> 非正文

### MiniMax（中文）
1. [标题](url) `[minimax]`

### Tavily（英文）
1. [标题](url) `[tavily]`

### Exa（兜底/补充）
1. [标题](url) `[exa]`

### 核心引用
| 来源 | 标题 | 用途 |
|------|------|------|
| [minimax] | ... | 数据 |
```

**规则**：
- 每源 ≤5 条，每条标注 `[minimax]` / `[tavily]` / `[exa]` / `[tavily-research]`
- 核心引用表选前 3 条，用途列填：定义 / 案例 / 数据 / 对比
- 统一用这四种标签，不用 `[tv]` `[web]` `[mm]` 等变体

## 关联 Skills

- `fresearchmethod` — 研究维度方法论（最常调用方，用本 skill 收集数据）
- `flogme` — OKR/SUM 总结前的行业调研
- `ffeishu` — 文档调研
