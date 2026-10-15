---
name: fsearch
user-invocable: true
description: |
  搜索活动统一原语 — 分语言路由搜索（中文→MiniMax、英文→Tavily，额度耗尽切 Exa）、
  自动 extract、按需 research、聚合去重、来源标注、搜索清单输出。
  被 fresearchframe / flogme / ffeishu 等需要外部调研的 skill 委托调用。
  不含领域方法论（领域解读由 fresearchframe 负责）。
allowed-tools: Read, Write, Bash,
  mcp__tavily__tavily_search, mcp__tavily__tavily_research,
  mcp__tavily__tavily_extract, mcp__tavily__tavily_crawl, mcp__tavily__tavily_map,
  mcp__exa__web_search_exa, mcp__exa__web_fetch_exa
---

# fsearch — 搜索活动统一原语

query 规划（判语言选源）→ 主力搜索（额度耗尽切 Exa）→ extract 全文 → 聚合去重 → 来源标注 → 搜索清单输出

**不含领域方法论**。领域方法论由 `fresearchframe` 负责。

## 配置

API key 配置：
- **Tavily / Exa**：通过 Claude Code 的 MCP 配置管理
  - **ccconfig 用户**：真实 key 放 `ccprivate/conf/claude.json`（symlink）
  - **独立用户**：`~/.claude/settings.json` 的 `mcpServers` 中配置 Tavily + Exa
- **MiniMax**：`ccprivate/conf/llm.json` 的 `llms.minimax31`（与 LLM 预设同一把 key，REST 直调，无需 MCP）

## 何时用

| 触发 | 调用方 |
|------|--------|
| "调研 XX" / "搜 XX 资料" | 任何 skill / 用户直接调用 |
| fresearchframe 调方法论前的数据收集 | fresearchframe |
| flogme 行业调研 | flogme |
| ffeishu 文档调研 | ffeishu |

## 搜索工作流

搜索分三层，调用方按需选择策略，**不是必跑所有层**：

```
query 规划（判断语言 + 策略选择）
    │
    ├─ [快速 ~1s] 主力单源 fast 探查（英文→Tavily fast，中文→MiniMax）
    │
    ├─ [标准 ~3s] 主力源搜索（按语言路由）→ 额度耗尽/报错 → Exa 兜底 → 自动 extract URL
    │       │
    │       └─ extract 不够？→ Exa fetch 补充全文
    │
    └─ [深度 ~30-150s] 标准搜索完成 → 用户确认 → Tavily Research（依赖 Tavily 额度）
```

### 搜索策略预设

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

- 判断依据是 query 主体语言；中英混合 query 优先按中文路由（MiniMax 中文强），拿不准可两源都跑
- **Tavily 超限特征**：`exceeds your plan's set usage limit` → 本次及后续直接切 Exa
- **MiniMax 失败特征**：HTTP 非 200 / `base_resp.status_code != 0`（额度/鉴权）→ 切 Exa
- 执行后必须逐条标注来源标签：`[tavily]`、`[minimax]`、`[exa]`、`[tavily-research]`。

### MiniMax 搜索调用（中文主力）

REST 端点，key 与 LLM 预设同一把（`ccprivate/conf/llm.json` 的 `llms.minimax31`）：

```bash
KEY=$(python3 -c "import json;print(json.load(open('$HOME/git/ccprivate/conf/llm.json'))['llms']['minimax31'])")
curl -s -X POST 'https://api.minimaxi.com/v1/coding_plan/search' \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"q":"查询词"}'
```

- 返回：`{organic:[{title,link,snippet,date}], related_searches, base_resp}`
- 走 coding_plan 搜索额度，非 Tavily 额度
- 注意：`q` 只接受一个查询词；多 query 分多次请求

### 三源对比

| | MiniMax Search | Tavily Search | Exa Search |
|--|---------------|--------------|------------|
| 定位 | **中文主力** | **英文主力** | 兜底 + 中英补充 |
| 速度 | ~1-2s | ~2-3s | ~3-4s |
| 中文 | **强项**，本土站点覆盖好 | 能覆盖，但不如本土深 | 较强，社区/测评站多 |
| 英文前沿 | 一般 | **强项**，arXiv/博客/新闻好 | 也可但不如 Tavily |
| 失败切换 | → Exa | → Exa | 末位，无兜底 |
| 内容提取 | snippet 为主 | Tavily extract（主力） | Exa fetch（补充） |

### 提取全文流程

```
Tavily extract（主力）→ 拿到内容 → 直接用
                      → Exa fetch（补充）→ 直接用
                      → 空壳/被拦截/需登录 → 跳过，备注即可
```

- **Tavily extract** 速度快、可并行，适合公开静态页面
- **Exa fetch** 适合 Exa 搜索结果的页面内容提取
- 注意：Tavily extract 走 MCP Task 机制可能超时，超时后自动切 Exa fetch

