# 能力框架模板 — capability → skill → knowledge

> 用于把课程/领域知识沉淀为「能力地图」多维表格（如 baframework）。
> 语义依据 **SFIA / ISO IEC 24773**。模板不含真实 token（token 在项目 config）。

## 三层语义（SFIA）

| 层 | 定义 | 证据 | 命名 | 入表 |
|----|------|------|------|------|
| knowledge | **懂**：facts/concepts/principles，acquired 但未必应用 | 能 explain/describe | 名词短语 | **否** |
| skill | **能做**：apply knowledge 有效完成 task | 有产出/可展示 | 名词短语 | 是 |
| capability | **可靠交付**：在专业情境下负责地应用 knowledge+skill | 持续成功 + 问责 | 能力域 | 是（父级） |

SFIA 官方：skill 描述是 **technology/vendor-neutral、名词短语**（如 "Availability management"）；SFIA 的 skill 列表**不含 knowledge**——knowledge 是 level 的 generic attribute，具体知识交行业 Bodies of Knowledge。**这是 knowledge 不入表、写进 skill 文档的权威依据。**

## capability 划分维度（择一，保持全程一致）

| 维度 | 切法 | 适合 |
|------|------|------|
| 分析类型 | 描述/诊断/预测/规范 | 教学、能力阶梯 |
| 分析流程/生命周期 | 问题框定→数据→建模→部署→治理（INFORMS CAP 7 域） | 岗位、项目 |
| 能力域 | 业务框定/数据管理/统计建模/可视化/沟通… | 通用能力地图（**推荐，融合前两者**） |

## 飞书表设计（多维表格）

**表 1：能力框架表**
- `知识点` (text) —— 主字段（capability 与 skill 都填名称）
- `知识点说明` (text)
- `父记录` (**link 自引用本表**) —— capability 行留空，skill 行的父记录指向其 capability
- `关联课程` (**link → courselist 表**) —— 多对多
- `相关课程` (text) —— 多行文本，写 courselist 对应单元文本（冗余便于查阅）
- `文档链接` (url) —— 该行的知识库文档（capability/skill 共用一列，靠父子行区分）
- 编号 (auto_number)

**表 2：课程表（courselist）**
- `课程名称` (text) —— 主字段。**层级行必须给不同值**：课程根行=课程名，单元行=`Week N: <主题>`
- `父记录` (link 自引用) —— 单元行指向课程根行；课程根行留空
- `周次` (number, 整数) 等单元标识
- `关联知识点` (**link → 能力框架表**) —— 双向；仅单元行填，课程根行不填
- `参考附件` (attachment) —— 该单元下载材料

## 层级展示（飞书关键）

- 飞书多维表格**无原生树视图**；默认网格是平铺的。
- 建 `父记录` 自引用后，**建一个"按父记录分组"的视图**（`view-set-group`，group by 父记录）即可看到层级。
- **主字段必须能区分行**：若所有行主字段都是同一个课程名，网格看起来就是 10 条一样的平铺行——层级不明显。给单元行填 `Week N: …` 即可。
- 多对多：双向关联字段自动生成反向列；反向列不可改型/删。

## 双向关联（n-n）要点

- capability↔skill：自引用 `父记录`（同表）
- framework↔courselist：`关联课程`↔`关联知识点` 双向；**反向列是自动生成的**
- 一个知识点可挂多门课程、一门课覆盖多知识点 = n-n
- **改一边会覆盖另一边**：反向列由"上游"写入。若知识点行也关联课程根行，课程根行的关联知识点会被自动补回——所以**知识点只挂单元行**，课程根行不挂

## 落地工作流（可复用）

1. 建表 schema（`field-create`：link 字段用 top-level `link_table`，非 `property.table_id`）
2. 建记录：`record-batch-create`（`create_records` 数组）
3. 建父子：`record-batch-update`（`update_records` map，`父记录:[{"id":...}]`）
4. 建关联：同上，`关联课程:[{"id":...}]`
5. 附件：`record-upload-attachment`（--file，cwd//tmp/~/files 内）
6. 分组展示：`view-set-group`
7. 坑：无 `record-create`（用 upsert）；`record-delete` 需 `--yes`；url 字段值传字符串

## 命名

- capability / skill：名词短语，中文（或双语）
- 保持同一 cap 下 skill 的粒度一致；数量不限，逻辑优先
