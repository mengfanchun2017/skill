# 飞书 Slides 前提检查与 fdiagram 协作

## 飞书 Slides 前提检查

选择飞书 Slides 输出前，检查 lark-cli 在线生成能力：

```bash
# 1+2. lark-cli 是否可用、账号与授权是否正常（由 fcore 统一判断）
~/.claude/skills/fcore/bin/fcore auth || (
  echo "lark-cli 不可用或未授权 → 降级为本地 PPTX"
  exit 1
)

# 3. 飞书 Slides API 是否支持在线创建
lark-cli --version | grep -qE 'slides|3\.' && echo "✅ 支持飞书 Slides" || echo "⚠️ 当前版本可能不支持 slides，将尝试"
```

检查失败则仅输出 PPTX，并说明阻塞原因。

---

## 与 fdiagram 协作

图表委托 `fdiagram` 生成：

```
fpptx 判断"这页需要图表"
  → 输出 Mermaid 描述或数据给 fdiagram
  → fdiagram 生成可编辑 SVG
  → SVG 嵌入 slide（OfficeCLI: --prop src=/path/to/diagram.svg）
  → fdiagram 负责 SVG 视觉样式（配色匹配当前主题）
```

- 架构/流程/时序/ER/类/状态/甘特图 → `fdiagram` Mermaid 模式
- 数据图表（柱状/折线/饼图）→ `fdiagram` SVG 或 OfficeCLI chart
- 白板/示意图 → `fdiagram` whiteboard-cli

---