### WebSearch（已禁用，勿调用）

`WebSearch` 是 Claude Code **内置搜索工具**，在 `settings.json` `permissions.deny` 中被禁用（中国区域 US-only 不可用 + bridge 路由事故后恢复禁用）。

fsearch **禁止调用 WebSearch**。搜索只走本 skill 的路由源（Tavily / MiniMax / Exa）。

## Tavily Research（深度综合）

**不是并行搜索源**，而是标准搜索后的按需步骤。

### 何时用

- 标准搜索返回结果量不足（<5 条有效）
- 调用方指定 `fsearch:deep` 策略
- 用户确认需要深度报告

### 执行方式

```
标准搜索完成 → 收集已有 URL + query → 调 Tavily Research
  └─ research 结果自动 append 到数据集，不覆盖已有搜索
```

### 速度说明

| 模型 | 典型耗时 | 输出 |
|------|---------|------|
| `mini` | ~10-30s | 简版摘要 |
| `pro` | ~60-150s | 完整研究报告，含归一化排名、敏感性分析等 |

- Tavily Research 走 MCP 后台 Task 机制，有排队延迟
- pro 模式下做多轮搜索+综合，产出质量高但耗时长
- **不建议在用户交互等待中使用 pro**，适合后台批处理
- 设 timeout 建议：mini=60s, pro=180s

## Tavily 参数速查

### Search 参数

| 参数 | 可选值 | 说明 |
|------|--------|------|
| `search_depth` | `basic` / `advanced` / `fast` / `ultra-fast` | fast=低延迟高相关; ultra-fast=极低延迟 |
| `topic` | `general` / `news` / `finance` | |
| `time_range` | `day` / `week` / `month` / `year` | |
| `start_date`/`end_date` | `YYYY-MM-DD` | |
| `max_results` | `5`-`20` | |
| `include_raw_content` | `false` / `markdown` / `text` | 返回原始页面内容 |
| `include_domains` / `exclude_domains` | 域名列表 | |
| `country` | ISO | |

### Research 参数

| 参数 | 可选值 | 说明 |
|------|--------|------|
| `model` | `mini` / `pro` / `auto` | mini < 30s, pro 60-150s |
| `input` | 字符串 | 详细描述需求，越详细质量越高 |

### 推荐默认值

- 普通快速搜索：`tavily_search(query, search_depth="fast", max_results=5)`
- 标准搜索：`tavily_search(query, search_depth="advanced", max_results=10)`
- 新闻动态：`tavily_search(query, topic="news", time_range="week", search_depth="advanced")`

## 双语搜索

对需要全局覆盖的主题，同时执行中英文 query：

```
中文 query  → MiniMax 搜索（主力），耗尽 → Exa
英文 query  → Tavily Search（主力），耗尽 → Exa
```

聚合、去重后标注 `[minimax]` / `[tavily]` / `[exa]`。

## 聚合去重

```python
def deduplicate_by_url(results):
    seen = set()
    unique = []
    for r in results:
        url = r.get('url', '')
        if url and url not in seen:
            seen.add(url)
            unique.append(r)
    return unique
```

## Session 内缓存（搜索质量保底）

- 同一 query 在 **15 分钟内**不重复执行搜索（依赖 Tavily MCP 自带缓存）
- 当前无 skill 层缓存实现，调用方自行管理
- 搜索质量保底：结果数 < 3 → 自动改写 query 重搜一次；仍 < 3 → 换源重搜（主力↔Exa 互换）或改用 `fsearch:deep`（需 Tavily 额度可用）

## 搜索清单（必须输出到调用方）

每次搜索完成后，**必须输出搜索清单**给调用方，由调用方决定是否附加。

```markdown
## 搜索清单

> 非正文

### MiniMax（中文）
1. [标题](url) `[minimax]`
2. [标题](url) `[minimax]`

### Tavily（英文）
1. [标题](url) `[tavily]`
2. [标题](url) `[tavily]`

### Exa（兜底/补充）
1. [标题](url) `[exa]`
2. [标题](url) `[exa]`

### 核心引用
| 来源 | 标题 | 用途 |
|------|------|------|
| [minimax] | ... | 数据 |
| [tavily] | ... | 数据 |
| [exa] | ... | 案例 |
```

**规则**：
- 每源 ≤5 条，每条标注 `[minimax]` / `[tavily]` / `[exa]` / `[tavily-research]`
- 核心引用表选前 3 条，用途列填：定义 / 案例 / 数据 / 对比
- 统一用 `[minimax]` `[tavily]` `[exa]` `[tavily-research]`，不用 `[tv]` `[web]` `[mm]` 等变体
- 调用方决定是否附加到最终输出文档

## 关联 Skills

- `fresearchframe` — 4 领域方法论（最常调用方）
- `flogme` — OKR/SUM 总结前的行业调研
- `ffeishu` — 文档调研