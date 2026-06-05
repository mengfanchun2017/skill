# Contributing

## 仓结构

```
claude-skills/
├── .claude-plugin/marketplace.json    # 仓根入口，**手动维护**
├── plugins/<skill>/                   # 各 skill 实体
│   ├── .claude-plugin/plugin.json     # plugin 元数据（自动推断）
│   ├── SKILL.md                       # skill 描述（必须 frontmatter）
│   ├── references/                    # 可选：长文档
│   ├── scripts/                       # 可选：脚本
│   └── ...
└── option-<name>/                     # 配套安装器（随 plugin 走）
```

## 新增 skill

1. `plugins/<name>/` 建目录
2. 写 `SKILL.md`，frontmatter 含 `name` + `description`：
   ```yaml
   ---
   name: my-skill
   description: 一句话说明（用户说什么时触发）
   ---
   ```
3. 跑 `python3 .claude-plugin/regen.py`（待补）重新生成 marketplace.json
4. 或者手动把 plugin 加进 `.claude-plugin/marketplace.json` 的 `plugins` 数组
5. 提交 PR

## 修改现有 skill

- 直接改 `plugins/<skill>/SKILL.md` 或其他文件
- 不用动 marketplace.json（desc 提取自 frontmatter）

## 版本

每个 plugin 独立版本号。根仓版本在 `.claude-plugin/marketplace.json` 的 `metadata.version`。

## 许可

贡献 = 同意 MIT 协议。
