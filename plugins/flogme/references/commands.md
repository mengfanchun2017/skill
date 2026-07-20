# flogme 命令速查

## 环境变量

从 `config.yaml` 读取 Base token / 表 ID / lark-cli 配置目录：

```bash
T=$(python3 -c "import yaml; c=yaml.safe_load(open('config.yaml')); print(c['bases']['okr_v2']['token'])")
T_O=$(python3 -c "import yaml; c=yaml.safe_load(open('config.yaml')); print(c['bases']['okr_v2']['tables']['O'])")
T_KR=$(python3 -c "import yaml; c=yaml.safe_load(open('config.yaml')); print(c['bases']['okr_v2']['tables']['KR'])")
T_WL=$(python3 -c "import yaml; c=yaml.safe_load(open('config.yaml')); print(c['bases']['okr_v2']['tables']['Worklog'])")
T_RF=$(python3 -c "import yaml; c=yaml.safe_load(open('config.yaml')); print(c['bases']['okr_v2']['tables']['Reflect'])")
LARKDIR=$(python3 -c "import yaml; c=yaml.safe_load(open('config.yaml')); print(c['lark_cli']['config_dir'])")

export LARKSUITE_CLI_CONFIG_DIR="$HOME/$LARKDIR"
export PATH="$HOME/.local/bin:$PATH"
```

## 拉取 Base 数据

```bash
# 默认 table 格式（人类可读），--format json 用于程序化解析
lark-cli base +record-list --base-token $T --table-id $T_O --as user
lark-cli base +record-list --base-token $T --table-id $T_KR --as user
lark-cli base +record-list --base-token $T --table-id $T_WL --as user --limit 200
lark-cli base +record-list --base-token $T --table-id $T_RF --as user
```

**JSON 输出格式**（`--format json`）：响应结构为 `data.data`（记录数组）+ `data.fields`（字段名数组）。
每条记录是数组（按 fields 顺序），不是 dict。解析方式：

```python
data = json.loads(output)
fields = data['data']['fields']
for rec in data['data']['data']:
    d = dict(zip(fields, rec))  # 转为 dict 使用
```

**分页**：`--limit` 最大有效值约 200。`has_more: true` 时用 `--offset N` 继续拉取。flag 是 `--base-token` 不是 `--app-token`。

## log_write.py 数据写入

```bash
SCRIPT="python3 ${CLAUDE_PLUGIN_ROOT}/log_write.py"

# 写 worklog
$SCRIPT worklog --title "完成 X" --kr recXXXX --type "项目交付" --note "..." --date 2026-06-12

# 写 reflect（含批量关联 KR，仅写入关联字段，不改 KR.状态）
$SCRIPT reflect --title "Q2 W3" --period "周" \
  --good "..." --improve "..." --learned "..." --next "..." \
  --batch-kr recXXX recYYY --date 2026-06-12

# 改 KR.状态（Active → Done / Cancelled 时手动跑）
$SCRIPT kr-status --kr recXXXX --status Done
```

**设计原则**：
- worklog/reflect 只写入对应表，不联动其他表 / 字段
- KR 状态推进靠用户主动判断，不靠累积量自动涨
- 量化指标（最终评分）改在季度末手填 KR.最终评分 字段

## SUM 生成流程

### Step 1: 导出数据

```bash
D=/tmp/sum_$(date +%s) && mkdir -p $D
lark-cli base +record-list --base-token $T --table-id $T_O --as user --format json --limit 200 2>&1 | sed '/^\[lark-cli\]/d' > $D/okr_o.json
lark-cli base +record-list --base-token $T --table-id $T_KR --as user --format json --limit 200 2>&1 | sed '/^\[lark-cli\]/d' > $D/okr_kr.json
lark-cli base +record-list --base-token $T --table-id $T_WL --as user --format json --limit 200 2>&1 | sed '/^\[lark-cli\]/d' > $D/worklog.json
lark-cli base +record-list --base-token $T --table-id $T_RF --as user --format json --limit 200 2>&1 | sed '/^\[lark-cli\]/d' > $D/reflect.json
```

### Step 2: 生成 Markdown

```bash
# 周期总结（Q2 工作）
python3 ${CLAUDE_PLUGIN_ROOT}/sum_generate.py \
  --okr-o $D/okr_o.json --okr-kr $D/okr_kr.json \
  --worklog $D/worklog.json --reflect $D/reflect.json \
  --period 2026Q2 --category work --type period \
  --output $D/summary.md

# 领域总结（AI 领域）
python3 ${CLAUDE_PLUGIN_ROOT}/sum_generate.py \
  --okr-o $D/okr_o.json --okr-kr $D/okr_kr.json \
  --worklog $D/worklog.json --reflect $D/reflect.json \
  --type domain --domain learn --year 2026 \
  --output $D/summary.md

# OKR 复盘
python3 ${CLAUDE_PLUGIN_ROOT}/sum_generate.py \
  --okr-o $D/okr_o.json --okr-kr $D/okr_kr.json \
  --worklog $D/worklog.json --reflect $D/reflect.json \
  --period 2026Q2 --type okr-review \
  --output $D/summary.md

# 年度综合报告
python3 ${CLAUDE_PLUGIN_ROOT}/sum_generate.py \
  --okr-o $D/okr_o.json --okr-kr $D/okr_kr.json \
  --worklog $D/worklog.json --reflect $D/reflect.json \
  --type annual --year 2026 \
  --output $D/summary.md
```

### Step 3: 委托 ffeishu 创建飞书文档

flogme 不自己调 `lark-cli docs +create`。将生成的 Markdown 交给 ffeishu skill，由 ffeishu 统一编排 lark-cli 创建飞书文档。ffeishu 自动处理表格宽度（822px）、标题层级（≤H3）、文档父目录等格式化规则（详见 ffeishu skill 格式约束）。
