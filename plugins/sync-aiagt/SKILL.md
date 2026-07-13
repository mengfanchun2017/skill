---
name: sync-aiagt
user-invocable: true
disable-model-invocation: true
description: Sync aiagt product pages with latest ccconfig state. User-invoked maintenance skill.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
---

# sync-aiagt — aiagt 产品页同步

当 ccconfig 有结构性变更（安装流程、功能列表、skill 数量、FAQ）后，同步到 aiagt 三个 CF Pages 站点。部署 = git push，CF Pages webhook 自动上线。

## 站点映射

| 站点 | 域名 | 对应 ccconfig 内容 |
|------|------|-------------------|
| `sites/config/` | cconf.aiagt.dev | README 安装步骤、功能列表、FAQ |
| `sites/skill/` | skills.aiagt.dev | skill 列表、依赖标记、安装命令 |
| `sites/main/` | aiagt.dev | 品牌首页（较少变更） |

完整结构 → `references/aiagt-structure.md`

## Step 1: 收集 ccconfig 当前真相源

读这三个文件，提取关键事实：

```bash
# ~/git/ccconfig/
Read README.md     # 安装步骤、功能数量、option 列表、skill 表
Read BOOTSTRAP.md  # 四步流程、前置条件
```

提取并记录：
- 安装命令序列（clone / bootstrap / init-ccprivate / init.sh all）
- bootstrap.sh 支持的环境变量
- 自建 skill 数量（`## 自建 Skills` 表的行数）
- option 组件列表
- 功能描述要点（一键恢复、公私分离、auto-sync 等）

## Step 2: 对比 aiagt 目标页面

读每个 aiagt 页面的 `<script>` 块中的 i18n 数据对象（`const t = { zh: {...}, en: {...} }`），对比 Step 1 提取的事实：

**sites/config/index.html** — 检查点：
- `step_1_title/cmd` / `step_2_title` / `step_3_title` — 安装步骤是否匹配当前流程
- `feat_N_title/desc` — 功能描述是否过时
- `faq_N_q/a` — FAQ 答案是否仍准确
- `clone-box` 中的 `git clone` 命令
- `hero` 区域的 skill 数量、功能数量

**sites/skill/index.html** — 检查点：
- skill 卡片列表 vs ccconfig README 自建 Skills 表
- `needs_ccconfig` 标记是否准确
- 安装命令格式

**sites/main/index.html** — 检查点：
- 产品卡片数量和描述

## Step 3: 报告 + 确认

列出所有过时项，格式：

```
| 页面 | 区块 | 当前值 | 应为 | 影响 |
```

用 `AskUserQuestion` 逐项确认是否更新。用户可能想跳过某些项。

## Step 4: 应用更新

对确认的项，直接 Edit `index.html` 中对应文本。i18n 数据在 `<script>` 块的 `t.zh` 和 `t.en` 对象中，**中英双语都要改**。

关键编辑规则：
- HTML 内联文本和 `<script>` 中的 i18n 数据**两处都要更新**
- `clone-box` 中的命令在 HTML 模板和 `<script>` 的 `t.zh.step_1_cmd` 中各有副本
- 改命令字符串时注意转义：`&amp;&amp;` = `&&`

## Step 5: 部署

```bash
cd ~/git/aiagt
git add sites/
git commit -m "chore: sync aiagt pages with ccconfig $(
  cd ~/git/ccconfig && git rev-parse --short HEAD
)"
git push origin main
```

pre-commit hook 自动处理 `shared/base.css` 同步。push 后 CF Pages webhook 自动部署，1-2 分钟生效。

**验证**：等 2 分钟后跑：
```bash
curl -s https://cconf.aiagt.dev | grep -o '<title>.*</title>'
```

## 部署 FAQ

**Q: 需要 deploy.sh 吗？**  
A: 不需要。deploy.sh = cp base.css + git push。pre-commit hook 已自动 sync base.css，直接 git push 效果相同。

**Q: CF Pages 怎么触发？**  
A: aiagt 的三个 CF Pages project 绑定 GitHub `mengfanchun2017/aiagt` main 分支，push 自动 build。`sites/<name>/` 目录内容直接 serve。
