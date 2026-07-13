# aiagt 站点结构

## 仓库

```
~/git/aiagt/
├── deploy.sh              # cp base.css + git push（历史，可废弃）
├── shared/base.css         # 暗色设计系统源文件
├── .githooks/pre-commit    # 自动 sync base.css 到三站
├── sites/
│   ├── main/               → aiagt.dev
│   ├── config/             → cconf.aiagt.dev
│   └── skill/              → skills.aiagt.dev
```

## 部署机制

```
编辑 index.html → git commit → git push origin main
                                  ↓
                         CF Pages webhook 检测 push
                                  ↓
                         三个 project 各自 build
                         root_dir = sites/{main,config,skill}/
                                  ↓
                         上线到对应域名
```

**不需要 deploy.sh**。pre-commit hook 自动处理 base.css 同步。

## 三站点内容对照

### sites/main/ — aiagt.dev

品牌首页。5 个产品卡片（ccconfig、ccskills、bwater + 2 待发布）。
产品描述、生态链接。

改动频率：低。

### sites/config/ — cconf.aiagt.dev

cconfig 产品落地页。最长的文件（~497 行）。

关键区块：
- **Hero 终端模拟器**（~L140-150）：clone 命令 + 四步安装
- **痛点卡片**（3 个）：`pain_1/2/3_*`
- **功能网格**（6 个）：`feat_1~6_*`
- **使用场景**（3 个）：`uc_1/2/3_*`
- **FAQ**（5 个）：`faq_1~5_*`
- **底部 CTA**（~L320）：clone 命令副本 + bootstrap + init 流程
- **版本号**：GitHub API 自动拉最新 commit hash，不需手动更新

i18n 数据在 `<script>` 末尾的 `t.zh` / `t.en` 对象中。

### sites/skill/ — skills.aiagt.dev

15 个 skill 市场页。每个 skill 一张卡片，含图标、描述、使用场景、依赖项、安装命令。

关键区块：
- **skill 卡片列表**：`skillsData` 数组，每个 skill 的 `name/desc/use_cases/deps/install_cmd/needs_ccconfig`
- **分类过滤**：文档办公/调研分析/效率工具
- **依赖通知横幅**：`needs_ccconfig: true` 的 skill 显示绿色徽章

## 编辑注意事项

1. i18n — 中英文数据在 `<script>` 块中，改一处 HTML 模板文本也要改 `t.zh` 和 `t.en` 中的数据
2. 转义 — HTML 中 `&&` 写为 `&amp;&amp;`，`<code>` 中的内容同样要注意
3. 命令 — clone 命令在 HTML 模板和 `<script>` i18n 数据中各有一份
4. 版本号 — `loadVersion()` IIFE 从 GitHub API 拉，不需手动维护
