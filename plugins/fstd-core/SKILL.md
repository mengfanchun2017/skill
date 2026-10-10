---
name: fstd-core
description: |
  飞书文档格式硬约束唯一真相源 — 标题层级、表格 XML、图表、缩写、引用等所有
  飞书文档创建的强制规则。ffeishu / fstd-report / fstd-case / fstd-course 均引用本文件，
  不再各自复制格式规则。
  用法：被其他 skill 引用，一般不直接触发
user-invocable: false
allowed-tools: Read, Glob, Grep
---

# fstd-core — 飞书文档格式硬约束（L2 共享）

**唯一真相源**：所有飞书文档的格式规则在此定义一处，其余 skill 只引用、不复制。
执行命令（lark-cli 语法/安全/验证步骤）在 `ffeishu`，本文件只定义「格式长什么样」。

> 变更本文件 = 变更全局飞书格式标准。改前确认影响面（ffeishu / fstd-report / fstd-case / fstd-course）。

## 标题

- 仅用 `# ## ###`（H1-H3），**禁止 H4+**
- **不加手动编号**（飞书自动生成目录）：禁止 `一、` `1.1` `(1)` 等前缀
- 非正文内容（使用说明、参考数据）用 `>` 引用包裹，不出现在目录
- 章节间**禁止** `<hr/>` 分割线
- **文档标题用简单连贯中文短名**（2-6 字），不带「长主语 — 解释副标题」；同项目子文档用统一短词风格

## 表格 → `<lark-table>` XML

- **禁止 Markdown 表格**，全部用 `<lark-table>` XML
- **colgroup 列宽之和 = 822**（`round(822/N)` 均分：2列→411×2, 3列→274×3, 4列→205×2+206×2, 5列→164×4+166）
- 必设属性：`rows="N" cols="N" header-row="true" header-column="true" column-widths="W,W,W"`
- 单元格内**纯文本**，不用 `#` 标题符号

## 图表

- 架构图/流程图/时序图 → `fdiagram`（Mermaid 白板）生成，`block_insert_after` 插入
- 数据/分析图（matplotlib/plotly）→ 图子文档工作流（ffeishu 工作流 G），每图独立子文档
- 图表在对应内容位置嵌入，不在文末堆砌

## 文本

- 缩写首次出现用 DFN 格式：`中文全称（English Full Name, ABBR）`
- 链接域名 `www.feishu.cn`，非 `open.feishu.cn`
- 内联样式嵌套（XML 模式）顺序（外→内）：`<a>` → `<b>` → `<em>` → `<del>` → `<u>` → `<code>` → `<span>` → text，关闭严格逆序

## 父子层级

- 子文档（用户指定父文档）→ 从 URL 提取 token 作 `--parent-token`，**禁止**套默认值
- 独立文档（未指定）→ 默认 wiki 节点（体裁注册表 `defaults.feishu_wiki_node`）

## 引用

- **执行侧**：`ffeishu`（命令语法/安全规则/写后验证）
- 内容规范侧（fstd-report / fstd-case / fstd-course）只引用本文件，不复制以上规则
