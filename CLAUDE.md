# CLAUDE.md — skill

> 项目级 AI 行为指南，仅在 `~/git/skill/` 工作时加载。全局规则在 `~/CLAUDE.md`。
>
> **分工**：README 面向外部用户（怎么装、有哪些技能），CONTRIBUTING 面向贡献者（PR 流程），
> 本文件只写**本机能动文件时的约定**和**从文档看不出来的机制**。三者不重复。

## 一句话

30 个自建 Claude Code plugin 的聚合仓，五层架构：`fcore`(机械) → `fhub`(派发) →
业务技能 → `fwstd-*`(规范) → `fworch-*`(编排)。详见 README 的架构图。

## 硬约束（改文件前必看）

1. **`SKILL.md` 的 `description` 是单一真相源**。改完跑 `python3 scripts/sync-marketplace.py --write`，
   CI 会检查 marketplace.json 是否同步（不同步 = 非零退出）。
2. **公开仓零真值**。不放 API key / 飞书 token / 租户域名 / 个人文档 URL。
   CI 检查 `plugins/*/config.yaml` 必须不存在（只允许 `config.yaml.example`）。
3. **机械操作一律走 `fcore`**，不要在 SKILL.md 里手写 lark-cli 参数。历史上 5 处各抄一份
   auth 预检，其中 3 处 grep 写错（`'"ok":true'` 匹配不到 `"ok": true`）导致认证正常也恒失败。
4. **SKILL.md 只写判断，不写实现**。细则进 `references/`，命令进 `scripts/` 或 `fcore`。
   超过 200 行就该拆。
5. **不改 `_boot.sh` 副本**。`plugins/*/references/_boot.sh` 是 `fcore/references/_boot.sh`
   的生成物，由 `ccconfig/bin/sync-plugin-env.sh` 分发。改源文件后重新分发。
6. **本仓不手动 commit/push**。`~/git/` 下由 auto-sync monitor 独占提交权（inotify → 30s
   debounce → add+commit+push）。改完文件继续干别的。

## 从文档看不出来的机制

### 为什么每个 plugin 都带一份 `_boot.sh`

`/plugin install` **只复制 plugin 自己的目录**。`fcore` 的实现（lib/*.sh）装在
`plugins/cache/<market>/fcore/<版本>/`，别的 plugin 装完拿不到它。

所以每个 plugin 带一份 40 行的 stub 去找实现，**实现仍然只有 fcore 一处**。
stub 依次找：自己就是 fcore → 兄弟目录（git clone 布局）→ cache 布局 → `~/.claude/skills/fcore/`
→ `F_CORE_LIB` 环境变量。

改 fcore 的 lib 后，若要覆盖所有布局，跑 `bash ccconfig/bin/sync-plugin-env.sh`。

### 为什么 description 不能随手改格式

`sync-marketplace.py` 逐字比对。改写时多一个空格、少一个换行都会报 `DRIFT`，
CI 直接红。改完必须 `--write`。

### 为什么配置不放 plugin 目录

`/plugin update` 整目录替换 `~/.claude/plugins/cache/<market>/<plugin>/<版本号>/`。
写在那里的 `config.yaml` 会丢。用户自填配置落 `~/.claude/skill-config/<plugin>.yaml`
（cache 之外），由 `fcore conf` 统一读写。

## 常用命令

```bash
python3 scripts/sync-marketplace.py           # 检查漂移（CI 同款）
python3 scripts/sync-marketplace.py --write   # 写回 marketplace.json

cd www && python3 -m http.server 8000         # 本地预览展示页

bash ccconfig/bin/sync-plugin-env.sh          # 分发 _boot.sh 到所有 plugin
bash ccconfig/bin/sync-plugin-env.sh --check  # 只校验
```

## 改完必须验证

```bash
bash -n plugins/fcore/lib/*.sh                 # 改 shell 后
python3 scripts/sync-marketplace.py            # 改 description 后
~/.claude/skills/fcore/bin/fcore where         # 确认路径解析正常
```

**shell 改动后不跑 `bash -n` 会出事**：Edit 跨行替换容易把多行压成一行，
运行时才报 `[: missing ']'`。

## 新增 plugin

步骤见 CONTRIBUTING。补充两条本机约定：

1. 建完目录后跑 `bash ccconfig/bin/sync-plugin-env.sh`，让新 plugin 拿到 `_boot.sh`
   （否则该 plugin 装到 cache 后无法解析配置）。
2. `marketplace.json` 里的 `keywords` 统一写 `["f"]`。

## 与 ccconfig 的关系

本仓是**产物**（技能实体），`~/git/ccconfig` 是**安装分发层**：

| ccconfig 侧 | 作用 |
|---|---|
| `lib/init-skill.sh sync` | symlink 本仓 plugin → `~/.claude/skills/` |
| `bin/sync-plugin-env.sh` | 分发 `_boot.sh` 到所有 plugin |
| `lib/deps-check.sh` | 读各 plugin 的 `deps.txt` 装 CLI 依赖 |

私有真值在 `~/git/ccprivate/conf/<plugin>.yaml`（**不是 `skill/`**，旧路径已迁走），
本仓只放 `config.yaml.example`。

## 相关

- 用户怎么装 → [README.md](README.md)
- 怎么加技能 → [CONTRIBUTING.md](CONTRIBUTING.md)
- 版本变更 → [CHANGELOG.md](CHANGELOG.md)
- 架构决策 → [docs/adr/](docs/adr/)
- 层级决策记录 → `ccconfig/docs/adr/0058-skill-layer-fcore-fhub.md`
