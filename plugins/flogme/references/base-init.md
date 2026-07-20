# Base 初始化流程

新建 Bitable 后有一张默认空表 "数据表"。**推荐直接复用默认表**，不要创建新表再删默认表。

## 推荐方案：Rename + 加字段

```bash
# 1. 重命名默认表
lark-cli base +table-update --base-token $T --table-id "数据表" --name "OKR_O" --as user

# 2. 给第一张表加字段
lark-cli base +field-create --base-token $T --table-id tblXXX \
  --json '{"field_name":"分类","type":"select","options":[{"name":"work","color":0},{"name":"learn","color":1}]}'

# 3. 创建其余表（第2张起）
lark-cli base +table-create --base-token $T --as user --name "OKR_KR" --fields '[...]'
```

**为什么不用 "新建+删默认" 方案**：
- 默认表 "数据表" 是最后一张表时无法删除（"A base must keep at least one table"）
- 新建→删默认需要 2 步 2 次 API；rename 只需 1 步，字段直接加到重命名后的表上
- 新 Base 默认没有 workflow / dashboard，无需处理

## 踩坑记录

| 默认项 | 是否存在 | 能否删除 |
|--------|---------|---------|
| 默认空表 "数据表" | ✅ 有 | ✅ 可删（但至少保留1张表） |
| 默认 workflow | ❌ 无 | ❌ lark-cli 无 `+workflow-delete`，API 无 DELETE endpoint |
| 默认 dashboard | ❌ 无 | ✅ `+dashboard-delete --yes` |

## 主字段 auto_number 转手动编号

auto_number 值无法修改（删除记录后编号永久跳过），但可转为 number 类型后手动设值：

```bash
# 1. 类型转换：auto_number → number
lark-cli base +field-update --base-token $T --table-id $T_KR \
  --field-id fldXXX --json '{"name":"内部ID","type":"number"}' --yes

# 2. 手动写入目标值
lark-cli api PUT ".../tables/$T_KR/records/$RID" \
  --data '{"fields":{"内部ID":1}}' --as user

# 3. 删冗余字段，主字段改名
lark-cli api DELETE ".../tables/$T_KR/fields/$REDUNDANT" --as user
lark-cli base +field-update --base-token $T --table-id $T_KR \
  --field-id fldXXX --json '{"name":"编号","type":"number"}' --yes

# 4. 整数格式：formatter="0"（API 直接 PUT）
lark-cli api PUT ".../tables/$T_KR/fields/fldXXX" \
  --data '{"field_name":"编号","type":2,"property":{"formatter":"0"}}' --as user
```

**Why**: auto_number 不可重置、不可手动设值、删除后编号永久跳过。转为 number 后完全自由控制。completed KR 可从 100+ 编号做视觉区分。

## field-update vs raw API PUT

`+field-update` 用 `--json` 传全量 field definition，底层是 PUT 语义。select 字段更新 options 时，**必须用 `+field-update` 而非 raw API**（raw API PUT 常报 field validation failed）。number 字段改 formatter 则必须用 raw API PUT（`+field-update` 不认 `property` key）。

```
❌ raw API PUT → select options update → field validation failed
✅ +field-update --json '{"name":"X","type":"select","options":[...]}' --yes

✅ raw API PUT → number formatter → {"field_name":"X","type":2,"property":{"formatter":"0"}}
❌ +field-update --json '{...,"property":{...}}' → Unrecognized key 'property'
```
