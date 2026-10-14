---
name: fworch-case
user-invocable: true
description: |
  案例库编排器。维护飞书 wiki 三层案例库 + Base 元数据，按关键词/专业领域检索案例，
  新增/更新案例时搜索整理生成正文，fetch 案例主文档内容注入课程上下文。
  内容规范（schema/起名/正文模版）见 fwstd-case。
  用法：用户说"案例库"/"案例"/"补充案例"/"推荐案例"/"新增案例"触发
allowed-tools: Read, Bash, Glob, Grep
---

# fworch-case — 案例库编排器（L3）

职责：维护飞书 wiki 三层案例库 → 按需检索 → fetch 案例正文 → 返回 chunks 给调用方。
通信契约 → `references/comm-contract.md`；通用契约 → `fworch/references/orchestrator-contract.md`
内容规范（Base schema / 起名规则 / 正文模版）在 **`fwstd-case`**，本 skill 只管编排。

**数据源**：飞书 wiki 空间（2026-09-26 重构：字段 23→15、wiki 三层、起名规则）。

> **真值全部在 `ccprivate/conf/writing/case.yaml`**（私有，不进公开仓库）：base_token / table_id / view_id / wiki_root_node / space_id / tenant_domain。
> 运行时通过共享层 `lark_conf_get writing/case.yaml <key>` 读取并导出为 `$FCASELIB_BT/TID/VIEW`（见 `references/lark_env.sh`）。公开仓库零真实值。

---

## 数据存储架构（wiki 三层，2026-09-26 定）

```
飞书 wiki 空间
├── caselib（多维表格 = 案例数据库，wiki 根节点 = $CASELIB_WIKI_ROOT）
│   └── 每记录 = 一个案例的元数据（字段见 fwstd-case）
└── 案例正文层（wiki 子节点，挂在 caselib 下）
    ├── Starbucks-RFM与客户分层-忠诚度      ← 案例主文档（docx，第2层）
    │   └── Starbucks-RFM与客户分层-忠诚度-漏斗图  ← 子文档（第3层，含 python 代码+图）
    └── GE Aviation-数字孪生-预测性维护     ← 案例主文档（docx，第2层）
```

- 第1层 = caselib 多维表格本身；第2层 = 案例主文档（docx）；第3层 = 主文档子文档（图表/代码/扩展材料）
- 「案例主文档」字段存第2层 docx 的 wiki URL

---

## 调用接口

```
fworch-case(query=<关键词>, professional=<可选专业领域>)
```

#### 稳定工具层（recommended 起点）

source 本文件打包账号前缀 + auth 预检 + 输出净化 + 打分检索。**绝对路径 source**：
```bash
source ~/.claude/skills/fworch-case/references/lark_env.sh
```
- `lark_auth_check` — auth 预检，失败 return 1（通用工具，另见 ffeishu/references/lark_env.sh）
- `lark_call <cmd...>` — 透传 lark-cli，剥离 `[lark-cli]` 日志行
- `fworch-case_search <query> [professional] [limit]` — 检索 + 打分调度，直接出 JSON 行
- 变量：`FCASELIB_BT/TID/VIEW`、`FCASELIB_SCORE_THRESHOLD`（默认 20）、权重 `FCASELIB_W_*`
- **原则**：脚本只保证前缀/预检/输出干净，不重写官方命令。lark-cli 更新 → 只改本文件命令段。

#### 检索流程（走 `fworch-case_search`，自动降级）

```bash
source ~/.claude/skills/fworch-case/references/lark_env.sh
fworch-case_search "<query>" "<professional>" <limit>   # limit 默认 3
```
调度逻辑（脚本内已实现）：
- **库 ≤20 条**（当前 5 条）：`+record-search --keyword` 全文检索 + 可选 `--filter-json` 过滤，直接返回记录
- **库 >20 条**：拉全量 → 每案例打分降序取前 3（`专业领域`=3 分、`分析方法/模型`=2 分、关键词=1 分）
  - 输出 JSON 行（`case_name/company/domain/methods/summary/url/record_id/score`），url 是案例主文档 wiki 链接

#### auth 预检（写操作/fetch 前必做，失败终止）

```bash
source ~/.claude/skills/fworch-case/references/lark_env.sh && lark_auth_check || echo "AUTH_FAILED"
```
预检失败 → 提示走飞书 QR 授权流程（`rules/feishu.md` § 预检），不在失败时硬闯。

