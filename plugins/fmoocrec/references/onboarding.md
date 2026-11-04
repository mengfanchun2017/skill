# 首次使用 — Grill Me 与飞书初始化

> SKILL.md 只留"首次要问什么、建立什么"；本文件是逐步命令。
> 命令走 `fcore`，不要手写 lark-cli 参数。

**已知缺陷（待修）**：原 `## 阶段一：数理基础` 一节是 heredoc 被截断后的残留
（表格只剩 `...`）。真实课程数据在 `references/bio-curriculum.md`，建文档时
从那里取，不要从本文的占位表格取。

## 工作流 0: 首次使用 — Grill Me

**触发**: `config.yaml` 无有效个人配置

### Step 0.1: Grill 问答

逐题提问，等用户回答后再问下一题。**给选项让用户选**（减少打字）。

```
Q1: 你叫什么名字？在哪个学校？几年级？（大一/大二/大三/大四/研究生）
Q2: 生物科学里你最感兴趣的方向？
    选项: 分子生物学 / 遗传学 / 细胞生物学 / 生物化学 / 神经科学
         / 免疫学 / 微生物学 / 生态与进化 / 生物信息学 / 不确定先都看看
Q3: 英语水平？能跟上全英文授课吗？
    选项: 完全没问题 / 需要中文字幕辅助 / 最好中文课程
Q4: 每周能投入多少小时学 MOOC？
    选项: 3-5h / 5-10h / 10-15h / 15h+
Q5: 职业方向？
    选项: 科研（读博） / 医学院（临床） / 生物技术公司 / 教育 / 不确定
Q6: 预算偏好？
    选项: 完全免费（旁听为主） / 关键课程愿意付费拿证书 / 证书对我很重要适度付费 / 不限预算
```

**注意**：数理基础（微积分/线代/化学/物理）不在推荐范围。这些由学校课程自然覆盖，MOOC 再加一层是额外负担。

根据答案推导 `subject_areas`（兴趣→课程领域映射）：

| 兴趣方向 | subject_area 筛选 |
|---------|------------------|
| 分子生物学 | molecular_biology, biochemistry, cell_biology |
| 遗传学 | genetics, genomics, epigenetics |
| 细胞生物学 | cell_biology, molecular_biology, biochemistry |
| 生物化学 | biochemistry, chemical_biology, proteomics |
| 神经科学 | neuroscience, cell_biology |
| 免疫学 | immunology, cell_biology, molecular_biology |
| 微生物学 | microbiology, molecular_biology, genetics |
| 生态与进化 | evolution, ecology |
| 生物信息学 | bioinformatics, genomics, computational_biology |

### Step 0.2: 查询 Supabase 课程

```bash
# 用 Python 调 Supabase 管理 API 查询（mcp__supabase__execute_sql 可能不可用时的 fallback）
python3 -c "
import json, requests
sql = '''SELECT name, name_zh, university, university_qs_rank, platform, url, alternate_url, alternate_platform, subject_area, stage, difficulty,
         duration_weeks, hours_per_week, language, has_chinese_subtitle,
         free_option, certificate_option, certificate_price_usd, certificate_platform,
         rating, prerequisites
         FROM courses WHERE is_active = true AND stage IN (''core'',''advanced'',''frontier'')
         ORDER BY stage, id'''
r = requests.post('https://api.supabase.com/v1/projects/<your-supabase-project-id>/database/query',
    headers={'Authorization': 'Bearer <your-supabase-access-token>',
             'Content-Type': 'application/json'},
    json={'query': sql}, timeout=15)
print(json.dumps(r.json(), ensure_ascii=False))
"
```

按学生画像筛选：
- 英语弱 → 优先 `language='zh'` 或 `has_chinese_subtitle=true`
- 时间少 → 优先 `duration_weeks` 短 + `difficulty='beginner'`
- 特定兴趣 → `WHERE subject_area IN (...)` 
- 预算敏感 → `ORDER BY certificate_price_usd ASC NULLS FIRST`

### Step 0.3: 创建飞书个人空间

**必须先调 ffeishu Skill**（飞书规则硬前置条件）。

创建资源顺序：

