# search-internals — 搜索实现细节

> fsearch 的内核细节，按需读取。SKILL.md 只给决策表与输出契约。

## 三源对比

| | MiniMax Search | Tavily Search | Exa Search |
|--|---------------|--------------|------------|
| 定位 | **中文主力** | **英文主力** | 兜底 + 中英补充 |
| 速度 | ~1-2s | ~2-3s | ~3-4s |
| 中文 | **强项**，本土站点覆盖好 | 能覆盖，但不如本土深 | 较强，社区/测评站多 |
| 英文前沿 | 一般 | **强项**，arXiv/博客/新闻好 | 也可但不如 Tavily |
| 失败切换 | → Exa | → Exa | 末位，无兜底 |
| 内容提取 | snippet 为主 | Tavily extract（主力） | Exa fetch（补充） |

## MiniMax 搜索调用（中文主力）

REST 端点，key 与 LLM 预设同一把（`ccprivate/conf/llm.json` 的 `llms.minimax31`）：

```bash
KEY=$(python3 -c "
import sys, json, os
sys.path.insert(0, os.path.expanduser('~/.claude/skills/ffeishu/references'))
from config_env import ccprivate_root
print(json.load(open(ccprivate_root()/'conf/llm.json'))['llms']['minimax31']['key'])")
curl -s -X POST 'https://api.minimaxi.com/v1/coding_plan/search' \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"q":"查询词"}'
```

- 返回：`{organic:[{title,link,snippet,date}], related_searches, base_resp}`
- 走 coding_plan 搜索额度，非 Tavily 额度
- 注意：`q` 只接受一个查询词；多 query 分多次请求

## 提取全文流程

```
Tavily extract（主力）→ 拿到内容 → 直接用
                      → Exa fetch（补充）→ 直接用
                      → 需保留结构（标题层级/表格/公式/图）且国内可达 → MinerU crawl
                      → 空壳/被拦截/需登录/SPA → Playwright（见 rules/search.md）
                      → 均失败 → 跳过，备注即可
```

- **Tavily extract** 速度快、可并行，适合公开静态页面
- **Exa fetch** 适合 Exa 搜索结果的页面内容提取
- **MinerU crawl**（`mcp__mineru__parse_documents`）：国内可达 + 需结构保留时用，正文提取保留 `#` 标题层级/表格/公式/图片 URL，适合把网页正文嵌进文档。**限制**：服务器在中国区，github/aws/wikipedia 等境外站超时或被区域限制；目标站反爬（如飞书官网）会失败 → 回落 Tavily/Exa
- 注意：Tavily extract 走 MCP Task 机制可能超时，超时后自动切 Exa fetch

**网页源选型速查**：

| 场景 | 首选 |
|------|------|
| 常规国内/外静态页 | Tavily extract |
| Exa 搜索结果页 | Exa fetch |
| 国内页 + 要保留结构嵌文档 | **MinerU crawl** |
| 登录墙 / SPA / 反爬 | Playwright |

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
