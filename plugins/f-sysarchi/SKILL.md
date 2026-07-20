---
name: fsysarchi
user-invocable: true
description: |
  [personal] 系统分析师/系统架构设计师备考 — 随工作边做边学。暗号 "archi" 触发。
  Use when 用户说"archi"/"系统分析师"/"备考"/"出题"/"grill"，
  或想在日常工作中嵌入考试知识点学习。
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch, AskUserQuestion
---

# f-sysarchi — 系统分析师/架构师随工备考

> [personal] 本 skill 为个人备考定制。目标: 2027 上半年软考系统分析师。学习内容与特定项目（ccconfig）耦合，其他用户需自行适配。

## 核心理念

**不是刷题，是映射**。把日常发生的每个工作——写 PRD、画架构图、做接口规范——映射到考试知识点。考试考的是你做过的、理解透的东西。

## 暗号

说 **archi** 即可触发。具体模式：

| 暗号 | 模式 | 行为 |
|------|------|------|
| `archi` | 学习透镜 | 当前任务自动关联考试知识点，指出"你现在做的这件事对应考试哪个章节" |
| `archi grill` | 随机测验 | 从已映射的知识点中出 3-5 道选择题/简答题，考完后判分讲解 |
| `archi grill <topic>` | 定向测验 | 从指定知识点出题（如 `archi grill 需求工程`） |
| `archi map` | 知识点映射 | 回顾最近的工作，列出"你已经覆盖了哪些考点、还缺哪些" |
| `archi progress` | 进度报告 | 显示备考进度（按考纲章节的覆盖率 + 掌握度评估） |
| `archi learn <topic>` | 深度学习 | 三源并行搜索 + 生成该知识点的学习笔记（飞书文档） |

## 考试大纲

软考「系统分析师」考试科目:

### 科目 1: 系统分析师综合知识（选择题，150 分钟）

| 章节 | 权重 | 核心知识点 |
|------|------|-----------|
| 1. 计算机系统知识 | 中 | CPU/存储/IO/操作系统/文件系统 |
| 2. 计算机网络与分布式系统 | 中 | OSI/TCP/IP/分布式/云计算/中间件 |
| 3. 数据库系统 | 高 | 关系DB/设计范式/SQL/数据仓库/NoSQL |
| 4. 企业信息化 | 中 | ERP/CRM/BI/业务流程重组/企业集成 |
| 5. 软件工程 | 高 | 生命周期/开发模型/过程管理/重用/产品线 |
| 6. 项目管理 | 高 | 范围/进度/成本/质量/人力/风险/配置管理 |
| 7. 信息安全 | 中 | 安全体系/加密/访问控制/容灾/冗余 |
| 8. 系统规划与分析 | 高 | 项目选择/问题分析/流程分析/数据流分析/可行性分析 |
| 9. 软件需求工程 | **极高** | 需求获取/分析/规格说明/验证/管理 |
| 10. 系统设计 | 高 | 架构设计/详细设计/接口设计/设计模式 |
| 11. 系统测试与维护 | 高 | 测试策略/用例设计/白盒黑盒/回归测试 |
| 12. 系统运行与维护 | 中 | 运维管理/变更管理/服务台/SLA |
| 13. 新技术 | 中 | 云计算/IoT/大数据/AI/区块链 |

### 科目 2: 系统分析师案例分析（简答题，90 分钟）
- 需求分析案例分析
- 系统设计案例分析
- 项目管理案例分析
- 数据库设计案例分析

### 科目 3: 系统分析师论文（论文，120 分钟）
- 需求工程实践
- 系统分析与设计方法
- 项目管理实践
- 新技术应用实践

## 工作→考点自动映射

当用户在 ccconfig 做实际工作时，f-sysarchi 自动指出对应的考试知识点：

| 工作内容 | 对应考点（科目1章节） |
|---------|------------------|
| 写/改 PRD（docs/prd.md） | 9. 软件需求工程（需求获取→分析→规格说明→验证） |
| 写/改 架构文档（docs/architecture.md） | 10. 系统设计（架构设计） |
| 写/改 ADR（docs/adr/） | 10. 系统设计（架构决策）+ 6. 项目管理（配置管理） |
| 写/改 接口规范（docs/interface-spec.md） | 10. 系统设计（接口设计） |
| 写/改 ATAM 评估（docs/architecture-evaluation.md） | 10. 系统设计（架构评估） |
| 写/改 术语表（docs/glossary.md） | 9. 软件需求工程（文档管理） |
| 写/改 ROADMAP | 6. 项目管理（范围管理、进度管理） |
| 写/改 CHANGELOG | 12. 系统运行与维护（变更管理） |
| 写/改 BOOTSTRAP | 8. 系统规划与分析（可行性分析） |
| 写 Bash 脚本（init.sh, update.sh 等） | 5. 软件工程（开发环境与工具） |
| 安全相关（SECURITY.md, pre-commit hook） | 7. 信息安全（访问控制、安全管理） |
| 飞书集成（option-bridge, f-feishu） | 4. 企业信息化（企业应用集成） |
| monitor.sh 守护进程 | 12. 系统运行与维护（运维管理） |
| 写 Skill（SKILL.md） | 5. 软件工程（软件重用） |
| python-requirements.txt 管理 | 1. 计算机系统知识（软件环境） |
| MCP 服务器管理 | 2. 计算机网络与分布式系统（中间件/Web服务） |

## Grill 模式

