# orchestrator ↔ 子 skill 通信契约（面试线）

> 通用契约（返回格式/真相源/进度）→ `fworch/references/orchestrator-contract.md`。
> 本文件补充面试线专属：配置文件写入（yaml-edit）。

## 子 skill 输出格式

每个 step 完成后返回 YAML dict：

```yaml
status: "ok" | "blocked" | "needs_input"
doc_url: "https://feishu.cn/docx/..."     # 主产出飞书 URL
notes:
  - "已搜 JD 关键词 N 个"
  - "等待用户在飞书审校"
```

- `status=ok` → orchestrator 写配置 `current_step += 1` + 记录 `doc_url`
- `status=blocked` → 终止当前 step，保留 current_step，等用户介入
- `status=needs_input` → orchestrator 问用户后重试

## 飞书文档作为 single source of truth

子 skill 只负责**创建/更新飞书文档**。用户改飞书后，下一次进入时 fetch 最新版本校验；通过 → ok，不通过 → 提示缺口。

## 配置文件写入

orchestrator 在 status=ok 后用 `ccprivate/bin/yaml-edit.sh` 更新 `<slug>.yaml`：

```bash
E="$(skillconf_ccprivate_root)/bin/yaml-edit.sh"
CFG="$(skillconf_file finterview/<slug>.yaml)"

$E "$CFG" set current_step 1
$E "$CFG" set feishu.brief_doc_url "https://feishu.cn/docx/..."
```

## 降级

`conf/finterview/` 或 registry interview 条目缺失时：按触发词直入本 orchestrator，父目录用 `interview.yaml` 的 `default_parent_wiki_node`。不阻断。
