---
name: fcore
description: |
  f* 技能包的机械内核 — 路径解析、配置读写、lark-cli 账号与授权预检、文档增改查上传、
  格式断言、体裁派发匹配。其他技能不重写这些命令，一律调 fcore。
  用法：被其他 f* 技能调用，或用户说"检查飞书授权"/"配置存哪了"/"这个需求该用哪个技能"。
user-invocable: true
allowed-tools: Read, Write, Bash, Glob, Grep
---

# fcore — 机械内核（L0）

**只放确定性操作。** 一切命令写在这里，其他技能的 SKILL.md 只写"该走哪条路"。

## 为什么有这一层

此前的代价（实测）：27 份 `_skillconf_boot` 副本、2 份已分叉的 `lark_env.sh`、
5 处 auth 预检其中 **3 处 grep 写错导致认证明明正常也恒报 AUTH_FAILED**、154 处硬编码
`~/.claude/skills/` 路径（plugin 装入 `cache/<market>/<plugin>/<version>/` 后全断）。

根因不是懒，是**没有一层专门放机械操作**，每个技能各自抄一遍，抄错的没人发现。

## 命令

| 命令 | 作用 |
|------|------|
| `fcore auth` | 预检 lark-cli。0=可用 1=未装 2=未配置/过期 |
| `fcore conf get <key> [默认]` | 读配置，8 级回退 |
| `fcore conf set <key> <值>` | 写用户自填（`/plugin update` 不覆盖） |
| `fcore conf path <key>` | 该键命中哪个文件（排障） |
| `fcore conf require <key>` | 缺失时打印三个填写位置 |
| `fcore data <相对路径>` | 用户数据文件路径（课程进度这类可变状态） |
| `fcore data-ls <模式>` | 列出用户数据文件 |
| `fcore genre <需求>` | 派发：返回 domain/genre → 该用哪个技能 |
| `fcore genres` | 列出所有域与体裁 |
| `fcore fmt-xml <file>` | 飞书格式断言（H1 蓝字/无 H4+/无分割线/colgroup 822/无手动编号） |
| `fcore fmt-md <file>` | 报告格式断言（无分割线/表格双横线/数据必有引用/文献 ≥15） |
| `fcore doc create\|get\|ids` | 文档增/查（固定参数模板） |
| `fcore upload <file>` | 上传到 Drive |
| `fcore search <词> [数量]` | 搜文档 |
| `fcore where` | 打印所有解析路径 —— 排障第一步 |

## 配置存放（升级不覆盖）

读取顺序（高 → 低），**用户自填落在最后三档，都不在 `plugins/cache/` 下**：

```
1. 环境变量 F_<KEY>
2. ${CLAUDE_PLUGIN_DATA}/config.json          官方持久目录
3. ~/.claude/plugins/data/<plugin>/config.json  同上兜底
4. ~/.claude/settings.json → pluginConfigs     官方弹窗
5. ~/.claude/.credentials.json → pluginSecrets 官方敏感通道
6. <ccprivate>/conf/<plugin>.yaml              私有仓（自用主通道）
7. <ccprivate>/conf/_shared.yaml               跨技能共享真值
8. ~/.claude/skill-config/<plugin>.yaml        ← 用户自填规范落点（推荐）
9. <plugin目录>/config.yaml                    旧通道（迁移兼容）
```

**为什么 8 安全**：`/plugin update` 整目录替换的是
`~/.claude/plugins/cache/<market>/<plugin>/<version>/`。
`~/.claude/skill-config/` 完全在这个范围之外，所以升级、卸载、重装都不会碰它。

**没配也能用**：`fcore conf get` 缺失时返回非零，调用方据此降级——只做本地能力
（抽取/写作/分析），跳过需要真值的步骤（飞书归档/Base 写入），并提示去哪里填。
不强制配置，不阻断流程。

## 用户数据 vs 配置

| 类型 | 例子 | 用什么 | 落点 |
|------|------|--------|------|
| 配置 | tenant_domain、wiki 节点 token | `fcore conf get/set` | `skill-config/<plugin>.yaml` |
| 用户数据 | 课程进度、案例索引、学习画像 | `fcore data` | `skill-config/data/<plugin>/` |

区别：配置是**键值对**，用户数据是**结构自由的文件**（课程配置有嵌套的 lesson_docs 列表）。

## 脚本调用

其他技能的 references/ 或 scripts/ 里直接 source：

```bash
source ~/.claude/skills/fcore/lib/path.sh
source ~/.claude/skills/fcore/lib/lark.sh
f_lark_need_auth || echo "降级：跳过飞书步骤"
```

plugin 安装布局下 `~/.claude/skills/` 可能不存在 → 用 boot stub 定位（`references/_boot.sh`），
与现有 27 份 stub 同一机制，实现仍只有 fcore 一处。
