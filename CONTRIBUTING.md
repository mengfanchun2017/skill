# Contributing

## 仓结构

```
claude-skills/
├── .claude-plugin/marketplace.json    # 仓根入口，**手动维护**
├── plugins/<skill>/                   # 自建 plugin（实体）
│   ├── SKILL.md                       # skill 描述（必须 frontmatter）
│   ├── references/                    # 可选：长文档
│   ├── scripts/                       # 可选：脚本
│   └── ...
├── plugins/skill-template/            # 脚手架（开发用）
└── option-<name>/                     # 配套安装器（随 plugin 走）
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
5. 提交 PR

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

## 版本

每个 plugin 独立版本号。根仓版本在 `.claude-plugin/marketplace.json` 的 `metadata.version`。

## 同步脚本

`scripts/sync-marketplace.py` 负责保持 marketplace.json 与 SKILL.md frontmatter 一致：

```bash
python3 scripts/sync-marketplace.py          # 检查模式：报告漂移 + 幽灵/孤儿，有差异则 exit 1
python3 scripts/sync-marketplace.py --write  # 写入模式：用 SKILL.md description 覆盖 marketplace.json
```

**设计原则：SKILL.md 是 description 的单一真相源。** marketplace.json 只存机器特有的字段（`name`、`source`、`keywords`），description 从 SKILL.md 自动填充。新增/修改 skill 时不需要手动写 marketplace.json 的 description 字段。

## 许可

贡献 = 同意 MIT 协议。
