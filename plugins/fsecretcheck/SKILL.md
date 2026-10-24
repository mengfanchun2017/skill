---
name: fsecretcheck
user-invocable: true
description: 密钥泄露检查 — 扫描仓库工作树与 git 历史里的真实凭据（API key/token/密码/内网 IP），判定该文件属于公开仓还是私密仓，给出脱敏建议。用法：用户说"检查密钥"/"密钥泄露"/"扫描密钥"/"有没有泄露"/"提交前检查"、"这个文件能公开吗"，或准备把配置/文档推到公开仓库前触发。
allowed-tools: Bash, Read, Grep, Glob
---

# fsecretcheck — 密钥泄露检查

## 概述

**公开仓库的守门员**。两个动作：① 扫出真实凭据（工作树 + git 历史）；② 判定内容归属（公开 / 私密）。

**核心前提**：私密仓库（如 ccprivate）**本来就是存 key 的地方**，对它扫描只报告不拦截；
公开仓库（ccconfig / skill / 任何要 push 到公开 remote 的仓）才需要拦截。

## 何时用

- 准备把配置/脚本/文档推公开仓库之前
- 怀疑某文件混进了真实 key
- 审计报告/交接材料里引用了真实地址、内网 IP
- 新 skill / 新脚本创建后（skill 仓库是公开的）

## 判定：先确定仓库可见性

```bash
# 私密（owner 私有仓 / 无人 fork / remote 指向私有 repo）
# → 只报告，不阻断
# 公开（remote 可被任何人 clone）
# → 报告 + 阻断 push
```

判定方法（不猜，直接问 remote）：

```bash
repo="$1"
url=$(git -C "$repo" remote get-url origin 2>/dev/null)
visibility=$(gh repo view "$(echo "$url" | sed 's#.*github.com[:/]##; s#\.git$##')" --json visibility -q .visibility 2>/dev/null)
echo "$repo: ${visibility:-unknown}"
```

`PRIVATE` → 报告模式；`PUBLIC` / `INTERNAL` / unknown-but-public-remote → 阻断模式。

## 扫描内容

### 1. 工作树（已跟踪 + 未跟踪）

```bash
SECRET_RE='sk-[a-zA-Z0-9]{20,}|sk-ant-[a-zA-Z0-9_-]{20,}|gho_[a-zA-Z0-9]{36}|ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{20,}|eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}|tvly-[A-Za-z0-9-]{16,}|cfut_[A-Za-z0-9]{16,}|sbp_[A-Fa-f0-9]{16,}|"x-api-key"[[:space:]]*:[[:space:]]*"[a-f0-9-]{36}"'

# 已跟踪文件
git -C "$repo" ls-files -z | xargs -0 grep -InE "$SECRET_RE" 2>/dev/null
# 未跟踪文件（排除 .git / node_modules / 二进制）
grep -rInE "$SECRET_RE" "$repo" --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv 2>/dev/null
```

正则**唯一真相源**（公开侧）：`ccconfig/lib/secret-patterns.sh` 的 `$SECRET_RE`。
新服务 key 前缀只改那一处，本 skill 与 pre-commit hook 一起受益。

### 2. 内网 IP / 真实域名（规则见 `ccprivate/rules/ccconfig-open-source.md`）

```bash
# 内网段 + tailscale + 真实私网 IP
grep -rInE '\b(10|192\.168|172\.(1[6-9]|2[0-9]|3[01]))\.[0-9]+\.[0-9]+|100\.(6[4-9]|[7-9][0-9]|1[0-2][0-9])\.[0-9]+\.[0-9]+' "$repo" \
  --exclude-dir=.git --exclude-dir=node_modules 2>/dev/null | head -20
# 真实邮箱
grep -rInE '[A-Za-z0-9._%+-]+@(gmail|qq|163|outlook|hotmail|foxmail)\.[A-Za-z]{2,}' "$repo" \
  --exclude-dir=.git 2>/dev/null | head -20
```

### 3. git 历史（关键：删掉的文件仍在历史里，GitHub 按 SHA 匿名可读）

```bash
# 历史里出现过的密钥前缀（-S 按内容变更检索，比 log -p 快）
git -C "$repo" log --all --oneline -S 'sk-ant-' -- . 2>/dev/null | head
git -C "$repo" log --all --oneline -S 'github_pat_' -- . 2>/dev/null | head
# 全历史逐条扫（慢，慎用大仓）
git -C "$repo" rev-list --all | while read c; do
  git -C "$repo" grep -lE "$SECRET_RE" "$c" 2>/dev/null
done | head
```

**命中历史的处理**：`git rebase -i` / `git filter-repo` 重写 → `force-with-lease` → **吊销该 key**
（GitHub 仍按旧 SHA 提供匿名对象，重写不等于删除，必须吊销）。

## 输出格式

按严重度：

```
🔴 P0 已泄露真实凭据
  <文件>:<行号>  <前缀>…（打码，只显示前 8 位）
  处置：吊销该 key → 脱敏 → 重写历史

🟡 P1 疑似 / 规则违反
  <文件>:<行号>  <命中的内容类别>

🟢 干净
  扫描 N 个文件，0 命中
```

**打码规则**：只显示前缀 + 前 8 字符（`sk-ant-…` 或 `tvly-ab12…`），绝不回显完整凭据。

## 与 ccconfig 的关系

- 公开仓的**提交时**防线是 pre-commit hook（`ccconfig/hooks/pre-commit`，注册在 ccconfig 与 skill）
- 本 skill 是**提交前 / 审计时**的主动检查，覆盖 hook 覆盖不到的场景（历史扫描、内网 IP、归属判定）
- hook 与 skill 共用同一套正则，改前缀只改 `ccconfig/lib/secret-patterns.sh`

## 边界

- **不检查私密仓的"该不该有 key"** —— 私密仓就是存 key 的，报告即可
- **不自动吊销 key** —— 吊销需要你到服务商控制台操作，本 skill 只给出该吊销哪个
- **不重写历史** —— 重写是有破坏性的（改写已发布历史），必须你确认后手动执行