# ffeishu 安装与配置

> SKILL.md 只留一句"怎么配"，细节在此。配置读写一律走 `fcore conf`，
> 不要手写回退链（此前 15 处各写一份，改一处必漏其余）。

## 前置条件

- lark-cli 命令参考 → `references/lark-cli-cheatsheet.md`。本 skill 直接调 lark-cli，不依赖 lark-* skill。
- 跨格式转换（涉及 Office 时）→ `references/feishu-office-bridge.md`

## 配置

> 📖 完整说明 → [config.aiagt.dev](https://config.aiagt.dev/ffeishu)

配置查找由**单一实现** `references/plugin_env.sh`（Python 版 `config_env.py`）统一决定，
所有 skill 共用同一条 8 级链（完整清单见「用户配置」一节）。

| 你是哪类用户 | 配置写在哪 |
|---|---|
| plugin 安装（`/plugin install`） | `claude plugin configure ffeishu@<market>` 弹窗填；值落 `settings.json` 的 `pluginConfigs` 或 `.credentials.json` 的 `pluginSecrets` |
| ccconfig 用户 | `$CCPRIVATE_HOME/conf/ffeishu.yaml`（旧位置 `skill/ffeishu.yaml` 仍兼容） |
| 独立用户（git clone） | `cp config.yaml.example config.yaml` 填真实值，或 `$CLAUDE_PLUGIN_DATA/config.json` |

⚠️ **不要**把配置写进 `<skill目录>/config.yaml` 然后指望它跨 `/plugin update` 存活 ——
plugin 用户装的是 `cache/<market>/<plugin>/<版本号>/` 只读副本，更新即整目录替换。

需提前准备：
- 飞书租户（企业版/个人版）
- `npm install -g @larksuite/cli` → `lark-cli auth login`
- wiki 节点 token（新文档默认父目录）

> 完整格式约束+安全规则参考 → `references/write-checklist.md`

## 文档父子层级规则

## 用户配置

用户说"配置 ffeishu"时，读取当前生效配置展示可配置项，用 AskUserQuestion 让用户修改，写回文件。

查找与写入位置由单一实现决定 —— **不要手写回退链**（此前每个 skill 各一份，改一处必漏其余）：

```bash
source ~/.claude/skills/ffeishu/references/plugin_env.sh
skillconf_diag                                    # 看每个键实际来自哪个源
cat "$(skillconf_file skill/ffeishu.yaml)"        # 默认配置文件的路径
```

8 级查找链（命中即用；写入写**命中的那个**，无命中时写第 5 顺位）：

```
1. $SKILLCONF_<KEY> / $FFEISHU_CONFIG   环境变量显式指定
2. $CLAUDE_PLUGIN_DATA/config.json      官方持久目录（跨 update 保留）
3. settings.json → pluginConfigs         claude plugin configure 弹窗填的
4. .credentials.json → pluginSecrets     声明 sensitive:true 的键
5. $CCPRIVATE_HOME/conf/ffeishu.yaml     自用多机同步主通道
6. $CCPRIVATE_HOME/skill/ffeishu.yaml    旧位置（兼容）
7. ~/.claude/skill-config/ffeishu.yaml   旧用户级路径（兼容）
8. <skill目录>/config.yaml               旧 symlink（兼容）
```

配置项说明见 `config.yaml.example` 注释。用户直接编辑命中的文件也可，无需重启。

---

## 参考手册