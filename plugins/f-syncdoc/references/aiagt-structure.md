# aiagt 站点结构

## 仓库

```
~/git/aiagt/
├── deploy.sh              # cp base.css + git push（可废弃，pre-commit hook 已覆盖）
├── shared/base.css         # 暗色设计系统源文件
├── .githooks/pre-commit    # 自动 sync base.css 到三站
├── sites/
│   ├── main/               → aiagt.dev
│   ├── config/             → config.aiagt.dev
│   └── skill/              → skill.aiagt.dev
```

## 部署

```
编辑 index.html → git commit → git push origin main
                                  ↓
                         CF Pages webhook
                                  ↓
                         三个 project build
                         root_dir = sites/{main,config,skill}/
                                  ↓
                         上线
```

不需要 deploy.sh。pre-commit hook 自动处理 base.css 同步。

## 三站点详解

### sites/config/ — config.aiagt.dev

源仓库：`~/git/ccconfig`

关键区块：
- Hero 终端模拟器（~L140-150）：clone 命令 + 四步安装
- 痛点卡片 3 个：`pain_1/2/3_*`
- 功能网格 6 个：`feat_1~6_*`
- 使用场景 3 个：`uc_1/2/3_*`
- FAQ 5 个：`faq_1~5_*`
- 底部 CTA（~L320）：clone 命令副本 + 安装流程
- 版本号：`loadVersion()` → GitHub API commit hash（自动，不需手动维护）

i18n 数据在 `<script>` 末尾 `t.zh` / `t.en`。

### sites/skill/ — skill.aiagt.dev

源仓库：`~/git/claude-skills`

关键区块：
- `SKILLS` 数组（~L244-260）：每个 skill 的 id/name/icon/cat/needs_ccconfig/desc_zh/desc_en/scenarios_zh/scenarios_en/deps
- 安装命令：`/plugin marketplace add`、`/plugin install`
- 依赖通知横幅：工具依赖标签
- 生态系统流程图

**SKILLS 数组是手工快照**，与 `claude-skills/plugins/` 无代码耦合。加新 skill 后必须手动更新此数组。

i18n 数据在 `<script>` 末尾 `t.zh` / `t.en`。

### sites/main/ — aiagt.dev

源仓库：`~/git/aiagt`（自身）

关键区块：
- 5 个产品卡片：ccconfig / ccskills / bwater + 2 个 Coming Soon
- 产品描述、域名链接、标签

改动频率最低。主要检查域名一致性和产品文案。

## 编辑注意事项

1. i18n — 中英文数据在 `<script>` 块中，改 HTML 内联文本也要改 `t.zh` 和 `t.en`
2. 转义 — HTML 中 `&&` → `&amp;&amp;`
3. 域名 — 改域名时 grep 全文件所有出现位置
4. 命令 — clone 命令在 HTML 模板和 `<script>` i18n 数据中各有一份副本
5. 版本号 — `loadVersion()` 自动拉 GitHub API，不需手动维护
