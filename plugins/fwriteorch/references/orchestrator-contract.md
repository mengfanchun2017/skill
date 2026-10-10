# Orchestrator 通信契约（通用，L3/L1 规范）

> 全部编排器（`orchcourse` / `orchreport` / `orchcase`）及其子 skill 遵循本契约。
> 各编排器可加体裁专属补充，但**返回格式与真相源约定统一**。

## 子 skill 输出格式（统一返回块）

每个子 skill 完成后返回 YAML dict：

```yaml
status: "ok" | "blocked" | "needs_input"
doc_url: "https://feishu.cn/docs/..."     # 主产出飞书 URL
aux_docs:
  - url: "https://feishu.cn/docs/..."     # 副产出（如课程总览、对比表）
    purpose: "overview"                   # 用途标识
notes:                                    # 给 orchestrator 的提示
  - "已调用 fsearch 3 次"
  - "等待用户在飞书审校"
```

字段约定：
- `status=ok` → orchestrator 记录 `doc_url` + 推进进度
- `status=blocked` → 终止当前 step，保留原进度，等用户介入
- `status=needs_input` → orchestrator 问用户后重试子 skill

## 飞书文档 = single source of truth

子 skill 只负责**创建/更新飞书文档**。用户改飞书后，下次进入时子 skill：
- fetch 飞书内容（最新版本）→ 校验完整性
- 通过 → `status=ok`
- 不通过 → 提示缺口让用户补

本地配置文件（如 `conf/fcourse/<slug>.yaml`）仅作**缓存镜像**，飞书在线为真值。

## 进度与配置写入

- **课程线**（有本地镜像）：orchestrator 在 `status=ok` 后用 `ccprivate/bin/yaml-edit.sh` 更新 `<slug>.yaml`（`set`/`append`/`get`，点号路径）。
- **报告/案例线**（无本地进度文件）：进度以飞书文档 + 注册表真值文件（`conf/writing/<genre>.yaml`）为准，不额外维护本地进度。

## 编排器骨架（统一）

```
读注册表/配置 → 判断进度 → 委派子 skill（按委派表）→ 收 status → 推进/更新 → 循环
每步原则：产出 → 展示飞书链接 → 用户改 → 确认 → 下一步
```

## 关联

- `fstd-core` — 格式硬约束
- `ffeishu` — 飞书机械层
- `ccconfig/docs/adr/0043-writing-system-architecture.md` — 架构决策
