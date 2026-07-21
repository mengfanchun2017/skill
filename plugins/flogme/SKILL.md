---
name: flogme
user-invocable: true
description: 个人管理系统 — OKR 目标管理、Worklog 工作日志、Reflect 反思、SUM 周期/领域总结生成。数据存飞书 Base，输出到飞书文档。
allowed-tools: Bash, Read, Write, Edit, Agent, WebSearch, mcp__tavily__tavily_search, mcp__minimax__web_search
---

# flogme — 个人管理系统

OKR → KR → Worklog → Reflect → SUM 五层架构，全部数据存飞书 Base。

## 架构

```
🎯 OKR（最高级）
   ├─ O: 方向性目标，季度/年度级别，变化慢
   └─ KR: 可量化关键结果，变化快，关联一个 O
        │
        ▼
📝 Worklog（日常记录）
   └─ 每条必须关联一个 KR，自动继承分类
        │
        ▼
🪞 Reflect（定期反思）
   └─ 周/月/季度，可选关联 O
        │
        ▼
📊 SUM（总结生成）双通道
   ├─ 个人总结: 读取以上三层 → 内置模板 → 飞书文档
   └─ 汇报输出: 学习外置模板 → Worklog+KR数据+用户输入 → 飞书文档
```

**核心原则**：O=why, KR=what success, Worklog=what I did, Reflect=what I learned, SUM=what it means.
**分类体系**：所有层级共用 `work / learn / project` 三类（工作/学习/项目）。

## 配置

> 📖 完整说明 → [config.aiagt.dev](https://config.aiagt.dev/flogme)

**ccconfig 用户**：真实值放 `ccprivate/skill-config/flogme.yaml`，`init-skill.sh sync` 自动覆盖。
**独立用户**：`cp config.yaml.example config.yaml` 填入真实值。

需提前准备：
- 飞书 Base（手动创建）→ 获取 Base token + 表 ID
- wiki 节点 token → OKR/SUM 文档输出位置
- `config.yaml.example` 含所有字段获取方式

config.yaml 在 ccprivate，含 Base tokens + table IDs + wiki node。数据结构见 [references/data-model.md](references/data-model.md)。

## 数据模型

4 个表（OKR_O / OKR_KR / Worklog / Reflect），完整字段规范 → [references/data-model.md](references/data-model.md)。

> KR_Progress 表已于 2026-06-09 废弃，详见 [ADR-0003](../../docs/adr/0003-deprecate-tasks-and-kr-progress.md)。

## 工作流

### 1. OKR 创建

```
用户: "新设一个 work 的 O：XXX，季度目标"
  → OKR_O 表创建 Objective → 拆解 2-5 个 KR → OKR_KR 表创建并关联 O
```

KR 写法：✅ "模型分流系统上线，P99 延迟降低 50%" ❌ "完成模型分流开发"（任务不是结果）。

### 2. Worklog 写入

**手动**：用户说"写日志"/"记录工作" → agent 判断 → 调 flogme skill → 写飞书 Base。
或直接运行 `log_write.py worklog --title ... --kr recXXX ...`。

**日合并**：每天 12:01 自动 consolidate 当日 worklog，去重合并。
（配置方式见下方 § 日合并定时器配置）

KR 自动路由、质量规则、合并策略、字段规范 → [references/worklog-quality.md](references/worklog-quality.md)。
整合脚本用法 → `worklog_consolidate.py --mode merge|weekly|monthly|dry-run`，详见 [references/worklog-quality.md](references/worklog-quality.md)。

### 3. Reflect 写入

```
用户: "做周反思" / "weekly reflect"
  → 拉取本周 Worklog → 引导填写四象限（做得好/待改进/学到/下阶段）
  → 调 log_write.py reflect 写入 Reflect 表
  → 注: 不自动改 KR 状态，KR 完成时主动跑 kr-status
```

写入命令：`log_write.py reflect --title "..." --period "周" --good "..." --improve "..." --learned "..." --next "..."`

### 4. SUM 总结生成

```
用户说"生成X总结"
  ├─ 个人总结（模板内置）→ 周期/领域/OKR复盘/年报
  │    拉取 Base 数据 → sum_generate.py 按模板生成 Markdown → 委托 ffeishu 创建飞书文档
  └─ 汇报输出（模板外置）→ 学习飞书文档模板 → 按模板结构填数据 → ffeishu 创建
       模板在 OKR wiki 节点「模板」文件夹，fetch 后提取 H1/H2/表格/固定文案
```

**个人总结类型**：
| 类型 | 触发示例 | 模板侧重 |
|------|---------|---------|
| 周期总结 | "生成本季度工作总结" | 时间维度：成果、不足、下阶段 |
| 领域总结 | "生成 AI 领域年度总结" | 领域维度：worklog 聚合 |
| OKR 复盘 | "复盘 Q2 OKR" | O 达成度、KR 评分、经验教训 |
| 综合年报 | "生成年度个人报告" | 三分类汇总 + 成长轨迹 + 新年 OKR |

模板详情 → [references/templates.md](references/templates.md)。

**SUM 生成命令**：拉取 Base 数据后用 `sum_generate.py` 生成 Markdown，详见 [references/commands.md](references/commands.md)。

## 数据写入

`log_write.py` 统一封装 worklog / reflect / kr-status 三个写入动作。命令用法 → [references/commands.md](references/commands.md)。

## Base 初始化

新建 Base 推荐 rename 默认表 + 加字段。auto_number 转 number、field-update vs raw API 选型 → [references/base-init.md](references/base-init.md)。

## 命令速查

lark-cli 环境变量、Base 数据拉取、SUM 生成全流程 → [references/commands.md](references/commands.md)。

## 集成点

| 系统 | 关系 |
|------|------|
| f-worklog | 简化版，flogme 是其升级替代 |
| ffeishu | SUM 输出目标：飞书文档，统一编排 lark-cli（不直接依赖 lark-* skill） |
| fpptx | 年度总结可选输出 PPT |
| fresearchframe | 领域总结前可联动做行业调研 |
| lark-cli | 所有飞书操作（文档/Base/表格/日历）通过 lark-cli（npm 全局） |

## 文档创建规则

SUM 生成飞书文档时，**必须通过 ffeishu skill 创建**（不裸调 lark-cli），原因：
- ffeishu 加载 write-checklist.md 等格式化约束，保证格式规则完整进 context
- 直接裸调会丢失格式化约束，导致编号标题、分割线、窄表格等问题

flogme 职责：从 Base 聚合数据 → 按模板填 Markdown → 交给 ffeishu 创建文档。

## 日合并定时器配置

Worklog 日合并通过 Claude 的 durable cron 机制运行（非系统 cron），需在 Claude 对话中创建：

> **首次配置**：在 Claude 对话中说"设 worklog 日合并每天中午12:01执行"即可。
> **改时间**：说"改 worklog 日合并时间到 HH:MM"。

底层命令：
```
CronCreate(cron="1 12 * * *",
  prompt="cd ~/git/skill/plugins/flogme && python3 worklog_consolidate.py --mode merge --write 2>&1",
  recurring=true, durable=true)
```

> ⚠️ `durable=true` 会将任务持久化到 `.claude/scheduled_tasks.json`，重启 Claude 后继续生效。

## 参考

- John Doerr, *Measure What Matters* (2018)
- Google re:Work OKR Guide
- Perdoo OKR Guide (2026)
- Julia Evans, Brag Documents
- Tiago Forte, PARA Method
