---
name: flogme
user-invocable: true
description: 个人管理系统 — OKR 目标管理、Worklog 工作日志、Reflect 反思、SUM 周期/领域总结生成。数据存飞书 Base，输出到飞书文档。
allowed-tools: Bash, Read, Write, Edit, Agent, WebSearch, mcp__tavily__tavily_search, mcp__minimax__web_search
---

# flogme — 个人管理系统

## 架构

```
🎯 OKR：O = 方向性目标（季度/年度）→ KR = 可量化结果
📝 Worklog：每条必须关联一个 KR，自动继承分类
🪞 Reflect：周/月/季度反思，可选关联 O
📊 SUM：个人总结（读三层 → 模板 → 飞书文档）／汇报输出（模板 → 文档）
```

**核心原则**：O=why, KR=what success, Worklog=what I did, Reflect=what I learned, SUM=what it means。
**分类体系**：所有层级共用 `work / learn / project`。

## 数据模型

4 张表：OKR_O / OKR_KR / Worklog / Reflect。字段规范 → `references/data-model.md`。
KR_Progress 表已于 2026-06-09 废弃。

**KR 三轴（2026-10-30 定）**：`type` 承诺强度 / `status` 生命周期 / `health` 进展健康。
三者正交，**不能合并** —— 原来把健康混进 status，导致「取消难点 KR 后健康分反而上升」的扭曲激励。
O 健康分 = Σ(health 折算 × type 权重) / Σ 权重，**cancelled 必须排除**，且必须同时看
off_track 条数（同分不同义）。

## 工作流

| 说法 | 做什么 |
|---|---|
| "记录工作"/"写日志" | Worklog 写入（关联 KR，自动继承分类） |
| "OKR"/"目标管理" | O/KR 创建与更新 |
| "反思" | Reflect 写入 |
| "总结"/"生成总结"/"季度报告"/"年度报告" | SUM 生成 |
| "周报"/"本周工作" | 周期汇总（cron 每周跑的就是这条） |

各工作流的完整步骤、命令、数据写入细节 → `references/workflows.md`。

## 自动化

每周一自动汇总上一周，跑 `weekly_rollup.py --once`（锚点是周一不是执行日，故不会重复）。
手动补跑、指定周、cron 边界、已知限制 → `references/automation.md`。

```bash
python3 weekly_rollup.py --once           # 预览
python3 weekly_rollup.py --once --write   # 写入
```

**改动后必须实跑验证**：此前 cron 传了脚本没有的参数（`--since-last-week`）→ 每次都静默失败，
而注册状态看起来是成功的。

## 数据补充源

除手动写 Worklog，还可汇入三类外部数据（部门工作记录表、工作群消息、用户补充）。
融合规则 → `references/supplement.md`。

## 归档

主表只留当年，旧年份搬到 `Worklog_Archive`（同 Base 内）。

```bash
python3 archive_worklogs.py --before 2026-01-01 --write
```

**安全设计**：先写归档表、条数核对一致才删主表，不一致立即中止。
每年初跑一次，**执行前先全量导出备份**。

## 配置

**ccconfig 用户**：真值在 `<ccprivate>/conf/flogme.yaml`，`sync` 自动接上。
**独立用户**：`fcore conf set <key> <值>` 写 `~/.claude/skill-config/flogme.yaml`（升级不覆盖）。

```bash
~/.claude/skills/fcore/bin/fcore conf path base_token    # 看当前从哪读
~/.claude/skills/fcore/bin/fcore conf require base_token # 缺失时给填写指引
```

需要：飞书 Base（4 张表）、wiki 节点 token。字段获取方式见 `config.yaml.example`。
**未配置时**：只能本地生成总结草稿，不写 Base/文档。

## 参考

- `references/data-model.md` — 4 表字段规范
- `references/workflows.md` — 各工作流步骤与命令
- `references/commands.md` — 命令速查
- `references/automation.md` — cron / 手动补跑 / 边界
- `references/supplement.md` — 外部数据汇入
- `references/templates.md` — SUM 模板
- `references/base-init.md` — Base 初始化

书目：John Doerr *Measure What Matters*(2018)、Google re:Work OKR Guide、Julia Evans Brag Documents、Tiago Forte PARA Method
