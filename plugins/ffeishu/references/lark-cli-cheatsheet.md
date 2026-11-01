# lark-cli 速查

> 完整踩坑记录 → `skills/ffeishu/references/lark-cli-cheatsheet.md`

## 运行前缀

**从 marker 读取当前账号目录**（`lark-switch.sh` 维护，切账号自动跟随）：

```bash
export LARKSUITE_CLI_CONFIG_DIR="$(grep '^configDir=' ~/.lark-cli-account | cut -d= -f2)" && export PATH="$HOME/.local/bin:$PATH"
```

⚠️ 不要写死 `~/.lark-cli`——该目录不存在。当前默认账号 ailab 实际目录是 `~/.lark-cli-ailab`（appId `cli_a97077...`），`lark-switch.sh ailab -p` 会写入 marker `~/.lark-cli-account`。
⚠️ 不要用 `"${LARKSUITE_CLI_CONFIG_DIR:-...}"` 回退默认——env 若已被设成错误目录会静默生效不报错。

## auth 预检（写操作前必做）

```bash
lark-cli drive +search --query test --page-size 1 --as user 2>&1 | sed '/^\[lark-cli\]/d'
```

若 `token_missing` → token 过期。完整授权流程见 feishu.md § auth 预检（QR 码 + scope）。

## 命令速查

| 命令 | 关键 flag | 易错 |
|------|----------|------|
| `docs +create` | `--doc-format markdown --content "..."` | `--markdown` 已废弃，用 `--doc-format markdown` |
| `docs +update` | v2: `--command overwrite\|block_insert_after\|str_replace\|block_delete` + `--content` | `--command` 不是 `--mode` |
| `docs +fetch` | v2: `--detail full\|with-ids\|simple` | full 含 colgroup width |
| `whiteboard +update` | `--source @file.mmd --input_format mermaid` | mermaid 不支持 subgraph |
| `whiteboard +query` | `--output_as image\|code\|raw --output ./` | **下划线** `--output_as`；`--output` 必须相对路径 |
| `base +table-create` | `--name --fields '<json-array>'` | 不是 `--json` |
| `base +field-create` | `--json '{"field_name":"X","type":"select","options":[...]}'` | type 是字符串；options 在顶层 |
| `base +field-update` | `--json '{"name":"X","type":"select","options":[...]}' --yes` | 全量 PUT 语义；select 改 options **必须用这个**，raw API 会 validation failed |
| `base +field-update` (number) | `api PUT .../fields/{id} --data '{"field_name":"X","type":2,"property":{"formatter":"0"}}'` | number 改 formatter **必须 raw API**，`+field-update` 不认 `property` |
| `auto_number → number` | `+field-update --json '{"name":"X","type":"number"}' --yes` | 转换后手动设值；auto_number 不可重置/手动改值 |
| `base +record-batch-create` | `--json '{"fields":[],"rows":[[]]}'` | link: `[{"id":"recXXX"}]` |
| `base +record-update` | **不存在** → raw API: `lark-cli api PUT .../records/{id} --data '{"fields":{...}}'` | |
| `base +record-list` | `--base-token X --table-id Y --format json --limit 200` | flag 是 `--base-token` 不是 `--app-token`；默认 table 格式，程序化解析需 `--format json`；limit 最大有效值 200，超 200 条需 `--offset` 分页 |
| `base +record-search` | `--keyword X --search-field Y` | 返回 `record_id_list`；`+record-list` 不返回 record_id |
| `slides +create` | `--title --slides '<json-array>'` | 在线 vs 导入 PPTX API 能力差很多 |
| `slides 导出` | `api POST export_tasks --data '{"type":"slides","token":"X","file_extension":"pptx"}'` | 不是 `drive +export` |
| `drive +upload` | `--folder-token --file "./rel"` | 必须相对路径，先 cd |
| `drive +export-download` | `--file-token --file-name` | 必须相对路径 |
| `wiki +node-get` | `--token "URL"` 或 `--node-token` + `--obj-type` | 支持 URL |

## 文件上传 / 下载（实测 2026-10-06）

### 下载两通道（附件 vs Drive 文件）

| 文件来源 | 命令 | 结果 |
|----------|------|------|
| **Drive 里的文件**（`+upload` 上传的） | `drive +download --file-token <token> --output ./x` | ✅ 直接可用 |
| **doc 内嵌附件**（`<figure><source token=.../>`） | `drive +download --file-token <token>` | ❌ HTTP 403 `token lookup failed` |
| **doc 内嵌附件**（正确通道） | `drive +preview --file-token <token> --type source_file --output ./x` | ✅ 拿到原始文件 |

**结论**：凡 URL/文档里引到的文件（附件块），一律走 `+preview --type source_file`；普通 Drive 文件才用 `+download`。

### 上传大小限制：严格 20MB

