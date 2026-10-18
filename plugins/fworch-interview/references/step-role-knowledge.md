# Step 2 专业知识地图

> 面试线 Step 2。产出《<岗位>-专业知识地图》。目的：把岗位所需的专业知识**系统化、分块**，零经验者据此建立完整知识框架。

## 输入
- JD/任职要求（`requirement_doc_url`）
- 岗位画像 + 组织行业（fetch）

## 输出
飞书子文档《<岗位>-专业知识地图》。返回按 `comm-contract.md`。

## 方法
按 **SFIA 三层**（capability→skill→knowledge）拆解岗位知识域（见 `fwstd-interview` + `fwstd-course/references/framework-template.md`）：

1. **从 JD 抽取职责动词**（如"机队规划""引进评估""退役处置"），聚成 capability
2. 每个 capability 下展开 skill（可执行动作）
3. 每个 skill 下写 knowledge 要点（概念/规章/方法/工具）
4. 标 **掌握程度**：入门/熟悉/精通（对照 9B 级别定位）

## 机队管理专员示例域（实际以 JD 为准）
- 民航基础知识（适航、航线、机型）
- 机队规划（引进/退出决策、机队结构）
- 飞机引进（选型、租赁 vs 购买、交付）
- 资产管理（飞机价值、折旧、残值、租赁结构）
- 维修工程基础（工程管理、适航指令 AD、时寿件）
- 运营经济性（油耗、利用率、座位经济性）
- 规章合规（民航局 CCAR 相关）
- 数字化工具（机队管理系统、数据分析）

## 流程
1. 从 JD + 行业搜索补齐每个 knowledge 要点
2. 用表格 XML 呈现"能力域 × 掌握程度 × 关键知识点"（`<table>`+`<colgroup>`，格式见 ffeishu）
3. 建飞书子文档；返回

## 依赖
fsearch / ffeishu
