# fmoocrec 日常流程 — 推荐/记录/画像/查看/证书

> SKILL.md 只留决策树；本文件是各流程的完整逻辑与输出格式。

## 工作流 1: 课程推荐

**触发**: 用户已有配置，想要课程推荐

### 1.1 读取当前状态

```bash
# 读 Supabase 获取全部活跃课程
# 读飞书 Base 获取已有进度 → 排除已完成的课
# 读飞书 Wiki 获取学生画像 → 获取兴趣/英语/时间
```

### 1.2 推荐逻辑

```
已完成的课 → 标记 ✅，不重复推荐
正在学的课 → 标记 📖，询问是否继续还是跳过
尚未开始的课 → 按画像排序推荐
```

推荐优先级：
1. **先修课已完成** → 排在前面
2. **匹配兴趣方向** → 加权
3. **难度匹配**（beginner 适合新生） → 加权
4. **时间合适** → 加权
5. **语言匹配** → 加权

输出格式：
```
📚 下一阶段推荐：

**优先推荐**（先修条件已满足）：
1. ⭐ <课程名> — <学校> (QS Bio #N) · <平台>
   难度: beginner | 时间: 6周×5h | 语言: 英文(中字)
   免费: <免费方案>
   证书: <证书方案> — $XX (Credly 徽章)
   链接: <URL>
   备用: <alternate_url>（同内容其他平台）
   为什么推荐: <理由>

**可选**（匹配你的兴趣但需先修）：
...

每门课可以深入问："/f-moocrec <课程名> 详情"
```

---

## 工作流 2: 记录学习进度

**触发**: 用户说完成了某门课 / 拿到了证书

### 2.1 确认信息

```
确认: MITx 7.00x Introduction to Biology
- 完成日期？
- 是免费旁听还是付费证书？
- 有证书链接吗？
- 投入了多少小时？
- 1-5 分打几分？
```

### 2.2 写飞书 Base

```bash
lark-cli base +record-batch-create --base-token $B --table-id $T \
  --json '{"fields":["课程名称","平台","大学","阶段","领域","状态","轨道","完成日期","证书URL","投入时间","评分"],"rows":[["Introduction to Biology - The Secret of Life","edX","MIT","core","general_biology","✅已完成","付费证书","2026-08-15","https://...",96,5]]}'
```

### 2.3 更新学习路径 doc

用 `lark-cli docs +update --command str_replace` 在路径 doc 中标记完成状态：
```bash
# 找到对应课程行，替换状态标记
lark-cli docs +update --api-version v2 --doc $PATH_DOC \
  --command str_replace --pattern "⬜ <课程名>" --content "✅ <课程名>" --as user
```

### 2.4 推荐下一门

自动触发工作流 1（课程推荐）。

---

## 工作流 3: 更新学生画像

**触发**: 用户想改画像信息

读现有画像 doc → 只更新变化的字段 → `lark-cli docs +update --command str_replace`
```bash
lark-cli docs +fetch --api-version v2 --doc $PROFILE --detail simple
# 定位要更新的行 → str_replace
lark-cli docs +update --api-version v2 --doc $PROFILE \
  --command str_replace --pattern "| 兴趣方向 | 旧值 |" --content "| 兴趣方向 | 新值 |" --as user
```

---

## 工作流 4: 查看学习进度

**触发**: 用户想看整体进度

### 4.1 查询 Base

```bash
lark-cli base +record-list --base-token $B --table-id $T --format json --limit 200
```

### 4.2 统计汇总

```
📊 学习进度总览

总课程: 38 门（Supabase 课程库）
已完成: X 门 | 进行中: Y 门 | 计划中: Z 门

阶段完成度:
  基础 ████████░░ 6/8
  核心 ████░░░░░░ 3/14
  进阶 ██░░░░░░░░ 1/10
  前沿 ░░░░░░░░░░ 0/6

证书获取: N 门付费证书，总花费 $XXX
总投入: XXX 小时
```

---

## 工作流 5: 证书背书建议

**触发**: 用户询问证书相关

### 5.1 证书分级

| 级别 | 建议 | 哪些课 |
|------|------|--------|
| ⭐⭐⭐ 强烈建议付费 | 核心主干课，证书对求职/升学有明显背书 | MITx 7.00x, HarvardX Biochemistry, MITx Genetics |
| ⭐⭐ 值得考虑 | 进阶课，领域内知名度高 | Duke Neuroscience, JH Genomics |
| ⭐ 免费足够 | 数理基础课、补充课 | MIT OCW 数学, 中国大学MOOC |

### 5.2 证书验证机制

- **edX**: 每张证书有唯一 URL（`https://courses.edx.org/certificates/...`），任何人可点击验证
- **Coursera + Credly**: 徽章含区块链哈希，可在 Credly 平台永久验证，可一键挂 LinkedIn
- **中国大学MOOC**: 证书在 icourse163.org 可查询

### 5.3 LinkedIn 展示

指导用户：
1. edX 证书 → Dashboard → "Share on LinkedIn"
2. Credly 徽章 → Accept badge → "Add to Profile"
3. 手动添加 → LinkedIn "Licenses & Certifications" → 填入证书 URL

---