1. **创建 Base + 进度表**
```bash
export LARKSUITE_CLI_CONFIG_DIR="$HOME/.lark-cli-<account>"
export PATH="$HOME/.local/bin:$PATH"

# 创建 Base
lark-cli base +base-create --name "MOOC学习进度" --as user 2>&1 | sed '/^\[lark-cli\]/d'
# 保存 base_token

# 重命名默认表为 progress
lark-cli base +table-update --base-token $BASE_TOKEN --table-id "数据表" --name "进度" --as user

# 添加字段（逐个）
lark-cli base +field-create --base-token $BASE_TOKEN --table-id $TBL --json '{"field_name":"平台","type":"select","options":[{"name":"Coursera","color":0},{"name":"edX","color":1},{"name":"MIT OCW","color":2},{"name":"中国大学MOOC","color":3},{"name":"其他","color":4}]}'
# ... 其他字段见 Step 0.4
```

2. **创建 Wiki 节点**（在已有 Wiki space 下）
```bash
lark-cli wiki +node-create --space-id $SPACE_ID --parent-node-token $ROOT_NODE \
  --title "MOOC 生物科学" --obj-type docx --as user
# 保存 wiki_node token
```

3. **创建学生画像 Wiki Doc**
```bash
cat << 'EOF' | lark-cli docs +create --api-version v2 \
  --parent-token $WIKI_NODE --as user --doc-format markdown --content - \
  --title "学生画像 - <姓名>"

# 学生画像 - <姓名>

| 字段 | 值 |
|------|-----|
| 姓名 | ... |
| 专业 | 生物科学 |
| 年级 | ... |
| 学校 | ... |
| 兴趣方向 | ... |
| 英语水平 | ... |
| 每周时间 | ... |
| 职业目标 | ... |
| 预算偏好 | ... |
| 创建日期 | YYYY-MM-DD |
EOF
```

4. **创建学习路径 Wiki Doc**
```bash
cat << 'EOF' | lark-cli docs +create --api-version v2 \
  --parent-token $WIKI_NODE --as user --doc-format markdown --content - \
  --title "生物科学 MOOC 学习路径"

# 生物科学 MOOC 学习路径

> 基于 QS 2026 生物科学 Top5 课程体系
> 学生: <姓名> | 生成日期: YYYY-MM-DD

## 阶段一：数理基础

| # | 课程 | 学校 | 平台 | 免费方案 | 证书方案 | 价格 | 时间 |
|---|------|------|------|---------|---------|------|------|
...
EOF
```

### Step 0.4: 进度 Base Table 字段定义

| 字段名 | 类型 | options/配置 |
|--------|------|-------------|
| 课程名称 | text (主字段) | — |
| 平台 | select | Coursera, edX, MIT OCW, 中国大学MOOC, 其他 |
| 大学 | text | — |
| 阶段 | select | 基础, 核心, 进阶, 前沿 |
| 领域 | select | 生物化学, 遗传学, 分子生物学, 细胞生物学, 神经科学, 免疫学, 生物信息学, 进化生物学, 基因组学, 其他 |
| 状态 | select | 📋计划中, 📖学习中, ✅已完成, ❌已放弃 |
| 轨道 | select | 免费旁听, 付费证书 |
| 开始日期 | datetime | — |
| 完成日期 | datetime | — |
| 证书URL | url | — |
| 投入时间 | number | 小时 |
| 评分 | rating (1-5) | — |
| 备注 | text | — |

### Step 0.5: 写配置

```python
# 更新 config.yaml
config = {
    "lark_cli": {"config_dir": "~/.lark-cli-<account>"},
    "tenant_domain": "<your-tenant>.feishu.cn",
    "space_id": "<space_id>",
    "wiki_node": "<wiki_node_token>",
    "docs": {
        "profile": "<profile_doc_token>",
        "path": "<learning_path_doc_token>"
    },
    "base": {
        "token": "<base_token>",
        "tables": {"progress": "<table_id>"}
    }
}
```

### Step 0.6: 输出

展示：
1. 学习路径概要（4 阶段结构 + 推荐第一门课）
2. 所有飞书文档链接
3. "下次输入 `/f-moocrec` 即可查看进度或获取推荐"

---
