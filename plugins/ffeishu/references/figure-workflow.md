# 图子文档工作流（数据/分析图）

> 架构图/流程图/时序图委托 fdiagram（飞书画板，就地嵌入）。
> 本文件只覆盖**数据/分析图**（matplotlib/plotly）：每个图建独立子文档，父文档只放链接。
> 内容规范见 `../../fstander-report/references/chart-guide.md`。

## 工作流 G: 图子文档生成（数据/分析图）

> 架构/流程图委托 fdiagram。本工作流用于**数据/分析图**（matplotlib/plotly）：每个图建独立子文档。
> 内容规范见 `../fstander-report/SKILL.md`，触发见 `../forch-report/SKILL.md` 工作流 G。

### 完整流程

```
父文档（已有）
  ↓ G.1 写 python 脚本 → /tmp/figs/<名>.py
  ↓ G.2 跑脚本 → /tmp/figs/<名>.png
  ↓ G.3 创建子文档（含图/解读/代码 3 段）
  ↓ G.4 父文档 block_insert_after 嵌入图块
父文档（含图嵌入 + 详见子文档链接）
```

### Step G.1: 写 python 脚本

```python
# /tmp/figs/<图名>.py
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC']  # 中文
plt.rcParams['axes.unicode_minus'] = False  # 负号

fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
# ... 数据 + 绘图 ...
plt.tight_layout()
plt.savefig('/tmp/figs/<图名>.png', dpi=150, bbox_inches='tight')
print('✅ /tmp/figs/<图名>.png')
```

```bash
python3 /tmp/figs/<图名>.py
```

### Step G.2: 验证图生成

```bash
ls -la /tmp/figs/<图名>.png
file /tmp/figs/<图名>.png  # 确认 PNG
```

### Step G.3: 创建子文档（3 段式）

子文档用 lark-cli docs +create，**父文档 token 作为 --parent-token**：

```bash
PARENT_TOKEN="<父文档 URL 或 token>"
FIG_NAME="<图名，简洁中文>"

cat << EOF | lark-cli docs +create --api-version v2 \
  --parent-token "$PARENT_TOKEN" --as user \
  --title "$FIG_NAME" --doc-format markdown --content -

# $FIG_NAME

## 图

![$FIG_NAME](attachment://<图名>.png)

> 详细解读见下文

## 解读

> 此处填写图的分析：数据来源、对比维度、关键洞察、注意点、不确定项

- 关键发现 1
- 关键发现 2
- 关键发现 3
- 不确定项：[待确认] / [数据有限]

## 代码

\`\`\`python
# 完整可重跑的 python 脚本
$(cat /tmp/figs/<图名>.py)
\`\`\`

EOF
```

**输出**：子文档 URL 和 token（保存到父文档嵌入步骤）。

### Step G.4: 父文档嵌入图块

**先 fetch 父文档拿到 block 结构**：

```bash
lark-cli docs +fetch --api-version v2 --doc "$PARENT_TOKEN" --detail with-ids
```

**找到要插入位置的 block_id**（如 `<target_block_id>`），用 `block_insert_after` 嵌入子文档链接：

```bash
CHILD_TOKEN="<子文档 token>"
CHILD_URL="<子文档 URL>"

# 在目标 block 后插入图块（链接到子文档）
cat << EOF | lark-cli docs +update --api-version v2 \
  --doc "$PARENT_TOKEN" --as user --mode block_insert_after \
  --block-id "<target_block_id>" --doc-format markdown --content -

**$FIG_NAME**：详见 [$FIG_NAME]($CHILD_URL)

EOF
```

**关键原则**：
- **绝不复制图到父文档**（飞书是引用，子文档 = 唯一源）
- 父文档用 `block_insert_after` 不能用 `str_replace`（避免破坏嵌入资源）
- **多步操作必须串行**（并行触发版本冲突）

### Step G.5: 验证

```bash
lark-cli docs +fetch --api-version v2 --doc "$PARENT_TOKEN" --detail full | grep -c "$FIG_NAME"
# 期望：≥ 1
```

### 常见错误

| 错误 | 原因 | 修复 |
|------|------|------|
| `media-insert` 路径错 | 路径必须相对 git 根目录 | `cd <git 根> && lark-cli drive +upload` |
| `block_insert_after` 找不到 block | block_id 错了 | 重 fetch 带 `--detail with-ids` |
| 子文档父目录错 | `--parent-token` 用了 doc token 而非 wiki node | 父文档 URL 提取的 token 即 wiki node |
| 中文乱码 | matplotlib 字体未设 | `plt.rcParams['font.sans-serif']=['Noto Sans CJK SC']` |

### 命名约定

- 子文档名 = 图名（简洁中文，与正文用语一致）
- `/tmp/figs/<图名>.{py,png}` 命名一致（`占比分析.py` → `占比分析.png`）

---

## 工具委托速查