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
   description: 一句话说明（用户说什么时触发）
   ---
   ```
3. 手动加进 `.claude-plugin/marketplace.json` 的 `plugins` 数组，`source: "./plugins/<name>"`
4. 提交 PR

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
- 不用动 marketplace.json（desc 提取自 frontmatter，但目前是手动同步；可加 regen 脚本自动化）

## 版本

每个 plugin 独立版本号。根仓版本在 `.claude-plugin/marketplace.json` 的 `metadata.version`。

## 许可

贡献 = 同意 MIT 协议。
