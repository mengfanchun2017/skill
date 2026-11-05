# Contributing

## 仓结构

```
skill/
├── .claude-plugin/marketplace.json    # 仓根入口（description 由脚本同步）
├── plugins/<skill>/                   # 自建 plugin（实体）
│   ├── SKILL.md                       # skill 描述（必须 frontmatter）
│   ├── references/                    # 可选：长文档
│   ├── scripts/                       # 可选：脚本
│   └── ...
└── www/                               # 静态展示页（部署到 skill.aiagt.dev）
```

## 新增自建 skill

1. `plugins/<name>/` 建目录
2. 写 `SKILL.md`，frontmatter 含 `name` + `description`：
   ```yaml
   ---
   name: my-skill
   description: 一句话说明（用户说什么时触发，会出现在 /plugin search 结果中）
   ---
   ```
   **`description` 是单一真相源** — marketplace.json 和 README 的描述都从这里自动同步，不需要手动复制。
3. 手动加进 `.claude-plugin/marketplace.json` 的 `plugins` 数组：
   ```json
   {
     "name": "my-skill",
     "source": "./plugins/my-skill",
     "keywords": ["f"]
   }
   ```
   **不需要写 `description`** — 运行 `python3 scripts/sync-marketplace.py --write` 自动从 SKILL.md frontmatter 填充。
4. 运行 `python3 scripts/sync-marketplace.py` 确认无漂移
   （新 plugin 是 ORPHAN 时，`--write` 会自动登记进 marketplace，不必手改 JSON）
5. 如果技能要用 `fcore`（配置解析、lark-cli 操作、格式断言），跑
   `bash ccconfig/bin/sync-plugin-env.sh` 让新 plugin 拿到 `references/_boot.sh` ——
   缺了它，`/plugin install` 装到 `cache/` 后无法跨 plugin 找到 fcore
6. 提交 PR

## 引用外部 skill

如果想引用一个公开的 skill（不是自己写的），在 marketplace.json 加：

```json
{
  "name": "external-skill",
  "description": "...",
  "source": {
    "source": "github",
    "repo": "owner/repo",
    "path": "skills/external-skill"
  },
  "version": "0.1.0"
}
```

不复制实体，**自动跟官方源同步**。

## 修改现有 skill

- 直接改 `plugins/<skill>/SKILL.md` 或其他文件
- 如果改了 frontmatter `description`，运行 `python3 scripts/sync-marketplace.py --write` 同步到 marketplace.json
- CI 会检查 marketplace.json 是否与 SKILL.md 一致（`python3 scripts/sync-marketplace.py` 非零退出 = 不同步）
- **改 shell 后必跑 `bash -n`**：Edit 跨行替换容易把多行压成一行，运行时才报错
- **SKILL.md 超过 200 行就该拆**：细则进 `references/`，命令进 `scripts/` 或 `fcore`

## 版本

每个 plugin 独立版本号。根仓版本在 `.claude-plugin/marketplace.json` 的 `metadata.version`。

## 同步脚本

`scripts/sync-marketplace.py` 负责保持 marketplace.json 与 SKILL.md frontmatter 一致：

```bash
python3 scripts/sync-marketplace.py          # 检查模式：报告漂移 + 幽灵/孤儿，有差异则 exit 1
python3 scripts/sync-marketplace.py --write  # 写入模式：用 SKILL.md description 覆盖 marketplace.json
```

**设计原则：SKILL.md 是 description 的单一真相源。** marketplace.json 只存机器特有的字段（`name`、`source`、`keywords`），description 从 SKILL.md 自动填充。新增/修改 skill 时不需要手动写 marketplace.json 的 description 字段。

## 从文档看不出来的机制

### `_boot.sh` 为什么每个 plugin 都带一份

`/plugin install` **只复制 plugin 自己的目录**。`fcore` 的实现（lib/*.sh）装在 `plugins/cache/<market>/fcore/<版本>/`，别的 plugin 装完拿不到它。

所以每个 plugin 带一份 40 行的 stub 去找实现，**实现仍然只有 fcore 一处**。stub 依次找：自己就是 fcore → 兄弟目录（git clone 布局）→ cache 布局 → `~/.claude/skills/fcore/` → `F_CORE_LIB` 环境变量。

改 fcore 的 lib 后，若要覆盖所有布局，跑 `bash ccconfig/bin/sync-plugin-env.sh`。

### `description` 为什么不能随手改格式

`sync-marketplace.py` 逐字比对。改写时多一个空格、少一个换行都会报 `DRIFT`，CI 直接红。改完必须 `--write`。

### 配置为什么不放 plugin 目录

`/plugin update` 整目录替换 `~/.claude/plugins/cache/<market>/<plugin>/<版本号>/`。写在那里的 `config.yaml` 会丢。用户自填配置落 `~/.claude/skill-config/<plugin>.yaml`（cache 之外），由 `fcore conf` 统一读写。

## 本仓与 ccconfig 的关系

本仓是**产物**（技能实体），`~/git/ccconfig` 是**安装分发层**：

| ccconfig 侧 | 作用 |
|---|---|
| `lib/init-skill.sh sync` | symlink 本仓 plugin → `~/.claude/skills/` |
| `bin/sync-plugin-env.sh` | 分发 `_boot.sh` 到所有 plugin |
| `lib/deps-check.sh` | 读各 plugin 的 `deps.txt` 装 CLI 依赖 |

私有真值在 `~/git/ccprivate/conf/<plugin>.yaml`（**不是 skill/**），本仓只放 `config.yaml.example`。

## 改完必须验证

```bash
bash -n plugins/fcore/lib/*.sh                 # 改 shell 后
python3 scripts/sync-marketplace.py            # 改 description 后
~/.claude/skills/fcore/bin/fcore where         # 确认路径解析正常
```

**shell 改动后不跑 `bash -n` 会出事**：Edit 跨行替换容易把多行压成一行，运行时才报 `[: missing ']'`。

## 常用命令

```bash
python3 scripts/sync-marketplace.py           # 检查漂移（CI 同款）
python3 scripts/sync-marketplace.py --write   # 写回 marketplace.json

cd www && python3 -m http.server 8000         # 本地预览展示页

bash ccconfig/bin/sync-plugin-env.sh          # 分发 _boot.sh 到所有 plugin
bash ccconfig/bin/sync-plugin-env.sh --check  # 只校验
```

## 新增 plugin（本机额外步骤）

建完目录后跑 `bash ccconfig/bin/sync-plugin-env.sh`，让新 plugin 拿到 `_boot.sh`（否则该 plugin 装到 cache 后无法解析配置）。`marketplace.json` 里的 `keywords` 统一写 `["f"]`。

## 许可

贡献 = 同意 MIT 协议。
