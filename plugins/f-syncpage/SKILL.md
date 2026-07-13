---
name: f-syncpage
user-invocable: true
disable-model-invocation: true
description: Sync aiagt product pages from source repos. User-invoked maintenance skill.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
---

# f-syncpage — aiagt 产品页同步

源仓库有结构性变更后，同步到 aiagt 对应产品页。通用 skill，支持多组源→目标映射。部署 = `git push`，CF Pages webhook 自动上线。

## 映射表

| 源仓库 | aiagt 站点 | 域名 | 检查重点 |
|--------|-----------|------|---------|
| `~/git/ccconfig` | `sites/config` | config.aiagt.dev | 安装命令、功能列表、FAQ、skill 数 |
| `~/git/claude-skills` | `sites/skill` | skill.aiagt.dev | skill 数组、依赖标记、安装命令 |
| `~/git/aiagt` | `sites/main` | aiagt.dev | 产品卡片、域名链接（低频） |

站点详细结构 → `references/aiagt-structure.md`

## Step 1: 确定范围

问用户同步哪些映射（单选/多选）。默认：全部检查。

## Step 2: 读源仓库真相

按选定的映射，读对应源仓库的关键文件：

**ccconfig 源**：
```
Read ~/git/ccconfig/README.md     → 安装步骤、功能列表、option 表、skill 表
Read ~/git/ccconfig/BOOTSTRAP.md  → 四步流程、环境变量
```

**claude-skills 源**：
```bash
ls ~/git/claude-skills/plugins/   → skill 目录列表
```
读每个 `plugins/<name>/SKILL.md` 的 frontmatter → 提取 name、description

**aiagt 源**（自身变更少，通常只检查域名一致性）：
```
Read ~/git/aiagt/README.md        → 产品列表、域名
```

提取事实清单 — 只记录在目标页面中以硬编码形式出现的数据。

## Step 3: 读 aiagt 目标页面

读对应 `sites/<name>/index.html`，定位 `<script>` 块中的 i18n 数据对象和硬编码内容，与 Step 2 事实清单逐项对比。

**cconfig → sites/config** 检查点：
- `step_N_title/cmd` — 安装步骤顺序是否正确
- `feat_N_title/desc` — 功能描述是否过时
- `faq_N_q/a` — FAQ 答案是否仍准确
- clone 命令格式
- 域名链接（og:url、nav、footer、交叉链接）
- skill 数量、option 列表

**claude-skills → sites/skill** 检查点：
- `SKILLS` 数组 vs `ls plugins/` 实际 skill 列表 — 新增/删除的 skill
- 每个 skill 的 `needs_ccconfig` 标记是否准确
- 安装命令格式（`/plugin marketplace add`、`/plugin install`）
- 域名链接

**aiagt → sites/main** 检查点：
- 产品卡片 vs `README.md` 产品列表
- 域名链接
- 占位产品数

## Step 4: 报告 + 确认

列出所有差异，格式：

```
| 站点 | 区块 | 当前值 | 应为 | 严重度 |
```

严重度：**高**=死链/错命令，**中**=过时描述/数量不对，**低**=文案优化。

`AskUserQuestion` 逐项确认（高严重度默认勾选）。

## Step 5: 应用更新

Edit `index.html` 中对应文本。关键规则：
- HTML 内联文本和 `<script>` i18n 数据 **两处都要改**
- 转义：`&&` → `&amp;&amp;`
- 改域名时检查所有出现位置（og:url、nav、hero CTA、feature links、footer）

## Step 6: 部署

```bash
cd ~/git/aiagt
git add sites/
git commit -m "chore: sync pages — $(cat /tmp/syncpage-summary)"
git push origin main
```

pre-commit hook 自动 sync `shared/base.css`。push 后 CF Pages 自动部署，1-2 分钟生效。

验证（按本次涉及的站点选）：
```bash
curl -s https://config.aiagt.dev | grep -o '<title>.*</title>'
curl -s https://skill.aiagt.dev  | grep -o '<title>.*</title>'
```

## 添加新映射

后续有新仓库绑定到 aiagt 站点，在"映射表"加一行 + 在 Step 2/3 加对应检查点即可。结构不改。