**出题原则**：
1. 优先从用户**最近做过的工作**对应的考点出题（有实战经验，更容易理解）
2. 题目带场景（"你在写 PRD 时定义了用户画像，这在考试中对应..."）
3. 选择题 + 简答题混合
4. 判分后讲解答题思路 + 关联的实战经历

**题库来源**：
- 历年真题（2018-2025）
- 根据用户实际工作场景改编
- 软考官方教材《系统分析师教程》（清华大学出版社）

**示例**：
```
🔍 archi grill 需求工程

Q1 [选择题] 你在 ccconfig PRD 中写的"用户画像"章节，在软件需求工程中属于:
A. 功能需求  B. 非功能需求  C. 涉众分析  D. 验收标准

Q2 [简答] 你写的"核心场景（Use Cases）"对应需求工程的哪个阶段？
这个阶段的输出物是什么？你在 PRD 中有没有遗漏？

Q3 [场景题] 假设 ccconfig 要增加"团队配置共享"功能。
请用结构化分析方法，画出该功能的数据流图（DFD）的顶层图和 0 层图。
```

## 进度追踪

进度数据存于 `config.yaml`（非 .example，含真实进度数据，放 ccprivate 覆盖）：

```yaml
exam:
  target: "2027-Q2"  # 目标考试时间
  subject: "系统分析师"  # 或 "系统架构设计师"

progress:
  "1. 计算机系统知识": {covered: false, confidence: 0}
  "2. 计算机网络与分布式系统": {covered: false, confidence: 0}
  "3. 数据库系统": {covered: false, confidence: 0}
  "4. 企业信息化": {covered: true, confidence: 4}  # 飞书集成相关工作覆盖
  "5. 软件工程": {covered: true, confidence: 4}     # bash 脚本/skill 开发覆盖
  "6. 项目管理": {covered: true, confidence: 3}     # ROADMAP/CHANGELOG 覆盖
  "7. 信息安全": {covered: true, confidence: 4}     # SECURITY/pre-commit 覆盖
  "8. 系统规划与分析": {covered: true, confidence: 3} # BOOTSTRAP/ROADMAP 覆盖
  "9. 软件需求工程": {covered: true, confidence: 4}  # PRD 覆盖
  "10. 系统设计": {covered: true, confidence: 4}     # architecture/ADR/ATAM 覆盖
  "11. 系统测试与维护": {covered: false, confidence: 0}
  "12. 系统运行与维护": {covered: true, confidence: 3} # monitor/sync 覆盖
  "13. 新技术": {covered: false, confidence: 0}

grill_history: []  # {date, topic, score, questions}
```

confidence 含义: 0=未学, 1=看过, 2=理解, 3=能应用, 4=能讲授, 5=考试通过

## 工作流

### W1: archi（学习透镜 — 默认模式）

```
用户: "archi"（在工作对话中触发）
  →
  1. 读取当前会话上下文（最近的工作内容）
  2. 匹配对应的考试章节
  3. 输出: "🔍 你刚才做的 [X] 对应考试第 [N] 章 [章节名]。考试会问: [相关考点]。你在实战中已经理解了 [具体内容]，考试时注意补充 [理论框架/术语]"
  4. 如果该章节 confidence < 3，建议补充学习
```

### W2: archi grill（测验模式）

```
用户: "archi grill" 或 "archi grill <topic>"
  →
  1. 从 config.yaml progress 读取已覆盖章节（covered: true）
  2. 优先出题于最近工作关联的章节
  3. 如指定 topic，只出该章节的题
  4. 3-5 题（选择题 + 简答题混合）
  5. 用户回答后 → 判分 → 讲解答题思路 → 关联实战经历
  6. 更新 grill_history
```

### W3: archi map（知识点映射）

```
用户: "archi map"
  →
  1. 读取 config.yaml progress
  2. 列出所有 13 章: ✅ 已覆盖（confidence 值） / ❌ 未覆盖
  3. 对未覆盖章节，建议"如果你做 [X 工作]，就能覆盖这个考点"
  4. 给出下一步行动建议（最优先补哪个章节）
```

### W4: archi progress（进度报告）

```
用户: "archi progress"
  →
  1. 读取 config.yaml progress
  2. 计算: 总覆盖率 = covered:true / 13 * 100%
  3. 计算: 平均掌握度 = avg(confidence)
  4. 列出: grill_history 最近 5 次测验成绩
  5. 给出备考建议: 距离目标考试还有 X 个月，当前节奏是否合理
```

### W5: archi learn（深度学习）

```
用户: "archi learn <topic>"
  →
  1. 三源并行搜索（Tavily + MiniMax + WebSearch）
  2. 关联本地已有工作产物（如该章节对应的 ccconfig 文档）
  3. 生成结构化学习笔记（飞书文档）
  4. 更新 config.yaml 中该章节的 confidence
```

## 集成点

| 系统 | 关系 |
|------|------|
| f-search | 学习模式的三源搜索委托 f-search |
| f-feishu | 学习笔记输出到飞书文档 |
| f-logme | 学习记录写入 Worklog 表（关联 OKR_KR "软考备考"）|

## 首次安装

```bash
# 创建进度配置文件
cp config.yaml.example config.yaml
# 编辑 config.yaml: 设定目标考试时间、初始 progress 值
```

cconfig 用户: `init-skill.sh sync` 自动 symlink。私有进度数据通过 ccprivate 覆盖 `config.yaml`。

## 参考

- 软考系统分析师考试大纲（2025 版）
- 《系统分析师教程》（清华大学出版社）
- SEI ATAM 方法
- 历年真题（2018-2025）