- 实测 19MB → ✅ ok；21MB → ❌ `1061043 file size beyond limit`
- **边界 = 20MB**（`drive/v1/files/upload_all` 上限）
- lark-cli help 声称 `>20MB 自动 multipart`，**实测不生效**——超过 20MB 直接报 1061043
- 官方大文件通道是 `multipart-upload-file` 预上传，但 lark-cli 未暴露对应子命令
- **结论**：>20MB 的文件 lark-cli 传不了，需换通道（压缩/直接给路径/换同步盘）

### zip 等二进制文件

- 上传/下载全通道可用，`+download` 下载后字节完整（zipfile.testzip 通过）
- 文件类型无限制，zip/docx/图片同待遇

### 追加附件块到文档底部

```bash
lark-cli docs +update --api-version v2 --doc <doc_token> --as user --command append --doc-format xml \
  --content '<figure view-type="Preview"><source token="<file_token>" name="<显示名>"/></figure>'
```

- `--command append`（v2，不再是 `--mode`）
- `<source token=...>` 复用已上传的 Drive 文件；`name=` 可任意改名
- 删除 Drive 文件（**必须带 `--params '{"type":"file"}'`**，否则 99992402 validation failed）：
  `lark-cli api DELETE /open-apis/drive/v1/files/{token} --params '{"type":"file"}'`

## 关键约束

- **含嵌入资源（白板/图片/电子表格）禁止 overwrite** — 只能用 str_replace / block_insert_after / block_delete
- **@file 路径必须相对当前目录** — `cd /tmp && --content @./file.md`（必须有 `@` 前缀，否则当字符串字面量）
  - ❌ `--content "./file.md"` → 文档内容变成字符串 "./file.md"
  - ✅ `--content @./file.md` → 读文件内容
- **跨租户无法访问** — 不同域名文档需导出本地处理
- **docs +create 必显式 `--title`** — 否则默认 "Untitled"，事后只能 str_replace 改
- **docx 删除**：`lark-cli api DELETE /open-apis/drive/v1/files/{token} --params '{"type":"docx"}'`
- **colgroup 修复**：用 `block_replace` 替换整个 table（不能用 str_replace 处理 `<colgroup>`）
- **base select 值**：必须用目标字段已有选项，不能想当然传字符串
- **lark-cli stdout**：WSL 会注入 `Shell cwd was reset to <path>` 行 → python json.loads 前过滤
- **`api` 子命令不输出 JSON**：`lark-cli api GET/POST/...` 输出人类可读日志行（如 `[fldmwAFw2J] 编号  type=1005  opts=[]`），**不要** pipe 给 `python3 -c "json.load(sys.stdin)"` → 报 `AttributeError: 'NoneType' object has no attribute 'get'`。只有显式带 `--format json` 的子命令（如 `base +record-list --format json`）才输出 JSON

## base +record-list JSON 输出格式

`--format json` 时输出结构：

```json
{
  "ok": true,
  "data": {
    "fields": ["标题", "说明", "日期", ...],
    "field_id_list": [...],
    "data": [
      ["标题值", "说明值", "2026-06-15 00:00:00", ...],
      ...
    ],
    "has_more": true,
    "record_id_list": ["recXXX", ...]
  }
}
```

**关键**：
- 记录在 `data.data`（不是 `data.records`）
- 每条记录是数组，按 `data.fields` 顺序排列，不是 dict
- `has_more: true` 时用 `--offset` 分页（limit 最大有效值 ~200）
- Python 解析：`fields = data['data']['fields']; for rec in data['data']['data']: d = dict(zip(fields, rec))`

## base 字段操作（实测 2026-10-31）

### 建 link / lookup 的 JSON（唯一正确写法）

```bash
# link（双向）
--json '{"name":"X","type":"link","link_table":"tbl...","bidirectional":true,"bidirectional_link_field_name":"反向名"}'

# lookup（四要素 from/select/where/aggregate）
--json '{"name":"Y","type":"lookup","from":"tbl...","select":"字段名",
         "where":{"logic":"and","conditions":[["源表字段","intersects",{"type":"field_ref","field":"本表link字段"}]]},
         "aggregate":"max"}'
```

- ❌ `{"type":21,"property":{"table_id":"tbl..."}}` → `800010701 Invalid discriminator value`（同 Base 也失败）
- ✅ 必须用 `"type":"link"` + `"link_table"` 平铺写法
- `from` 写 **table_id 最稳**；写表名有时 `800030104 not_found`（改过字段的表尤其）
- 建 lookup 需 `--i-have-read-guide`；`+field-create` **不吃 `--yes`**（只有 `+field-update` 吃）

### lookup 的 where 三个坑

1. **`conditions: []` 空数组被拒** → `800010701 Array must contain at least 1 element(s)`
2. **侥幸建成空条件 → 整列恒空且 API 全 success**，看起来像"确实没数据"，必须读回记录对账
3. **跨类型匹配静默返回空**：源表存 text `"1"`、本表是 number `1` → `is` 永远空。必须另存同类型字段做匹配键

