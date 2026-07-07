---
name: f-xlsx
user-invocable: true
description: |
  Excel .xlsx 原生生成 — OfficeCLI 引擎，支持公式/图表/条件格式/数据透视表/多工作表。
  Use when 用户说"创建Excel"/"做表格"/"生成xlsx"/"导出报表"/"数据透视表"/"画图表(Excel)"。
allowed-tools: Read, Write, Bash, Glob
---

# f-xlsx — OfficeCLI Excel 生成

从零或模板生成 .xlsx 文件。OfficeCLI 单引擎。

## 安装

```bash
curl -fsSL https://d.officecli.ai/install.sh | bash
```

---

# OfficeCLI Excel 引擎

## 核心命令

```bash
# 创建空白 XLSX
officecli create data.xlsx

# 打开文件
officecli open data.xlsx

# 查看结构
officecli get data.xlsx / --json
officecli query data.xlsx sheet --json

# 写入单元格
officecli set data.xlsx "/sheet[1]/cell[A1]" --prop value="标题" --prop bold=true --prop size=14

# 设置列宽
officecli set data.xlsx "/sheet[1]/column[A]" --prop width=15

# 批量模式（推荐）
officecli batch data.xlsx --input xl_commands.json

# 查看/验证
officecli view data.xlsx values
officecli validate data.xlsx

# 关闭
officecli close data.xlsx
```

## 批量模式示例

```json
[
  {"command": "add", "parent": "/", "type": "sheet", "props": {"name": "销售数据"}},
  {"command": "set", "path": "/sheet[1]/cell[A1]", "props": {"value": "月份", "bold": true}},
  {"command": "set", "path": "/sheet[1]/cell[B1]", "props": {"value": "销售额", "bold": true}},
  {"command": "set", "path": "/sheet[1]/cell[A2]", "props": {"value": "2026-01"}},
  {"command": "set", "path": "/sheet[1]/cell[B2]", "props": {"value": 150000, "format": "#,##0"}},
  {"command": "set", "path": "/sheet[1]/cell[A3]", "props": {"value": "2026-02"}},
  {"command": "set", "path": "/sheet[1]/cell[B3]", "props": {"value": 180000, "format": "#,##0"}},
  {"command": "set", "path": "/sheet[1]/cell[B4]", "props": {"formula": "=SUM(B2:B3)"}}
]
```

---

## 设计系统

### 表格样式预设

| 样式 | 表头背景 | 表头文字 | 数据行 | 边框 |
|------|---------|---------|--------|------|
| 经典蓝 | `1F4E79` | white, bold | zebra `F2F7FB`/white | thin `D0D0D0` |
| 极简灰 | `333333` | white, bold | white | thin `E0E0E0` |
| 学术 | `000000` | white, bold | white | thin `000000` |

### 数字格式

| 类型 | Format | 示例 |
|------|--------|------|
| 整数 | `#,##0` | 1,234 |
| 小数 | `#,##0.00` | 1,234.56 |
| 百分比 | `0.0%` | 85.3% |
| 金额 | `¥#,##0.00` | ¥1,234.56 |
| 日期 | `yyyy-mm-dd` | 2026-07-07 |

### 列宽约定

- 中文文本: 字符数 × 2 字符宽度
- 数字: 10-15 字符宽度
- 日期: 12 字符宽度

---

## 常用工作流

### 工作流 A: 数据报表

```
1. officecli create report.xlsx
2. 添加工作表: 原始数据 / 汇总 / 图表
3. 写入表头（bold + 背景色）
4. 写入数据行（zebra stripe）
5. 汇总表: SUM/AVERAGE/COUNT 公式
6. 添加图表: officecli add ... --type chart
7. officecli validate report.xlsx
8. officecli close report.xlsx
```

### 工作流 B: 对比表

```
1. 多列并排对比
2. 条件格式: 高亮差异 >10%
3. 冻结表头行
4. 自动筛选
```

### 工作流 C: 清单/台账

```
1. 首行冻结（表头）
2. 自动筛选
3. 下拉选择: 数据验证
4. 日期列统一格式
```

---

## QA 检查清单

- [ ] `officecli validate` 通过
- [ ] 数字列格式统一（不会 150000 和 150,000 混用）
- [ ] 表头有加粗 + 背景色
- [ ] 无 `#REF!` / `#VALUE!` 公式错误
- [ ] 列宽适配内容（无 `###` 截断）
- [ ] 打印区域设置（如需打印）

## 帮助

```bash
officecli help xlsx              # 列出所有 xlsx 元素
officecli help xlsx cell         # 单元格属性
officecli help xlsx chart        # 图表属性
officecli help xlsx add chart --json  # JSON schema
```

> 详细参考: officecli skill（`~/.claude/skills/officecli/SKILL.md`）