#### 返回格式

```yaml
query: "RFM"
professional: "个性化推荐"
chunks:
  - id: "case-001"            # 命中次序：case-001..case-00N
    title: "Starbucks-RFM与客户分层-忠诚度"
    summary: "..."            # fetch 切片后的案例原文
    url: "https://..."        # 主文档 wiki url，调用方用于注入可点击引用
    record_id: "recXXX"       # Base 记录 id（溯源用）
```

#### 失败处理

- Base 不可访问 / auth 失败 → 终止，提示授权
- 无命中 → `{chunks: []}`，调用方提示无匹配
- 单个 fetch 失败 → 丢弃该 doc 继续；全部失败 → `{error: "fetch_failed"}`

---

## 新增案例（你给材料 → 搜索整理生成）

**触发**：用户说"新增案例"+ 提供材料（链接/文档/描述）。
**流程**：材料预处理 → `/fsearch` 搜索扩展 → 生成主文档 + 子文档 → 建 wiki 三层 → 回填 Base。
**正文结构与写作要求**：严格按 `fwstd-case` 的「案例正文模版」。

0. **材料预处理**：原始材料（本地 PDF/Word/PPT 或 URL）先转 markdown：
   - **本地文件 / PDF URL** → MinerU 解析（`references/mineru_parse.py`）
   - **网页 URL** → Tavily extract / Exa fetch 优先；MinerU `crawl` 补充（国内可达、需结构保留时）
   - **纯文字描述** → 直接进 `fsearch`
1. **搜索扩展**：`fsearch` 补充背景/数据/图表源，扩展内容作主文档单独一节。
2. **命名**：按 `fwstd-case` 起名规则算标题。
3. **建正文（第2层主文档）**：按 `fwstd-case` 正文模版写 → `docs +update --command overwrite --doc <url> --content @file.md --doc-format markdown` 整文替换。
4. **拆子文档（第3层）**：图表/代码拆独立子文档，标题 = 主文档标题 + `-内容名`。
5. **建 wiki 层级**：
   - 主文档移入 caselib wiki：`wiki +move --obj-token <token> --obj-type docx --target-parent-token "$CASELIB_WIKI_ROOT" --target-space-id "$CASELIB_SPACE_ID" --as user`
   - 子文档挂主文档：`--target-parent-token` 用主文档 node_token
   - 改名：`drive +update-title --token <node_token> --type wiki --title "<新标题>" --as user`
6. **回填 Base 记录**：见下方 JSON（字段与选项见 `fwstd-case`，⚠️ 字段名 `案例名称`、编号 auto_number 不写）。

### MinerU 解析（材料预处理标准工具）

> 官方 MinerU API（mineru.net），PDF/Word/PPT/图片/网页 → Markdown。≤20页/≤10MB 走免费 Flash，>20页走 Precision（token）。
> 脚本依赖由 uv 自管（PEP 723），不依赖系统 python 的 mineru 包。

```bash
uv run ~/.claude/skills/fworch-case/references/mineru_parse.py "<本地路径>.pdf"
uv run ~/.claude/skills/fworch-case/references/mineru_parse.py "https://example.com/article"
uv run ~/.claude/skills/fworch-case/references/mineru_parse.py "<file>" --force-precision
# 直接执行也行（shebang 走 uv）: ~/.claude/skills/fworch-case/references/mineru_parse.py <file>
```
- 输出 markdown 到 stdout；`--outdir DIR` 存图；debug（mode/pages/chars）到 stderr
- token 在 `ccprivate/conf/mineru.json`（脚本自动读，勿硬编码）
- 需 uv（`bash ccconfig/lib/ensure-uv.sh` 一键装）
- 境外站（github/aws/wikipedia）超时→网页优先 Tavily/Exa
- 表格 → 飞书原生表格；图/公式 → 第3层子文档

### 回填 Base（新增）

