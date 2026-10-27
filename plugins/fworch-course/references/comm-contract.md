# orchestrator ↔ 子 skill 通信契约（课程线）

> 通用契约（返回格式/真相源/进度）→ `fworch/references/orchestrator-contract.md`。
> 本文件补充课程线专属：配置文件写入（yaml-edit）。

## 子 skill 输出格式

每个 fworch-course-* 子 skill 完成后返回 YAML dict（stdout 或返回块）：

```yaml
status: "ok" | "blocked" | "needs_input"
doc_url: "https://feishu.cn/docs/..."     # 主产出飞书 URL
aux_docs:
  - url: "https://feishu.cn/docs/..."     # 副产出（如课程总览）
    purpose: "overview"                   # 用途标识
notes:                                    # 给 orchestrator 的提示
  - "已调用 fsearch 3 次"
  - "等待用户在飞书审校"
```

字段约定：
- `status=ok` → orchestrator 写配置 `current_step += 1` + 记录 `doc_url`
- `status=blocked` → 终止当前 step，保留原 current_step，等用户介入
- `status=needs_input` → orchestrator 问用户后重试子 skill

## 飞书文档作为 single source of truth

子 skill 只负责**创建/更新飞书文档**。用户改飞书后，下一次进入时：
- 子 skill fetch 飞书内容（最新版本）
- 校验完整性
- 通过 → 返回 status=ok
- 不通过 → 提示缺口让用户补

## 配置文件写入

orchestrator 在 status=ok 后用 `ccprivate/bin/yaml-edit.sh` 更新 `<slug>.yaml`。
路径用点号分隔，支持三种操作：

```bash
E="$(skillconf_ccprivate_root)/bin/yaml-edit.sh"
CFG="$(skillconf_file fcourse/<slug>.yaml)"

$E "$CFG" set current_step 1                                   # 设标量（数字/布尔自动推断）
$E "$CFG" set feishu.overview_doc_url "https://feishu.cn/..."  # 中间段不存在自动建 dict
$E "$CFG" append feishu.lesson_docs chapter=1 title=导入 url="https://feishu.cn/..."  # list 追加 dict
$E "$CFG" get current_step                                     # 读值（判断进度用）
```

空串用 `""` 保留原语义；`set` 空串可清空字段。注意：pyyaml 读写会丢失注释，课程配置视为数据文件。
