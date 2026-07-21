# Worklog 质量规范与合并策略

## 质量规则（SessionEnd hook 内置）

| 规则 | 动作 |
|------|------|
| 0 条 user 消息 | **跳过**，不写入（空 session 噪音） |
| LLM 标题生成失败 | fallback → commit message → 首条 user prompt |
| 标题为 `session 工作` 格式 | 标记为低质量，待人工修正 |
| 同 session 多次触发 | **合并**到第一条（累加 token/轮数，标题取较长者） |

**KR 自动路由**：根据 session cwd 匹配 `config.yaml` → `kr_route` 配置，自动关联到对应 KR。未匹配的走 `_default`。

```json
// config.yaml → kr_route
{
  "<project-name>": "recXXX",     // ~/git/<project-name> → O4 KR-产品化
  "<another-project>": "recYYY",  // ~/git/<another-project> → O4 KR-工作流
  "_default": "recYYY"
}
```

## 整合策略

### 周度 (`--mode merge`)

- 完全同标题 → **自动合并**：保留说明最长的那条，合并其余说明（`---` 分隔），删除重复
- 标题相似 > 85% 且同日期 → 候选合并（人工确认）
- 空 session 记录（0 轮对话）→ 自动删除

### 月度 (`--mode monthly`)

- 标题含 `session 工作` / `## Context Usage` → 候选修正
- 跨日期同主题分散记录 → 候选合并清单
- 关联 KR 无效（指向已删除记录）→ 批量检测

### 合并规则

| 条件 | 动作 | 是否自动 |
|------|------|---------|
| 完全同标题 | 保留说明最长记录，合并说明，删除其余 | ✅ 自动 |
| 标题相似 > 85% + 同日期 | 候选合并 | ❌ 人工 |
| 标题相似 > 85% + 跨日期 + 递进更新 | 合并说明到最早记录 | ✅ 自动 |
| 0 user_msgs 且 0 commits 0 edits | 删除 | ✅ 自动 |

### 调度机制

| 频率 | 触发方式 | 动作 |
|------|---------|------|
| 每周 | 自动（距上次 merge > 7 天时 hook 自动执行） | `--mode merge --write` |
| 阶段（~30天） | 提醒（hook 写入 notes 文件，下次对话可见） | `--mode monthly` 预览 |
| 手动 | 用户说 "做周整合" / "阶段总结" | 立即执行 |

状态文件：`/tmp/flogme_last_merge`、`/tmp/flogme_last_monthly`（记录上次执行时间戳）。

## 脚本用法

```bash
python3 worklog_consolidate.py --mode merge         # 预览去重
python3 worklog_consolidate.py --mode merge --write # 执行合并
python3 worklog_consolidate.py --mode weekly        # 每周清理
python3 worklog_consolidate.py --mode monthly       # 阶段全量扫描
python3 worklog_consolidate.py --mode dry-run       # 统计总览
```

## 字段规范

Worklog 表当前字段（11 个，2026-06 清理后）：

| 字段 | 类型 | 写入方式 |
|------|------|---------|
| 标题 | 文本 | LLM 生成，≤60 字，无 `##`/`【】` 前缀 |
| 成果类型 | 单选 | 自动填 `工具开发` |
| 说明 | 多行文本 | 结构化摘要 + commits + edits |
| 日期 | 日期 | 当天 |
| 关联KR | 链接 | kr_route 自动匹配 |
| input/output_tokens | 数字 | transcript 统计 |
| model | 文本 | 使用的 LLM |
| asst/user_msgs | 数字 | 对话轮数 |
| 来源 | 单选 | auto-clear/new/exit/resume/other |

已删字段（2026-06）：量化结果、cache_creation/read_input_tokens、关联Action、合并到、合并状态