```bash
lark-cli base +record-batch-create --base-token "$FCASELIB_BT" \
  --table-id "$FCASELIB_TID" --json '{
    "create_records": [{
      "案例名称": "Starbucks-RFM与客户分层-忠诚度",
      "公司": "Starbucks", "行业": ["零售","快消"], "地区": ["北美"], "案例年份": 2024,
      "专业领域": ["个性化推荐"], "业务职能": ["市场","IT/数据"],
      "案例类型": ["数字化转型","业务增长"], "分析方法/模型": ["RFM","聚类"],
      "摘要": "- 公司/业务：...\n- 分析动作：...\n- 目标：...",
      "数据源链接": "[来源标题](url)", "案例主文档": "[...](wiki url)",
      "案例状态": ["已上线"]
    }]
  }' --as user
```
⚠️ select 值必须是 field 现有选项（`+field-list` 先查），写错报 `not_found`。

---

## 案例更新版（原资料过老 → 生成新版报告）

**触发**：用户说"案例原链接太老/有新进展，写更新版"。

1. **深度搜索**：tavily/exa 搜相关主题最新（近1-2年）新闻与分析。
2. **命名**：`{YYYYMMDD} {公司}-{动作}-{目标}`（YYYYMMDD = 最新关键事件日期）。
3. **建正文**：严格按 `fwstd-case` 正文模版。
4. **挂原案例下**：`docs +create --title "<标题>" --content @file.md --doc-format markdown --parent-token <原案例 node_token> --as user`。
5. **回填 Base**：新建记录，案例年份 = 新日期年份，「案例主文档」填新 wiki URL。
6. 更新版与原案例并存。

## 更新现有案例

- 定位：给 record 分享链接 → `+url-resolve` 解出 record_id → `+record-get`
- 更新记录：`+record-batch-update` 按 record_id 改字段
- 更新正文：改 wiki 主文档后回填「案例主文档」URL
- ⚠️ select 字段值必须是现有选项

## 定位 record（用户给行链接）

```bash
lark-cli base +url-resolve --url "<record 分享链接>" --as user
# 返回 base_token + table_id + record_id(recXXX) + record_share_token
```

---

## 检索注意事项（推荐引擎友好）

- `+record-search --keyword` 全文匹配，中英文均生效；select 多选字段选项名也能被命中
- 精确维度过滤（专业领域/案例类型/行业）用 `+record-list --filter-json`（**不用 `+record-search --filter-json`**，flag 模式无 `--keyword` 报错）：
  ```bash
  lark-cli base +record-list --base-token "$FCASELIB_BT" \
    --table-id "$FCASELIB_TID" \
    --filter-json '{"logic":"and","conditions":[["专业领域","==","个性化推荐"]]}' \
    --field-id "案例名称" --field-id "专业领域" --format json --as user
  ```
- 当前策略 = `fworch-case_search` 自动降级（≤20 关键词+filter，>20 全量打分），阈值/权重可用 env 覆盖

---

## 维护速查

| 操作 | 命令 |
|------|------|
| 看字段/选项 | `+field-list --format json` |
| 新增字段 | `+field-create --json '{"name":"..","type":".."}'` |
| 删字段 | `+field-delete --field-id ".." --yes` |
| 改字段名/选项 | `+field-update --field-id ".." --json '完整定义' --yes` |
| 列顺序 | `+view-set-visible-fields --view-id "$FCASELIB_VIEW" --json '{"visible_fields":[...]}'` |
| 移 docx 进 wiki | `wiki +move --obj-token <t> --obj-type docx --target-parent-token <p> --target-space-id <sp>` |
| wiki 节点改名 | `drive +update-title --token <node> --type wiki --title "<新>"` |
| 查 node / 子节点 | `wiki +node-get --node-token <t>` / `wiki +node-list --space-id <sp> --parent-node-token <p>` |
| record 链转坐标 | `base +url-resolve --url <链接>` |

---

## 迁移记录

- 2026-09-24：从本地 YAML 全量迁至飞书 Base
- 2026-09-26：结构重构（字段 23→15 + wiki 三层）
- 2026-10-10：`fcaselib` → `fworch-case`（编排）+ `fwstd-case`（内容规范）拆分

---

## 依赖

- `references/lark_env.sh` — 稳定工具层（auth 前缀/预检/输出净化/打分检索）
- `references/mineru_parse.py` — 材料解析
- `fwstd-case` — 内容规范（schema/起名/正文模版）
- `ffeishu` — 飞书文档操作
- `fsearch` — 新增案例搜索扩展
- 调用协议由 fworch-course 的 `references/case-protocol.md` 约束
