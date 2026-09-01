---
name: fskillcreat
description: 创建新 Skill，问公开/私有，生成骨架，注册 symlink
---

# fskillcreat — 创建新 Skill

交互创建流程。先问用户选择，再执行。创建完成后自动注册到 `~/.claude/skills/`。

## 创建流程

### 1. 问归属

用户没说就主动问：

> 这个 skill 放公开（`~/git/skill/plugins/`，随 skill 仓库分发）还是私有（`~/git/ccprivate/skill-local/`，仅自己用）：
>
> 1) 公开
> 2) 私有

用户明确说了"公开"/"私有"则跳过提问。

### 2. 问名称

小写英文 + 数字，无空格，不用横线（skill 目录名无横线惯例）。示例：`fsample`。

### 3. 创建目录骨架

```
<source>/<name>/
  ├── SKILL.md         # 必选
  ├── deps.txt         # 可选，CLI 工具依赖
  └── config.yaml.example  # 可选，配置模板
```

公开路径：`~/git/skill/plugins/<name>/`
私有路径：`~/git/ccprivate/skill-local/<name>/`

### 4. 写 SKILL.md

基于用户对 skill 功能的描述，生成初始 SKILL.md，包含：

- **frontmatter**：`name`、`description` 中文字段
- **正文**：描述 skill 做什么、调用方式、步骤
- 不加多行 docstring 或注释块

参考 `fskillcreat GLOSSARY.md` 里的设计原则（leading word、completion criterion、progressive disclosure）来组织内容。简单 skill 不要过度设计。

### 5. 注册 symlink

```bash
bash ~/git/ccconfig/lib/init-skill.sh link-single <name>
```

### 6. 同步 marketplace（公开 skill）

如果是公开 skill，调 marketplace.json 同步：

```bash
cd ~/git/skill && python3 scripts/sync-marketplace.py --write
```

### 7. 最终提示

输出创建的完整路径和下一步：

- 公开：`cd ~/git/skill && git add . && git commit -m "feat: <name>" && git push`
- 私有：`cd ~/git/ccprivate && git add . && git commit -m "feat(skill-local): <name>" && git push`

## 设计参考

Skill 的本质是给随机系统注入确定性。**Predictability** — agent 每次走同样的 _process_，不是同样的 _output_ — 是根美德。

完整设计原则见 [`GLOSSARY.md`](GLOSSARY.md)，包括：

- **Invocation**：model-invoked vs user-invoked 选择
- **Information hierarchy**：步骤 / 内联参考 / 外部参考三层
- **Leading words**：用紧凑概念锚定行为
- **Failure modes**：premature completion、duplication、no-op