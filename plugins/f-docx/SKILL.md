---
name: f-docx
user-invocable: true
description: |
  Word .docx 原生生成 — OfficeCLI 引擎，支持模板/样式/表格/图片/页眉页脚/目录。
  Use when 用户说"创建Word"/"写Word文档"/"生成docx"/"导出Word"/"做简历"/"写报告docx"。
allowed-tools: Read, Write, Bash, Glob
---

# f-docx — OfficeCLI Word 生成

从零或模板生成 .docx 文件。OfficeCLI 单引擎，零外部依赖。

## 安装

```bash
curl -fsSL https://d.officecli.ai/install.sh | bash
```

---

# OfficeCLI Word 引擎

## 核心命令

```bash
# 创建空白 DOCX
officecli create report.docx

# 打开文件（启动常驻进程，加速后续操作）
officecli open report.docx

# 查看结构
officecli get report.docx / --depth 2 --json
officecli query report.docx body --json

# 添加段落
officecli add report.docx /body --type paragraph \
  --prop text="标题文字" --prop bold=true --prop size=28

# 添加表格
officecli add report.docx /body --type table --prop rows=3 --prop cols=4

# 批量模式（推荐）
officecli batch report.docx --input doc_commands.json

# 查看/验证
officecli view report.docx text
officecli validate report.docx

# 关闭
officecli close report.docx
```

## 批量模式示例

```json
[
  {"command": "add", "parent": "/body", "type": "paragraph", "props": {"text": "第一章 概述", "bold": true, "size": 28}},
  {"command": "add", "parent": "/body", "type": "paragraph", "props": {"text": "正文内容..."}},
  {"command": "add", "parent": "/body", "type": "table", "props": {"rows": 3, "cols": 4}}
]
```

## 设计系统

### 字体对

| 用途 | 中文 | 英文 | 说明 |
|------|------|------|------|
| 标题 | 微软雅黑 | Calibri | 正式报告 |
| 标题 | 思源黑体 | Georgia | 创意文档 |
| 正文 | 宋体 | Times New Roman | 学术/正式 |
| 正文 | 微软雅黑 | Calibri | 商业/通用 |

### 字号层级

| 元素 | 字号 | 加粗 | 对齐 |
|------|------|------|------|
| 文档标题 | 28pt | bold | center |
| 一级标题 | 22pt | bold | left |
| 二级标题 | 18pt | bold | left |
| 三级标题 | 14pt | bold | left |
| 正文 | 12pt | — | justify |
| 表格内容 | 10pt | — | left |
| 页眉页脚 | 9pt | — | center |

### 色板

| 主题 | 主色 | 辅色 | 适用 |
|------|------|------|------|
| 经典蓝 | `1F4E79` | `D6E4F0` | 商业报告、简历 |
| 深灰 | `333333` | `F2F2F2` | 极简、技术文档 |
| 学术黑 | `000000` | `FFFFFF` | 论文、正式信函 |

### 页面设置

```
A4: 21cm × 29.7cm
边距: 上下 2.54cm, 左右 3.18cm (Word 默认)
边距(窄): 上下 1.27cm, 左右 1.27cm
```

---

## 常用工作流

### 工作流 A: 创建报告

```
1. officecli create report.docx
2. officecli open report.docx
3. 批量添加: 标题 → 目录占位 → 章节标题 → 正文 → 表格
4. 页眉页脚: 页码、公司名
5. officecli validate report.docx
6. officecli close report.docx
```

### 工作流 B: 从模板创建

```bash
officecli create report.docx --template ~/templates/report.docx
officecli open report.docx
# 替换占位符文本
officecli set report.docx ... --prop text="实际内容"
```

### 工作流 C: 简历

```
1. 选择字体对: 微软雅黑 + Calibri
2. 色板: 经典蓝
3. 结构: 个人信息 → 教育背景 → 工作经历 → 技能 → 项目
4. 单页原则（~800字）
```

---

## QA 检查清单

- [ ] `officecli validate` 通过
- [ ] 字体一致（不超过 2 种）
- [ ] 标题层级正确（H1→H2→H3）
- [ ] 表格有表头、对齐一致
- [ ] 无 placeholder 残留
- [ ] 页码正确

## 帮助

```bash
officecli help docx              # 列出所有 docx 元素
officecli help docx paragraph    # 段落属性
officecli help docx table        # 表格属性
officecli help docx add paragraph --json  # JSON schema
```

> 详细参考: officecli skill（`~/.claude/skills/officecli/SKILL.md`）
