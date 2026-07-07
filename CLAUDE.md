# CLAUDE.md — claude-skills

> Claude Code skill marketplace 聚合仓库。自建 16 个 f-* skill + 外部第三方引用。

## 目录结构

```
plugins/           # 自建 skill（每个子目录一个 skill）
  <name>/
    SKILL.md       # skill 定义（YAML frontmatter + markdown body）
    config.yaml.example  # 用户配置模板（复制为 config.yaml 填入真实值）
    deps.txt        # npm 依赖声明（格式：@package npm:version skill-name）
    references/     # 长文档引用（SKILL.md 通过路径指向）
    scripts/        # Python/bash 辅助脚本
    .gitignore      # 阻止 config.yaml 提交

.claude-plugin/
  marketplace.json  # plugin 注册表（source + name，description 从 SKILL.md 同步）

scripts/
  sync-marketplace.py  # SKILL.md frontmatter → marketplace.json 描述同步
```

## 约定

- `config.yaml` 通过 `.gitignore` 排除，真实值在用户私有仓库（ccprivate）
- `config.yaml.example` 是公开模板，含占位符
- `deps.txt` per-skill 声明 npm 依赖，`init-skill.sh` 自动安装
- `SKILL.md` frontmatter 是 `description` 唯一真相源，`sync-marketplace.py` 自动同步

## 贡献

1. 在 `plugins/<name>/` 创建 skill
2. 写 SKILL.md（YAML frontmatter: name, description, user-invocable, allowed-tools）
3. 在 marketplace.json 添加条目（source + name，描述留空由 CI 填充）
4. CI 自动校验 frontmatter + marketplace 一致性
