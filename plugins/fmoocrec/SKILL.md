---
name: fmoocrec
user-invocable: true
description: |
  MOOC 课程推荐助手 — 基于 QS 世界排名顶级学府课程体系，为学生生成个性化 MOOC 学习路径。
  课程数据存 Supabase（共享），学生画像/进度存飞书 Wiki + Base（个人持久化）。
  用法：用户说"课程推荐"/"MOOC"/"在线课程"/"自学路径"/"学习规划"、问"有什么好的网课"/"想系统学生物"。
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# fmoocrec — MOOC 课程推荐助手

**课程范围**：只做生物专业课（core/advanced/frontier，约 30 门）。数理基础不做 ——
学校课程自然覆盖，MOOC 再加一层是负担。

```
Supabase（共享课程数据，只读）        飞书（学生个人数据）
courses 表 ~30 门元数据    ──SQL──→    学生画像 Doc / 学习路径 Doc / 进度 Base
```

## 决策树

```
/f-moocrec
  ├─ 未配置 或 docs.profile 为空
  │   → 工作流 0：grill 问答 + 建飞书资源      （references/onboarding.md）
  ├─ 已配置
  │   ├─ "推荐课程"/"下一门"/"接下来学什么"     → 工作流 1
  │   ├─ "完成了"/"拿到证书了"                 → 工作流 2
  │   ├─ "更新画像"/"改了方向"                 → 工作流 3
  │   ├─ "进度"/"学了哪些"/"还差多少"          → 工作流 4
  │   └─ "证书"/"背书"/"认证"                  → 工作流 5
```

各工作流的完整逻辑、推荐算法、输出格式 → `references/workflows.md`。

## 配置

**ccconfig 用户**：真值在 `<ccprivate>/conf/fmoocrec.yaml`，`init-skill.sh sync` 自动接上。
**独立用户**：`fcore conf set <key> <值>` 写进 `~/.claude/skill-config/fmoocrec.yaml`
（`/plugin update` 不覆盖）。

```bash
~/.claude/skills/fcore/bin/fcore conf path tenant_domain     # 看当前从哪读
~/.claude/skills/fcore/bin/fcore conf require base_token     # 缺失时打印填写指引
```

需要：飞书 Base（学习进度表）、飞书 Wiki 节点（画像 + 路径文档）。
Supabase 课程数据共享只读，**无需用户配置**。

**未配置时**：能查课程、能给推荐（只读 Supabase + 内存推荐），
不写飞书 Base/Wiki；提示用户补配置后再启用进度跟踪。

## 飞书操作边界

| 操作 | 谁做 |
|---|---|
| 创建/更新 wiki doc | **先调 ffeishu**（全局硬前置），Base 操作不需要 |
| 创建 Base / 表 / 字段 | 本 skill 直接调 lark-cli |
| 进度记录读写 | 本 skill 直接（`scripts/bio-progress.py`） |
| 课程查询 | 本 skill 直接（Supabase 管理 API） |

**命令走 `fcore`**：`fcore auth` 判断可用性，不可用时降级为"只推荐不写库"。

## 格式约束

生成学习路径/推荐时：

1. 表格必须 XML + `<colgroup>`（宽度和 822）；不手动编号；不用 H4+；不用 `---`
2. 课程链接必须是完整可点击 URL（禁止 bit.ly 短链，易失效）
3. 每门课**同时列免费方案和证书方案**（双轨）
4. 证书信息必须包含验证方式
5. 图表必须用 `<whiteboard type="mermaid">` XML 语法 —— Markdown mermaid 代码块
   **不会**自动转白板，ASCII 字符画也不是图表。支持 flowchart/pie/gantt/timeline/mindmap

完整陷阱清单（12 条） → `references/rules.md`。

## 参考

| 文件 | 内容 |
|---|---|
| `references/onboarding.md` | 工作流 0 完整步骤 + 飞书初始化命令 |
| `references/workflows.md` | 工作流 1-5 逻辑与输出格式 |
| `references/rules.md` | 格式约束、委派规则、12 条陷阱、Supabase 维护 |
| `references/bio-curriculum.md` | **真实课程数据**（~30 门 + 先修关系图） |
| `references/certificate-guide.md` | 证书获取/验证/LinkedIn 挂载 |
| `references/platform-guide.md` | 平台定价、免费策略、语言支持 |
| `scripts/bio-progress.py` | Base 进度读写 |
| `scripts/refresh-courses.py` | 刷新课程状态（活跃/失效） |
| `scripts/seed-courses.sql` | 课程表初始化 SQL |