`aggregate` 取值（**全小写 snake_case**）：`raw_value` / `sum` / `average` / `max` / `min` / `counta`（不是 `count`）/ `unique_counta` / `unique`。

### 改字段必须传完整定义

只传 `{"name":"新名"}` 改 link/lookup → `800010701`。因为改名接口走的是同一套 `type` 判别，缺字段就判不出来：

```bash
# link 改名：带 link_table + bidirectional
--json '{"name":"新名","type":"link","link_table":"tbl...","bidirectional":true,"bidirectional_link_field_name":"反名"}'

# lookup 改名：带 from + select + where + aggregate
--json '{"name":"新名","type":"lookup","from":"tbl...","select":"原字段","where":{...},"aggregate":"max"}'
```

- 反向字段（`bidirectional_link_field_name` 生成的那个）**不能改名** → `unsafe_operation_blocked: Updating a link field type, bidirectional setting, or duplex target table is not supported`

### 跨 Base 关联的唯一正解：共享数据源同步表

link/lookup 的 `from` **硬限同 Base**，拿别 Base 的 table_id 建一律 `800010701`。

解法是「共享数据源 → 同步成主 Base 内的只读表」：

| 步骤 | 操作 | 能否 API |
|---|---|---|
| 1. 发布 | 源 Base 表名右侧 `⋮ 更多操作 → 发布为共享数据源`（**不是**右上角分享按钮） | ❌ 纯 UI |
| 2. 接入 | 目标 Base 左下 `新建 → 导入/同步数据 → 连接器中心 → 管理数据源 → 组织共享数据源` | ❌ 纯 UI |
| 3. 同步表落地 | 目标 Base 多出一张带闪电图标的只读表 | — |
| 4. 建 link | `link_table` 指向该同步表的 table_id | ✅ |

**关键认知**（易误判，务必记牢）：

- **同步表只读的是「数据行」，表本身可以当 link 目标**。往同步表加记录 → `800080821 unsafe_operation_blocked`；但建 link 指向它 → 成功，反向字段自动生成在同步表侧。不要因为"只读"就放弃这条路。
- **退化的是「行内关联字段的值」，不是 link 能力**。源侧 link/lookup 同步后变文本（如逗号拼接 `"4,5"`），只影响跨表反查，不影响当字典查。
- **只发布不接入 = 目标 Base 里什么都不出现**，`is_synced` 也一直是 None。必须两步都做完。

同步机制：每小时一次；超 10 天未浏览目标 Base → 降 24 小时；超 30 天 → **自动关闭，需手动重开**。同步表可加新字段（number/text/formula 都行），同步不覆盖自建字段。

发布/接入无 OpenAPI：`/syncs`、`/datasources`、`/tables/{id}/sync`、`/bases/{t}/publish`、`/shared_data_sources` 实测全 404。

### 同步表上的取值限制

同步表只读，多值文本（`"4,5"`）无法精确拆：

- 数字字段 vs 文本 → 静默空
- `intersects` 文本对文本 → **误匹配**，`"101"/"10"/"11"` 都含 `"1"`
- formula `FIND` 精确拆 → 恒为 1，无效
- 拆行 → 只读，加不了记录

能用的只有：加 number 列做精确匹配（仅命中单值行），或改用 `aggregate: max/unique` 走 link 聚合（推荐）。

### 导出文件污染仓库（高频事故）

`+record-list` 把 ndjson 落到 **cwd**。若 cwd 是 git 仓库且 auto-sync 在跑，30 秒内被推上远程。

- 文件名两种形态：**按 table_id 调用** → `tblXXX_<日期>_<时间>_<序号>.ndjson`；**按表名调用** → `<表名>_<日期>_<时间>_<序号>.ndjson`
- `.gitignore` **只挡 `tbl*` 会漏**表名形态（`oKR_` / `worklog_`），必须加时间戳模式

```gitignore
tbl*_*.ndjson
*_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9][0-9][0-9]_[0-9][0-9][0-9].ndjson
*.manifest.json
```

- 操作前 `cd /tmp`（或 `~/files/<project>/`），别在仓库根跑

### 其他必知

- `+record-batch-update` 的 JSON 是 `{"update_records":{"recX":{"字段":[值]},...}}`，**不是** `{"records":[{record_id,fields}...]}`
- `+record-batch-create` 用 `{"fields":[...],"rows":[[...]]}`，link 值传 `[{"id":"recX"}]`
- 反向字段/`+field-delete` 需 `--yes`；`+table-delete --yes`
- 同步表判断：`api GET /open-apis/bitable/v1/apps/{token}/tables` 里看 `is_synced`；但同步表在该接口常返回 `is_synced: None`，改用名称/闪电识别或直接查表名
- **裸 `lark-cli api` 缺 scope**：查记录类端点会 `99991679 missing_scope`（要 `bitable:app:readonly` 等）。优先用 `base +record-list` 等 shortcut，它们走已授权的 scope
