---
name: fsyncdoc
user-invocable: true
disable-model-invocation: true
description: Sync source repo docs + optional aiagt product page. Two-phase pipeline.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
---

# f-syncdoc — 源码文档同步 + 产品页同步

代码变更后同步文档，有对应 aiagt 产品页则顺带同步。

## 映射系统

映射关系外置，不写死在此 SKILL.md：

- **私有映射**（不提交）：`$CCPRIVATE_HOME/skill/f-syncdoc-mapping.json`
- **模板**（可提交）：`page-mapping.template.json`

加载逻辑：
- 私有映射存在 → doc sync + page sync 全开
- 不存在 → 只做 doc sync（开源用户）

`$CCPRIVATE_HOME` 默认 `~/git/ccprivate`。

### 映射格式

```json
{
  "ccconfig": {
    "repo_path": "~/git/ccconfig",
    "page": {
      "site_dir": "~/git/aiagt/sites/config",
      "domain": "config.aiagt.dev"
    }
  },
  "skill": {
    "repo_path": "~/git/skill",
    "page": {
      "site_dir": "~/git/aiagt/sites/skill",
      "domain": "skill.aiagt.dev"
    }
  },
  "aiagt": {
    "repo_path": "~/git/aiagt",
    "page": {
      "site_dir": "~/git/aiagt/sites/main",
      "domain": "aiagt.dev"
    }
  }
}
```

无 `page` 条目的 repo 只做 doc sync。

## 执行流程

### Step 0: 确定范围

加载 mapping.json 取所有源仓库列表。

无参数 → `AskUserQuestion` 勾选要同步的仓库。有参数（如 `ccconfig`）→ 直走。

### Phase 1 — Doc sync：读源码 → 更新文档

对每个选定仓库：

**1a. 读源码提取当前事实**

```bash
ls <repo_path>/
find <repo_path> -maxdepth 2 -name "*.sh" -o -name "*.py" -o -name "*.md" | sort | head -40
```

Read 关键入口文件（入口脚本、CLAUDE.md、CHANGELOG.md）。提取事实清单 — 安装步骤、功能点、配置项、CLI 命令列表、架构文件列表。

**1b. 读现有文档**

```bash
ls <repo_path>/README.md <repo_path>/BOOTSTRAP.md <repo_path>/CHANGELOG.md <repo_path>/CONTRIBUTING.md <repo_path>/docs/ 2>/dev/null
```

Read 每个存在的文档。

**1c. 对比输出差异表**

```
| 文档 | 区块 | 当前值 | 应为 | 严重度 |
```

严重度：**高**=错步骤/死链/错版本，**中**=过时描述/缺文件，**低**=文案优化。

`AskUserQuestion` 逐项确认（高严重度默认勾选）。

**1d. 应用更新**

Edit 每处过时内容。注意中英文文案同步、命令/路径双重检查。

### Phase 2 — Page sync：条件触发页面同步

加载 mapping.json → 当前仓库有 `page` 条目？

无 → 跳过。

有 → 执行页面同步：

**2a. 读目标页面**

Read `<site_dir>/index.html`，定位：
- 内联 HTML 文本（Hero 终端模拟器、CTA 按钮、功能卡片等）
- `<script>` 块中的 i18n 数据对象（`t.zh` / `t.en`）

**2b. 对比 + 检查点**

站点结构差异 → `references/aiagt-structure.md`

通用检查点：
- install 命令/步骤匹配最新源码
- 功能列表有增减
- FAQ 答案仍准确
- 域名链接（og:url、nav、footer、交叉链接）
- skill 数量 / option 列表（config）
- SKILLS 数组 vs 实际 plugin 列表（skill）
- 产品卡片描述（main）

**2c. 报告 → 确认 → 应用**

同上差异表 + Edit。注意：
- HTML 内联文本和 `<script>` i18n 数据**两处都要改**
- 转义：`&&` → `&amp;&amp;`
- 改域名时 grep 全文件

### Step 3: 提交

Phase 1 有变更：
```bash
cd <repo_path>
git add <changed files>
git commit -m "docs: sync from source code changes"
git push origin main
```

Phase 2 有变更（page 在 aiagt 仓库，与 source repo 可能不同）：
```bash
cd ~/git/aiagt
git add sites/
git commit -m "chore: sync page — <summary>"
git push origin main
```

push → CF Pages webhook → 1-2 分钟上线。pre-commit hook 自动处理 base.css 同步。

验证：
```bash
curl -s https://<domain> | grep -o '<title>.*</title>'
```

## 添加新映射

mapping.json 加一条（含 repo_path + 可选 page），本 SKILL.md 无需修改。
