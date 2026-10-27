#!/bin/bash
# plugin_env.sh — skill 配置解析的【唯一实现】。
#
# 此前每个 skill 各写一份路径回退链（实测 15 处重复实现，变量名还有
# $CCPRIVATE_HOME / $CCPRIVATE_DIR / 裸 $HOME/git/ccprivate 三种并存）。
# 本文件是唯一真相源：所有 skill 都 source 它，不再自己拼路径。
#
# 同时提供 Python 版（config_env.py，同一套优先级）供 .py 脚本调用。
#
# ── 优先级（高 → 低）─────────────────────────────────────────────
#   1. 环境变量 SKILLCONF_<KEY>            显式覆盖（调试/CI 用）
#   2. ${CLAUDE_PLUGIN_DATA}/config.json   官方持久目录（用户自填，跨升级保留）
#   3. settings.json → pluginConfigs       官方非敏感通道（/plugin 弹窗填的）
#   4. .credentials.json → pluginSecrets   官方敏感通道（"sensitive":true 的值）
#   5. $CCPRIVATE_HOME/conf/<plugin>.yaml  私有仓真值（自用多机同步的主通道）
#   6. $CCPRIVATE_HOME/skill/<plugin>.yaml 私有仓旧位置（迁移期兼容）
#   7. ~/.claude/skill-config/<plugin>.yaml  旧用户级路径（迁移期兼容）
#   8. <plugin目录>/config.yaml            旧 symlink 通道（迁移期兼容）
#
# 5/6/7/8 是历史包袱，保留只为不破坏已在跑的机器；新配置一律写 2 或 5。
#
# ── 用法 ────────────────────────────────────────────────────────
#   source ".../references/plugin_env.sh"
#   v=$(skillconf_get tenant_domain)              # 取值（缺失 → 空 + 非零码）
#   v=$(skillconf_get tenant_domain "默认值")      # 带默认值
#   skillconf_require tenant_domain || exit 1     # 缺失时打印引导并返回非零
#   skillconf_diag                                # 打印"每个键从哪个源来的"
#   p=$(skillconf_path)                           # 当前会命中的文件路径

# ── 定位 plugin ────────────────────────────────────────────────
# CLAUDE_PLUGIN_ROOT 只在 hook/MCP/LSP 进程与 Markdown 内联替换里存在，
# Bash 工具里没有 —— 故必须从路径反推。
#
# ⚠️ 必须在 **source 时刻**捕获调用方，不能在调用时刻用 ${BASH_SOURCE[1]}：
# plugin_env.sh 住在 ffeishu 下，被别的 skill source 后再调用 skillconf_get 时，
# 函数内部的 BASH_SOURCE[1] 指向的是 plugin_env.sh 自己（或中间函数）→ 会解析成
# ffeishu，导致"给 fworch-case 取配置却读到 ffeishu 的"。实测踩过。
_SKILLCONF_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}")" 2>/dev/null && pwd || true)"
case "$(basename "${_SKILLCONF_SOURCE_DIR:-}")" in
    references|scripts) _SKILLCONF_SOURCE_DIR="$(dirname "$_SKILLCONF_SOURCE_DIR")" ;;
esac

skillconf_plugin_dir() {
    # 1. 显式指定（跨 plugin 取值时用）
    if [[ -n "${SKILLCONF_PLUGIN_DIR:-}" && -d "$SKILLCONF_PLUGIN_DIR" ]]; then
        printf '%s\n' "$SKILLCONF_PLUGIN_DIR"; return 0
    fi
    # 2. 官方变量（hook/MCP/LSP 进程里有）
    if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" && -d "$CLAUDE_PLUGIN_ROOT" ]]; then
        printf '%s\n' "$CLAUDE_PLUGIN_ROOT"; return 0
    fi
    # 3. source 时刻捕获的调用方目录
    if [[ -n "${_SKILLCONF_SOURCE_DIR:-}" && -d "$_SKILLCONF_SOURCE_DIR" ]]; then
        printf '%s\n' "$_SKILLCONF_SOURCE_DIR"; return 0
    fi
    return 1
}

skillconf_plugin_name() {
    # 显式名优先（跨 plugin 取值，如 fpdf 要读 ffeishu 的配置）
    if [[ -n "${SKILLCONF_PLUGIN_NAME:-}" ]]; then
        printf '%s\n' "$SKILLCONF_PLUGIN_NAME"; return 0
    fi
    local d; d="$(skillconf_plugin_dir)" || return 1

    # ⚠️ /plugin install 用户的 CLAUDE_PLUGIN_ROOT 是**带版本号**的 cache 目录：
    #   ~/.claude/plugins/cache/<market>/<plugin>/<version>/
    # 直接 basename 会得到 "0.1.0"（实测踩过）→ 去查 "0.1.0@market" 的配置，
    # 永远查不到。故：① 先反查 installed_plugins.json（权威）② 再按 cache 布局取上一层。
    local reg="$HOME/.claude/plugins/installed_plugins.json"
    if [[ -f "$reg" ]]; then
        local n
        n="$(python3 - "$reg" "$d" <<'PYEOF'
import json, os, sys
reg, root = sys.argv[1], os.path.realpath(sys.argv[2])
try:
    d = json.load(open(reg))
except Exception:
    sys.exit(1)
for key, arr in (d.get("plugins") or {}).items():
    name = key.split("@", 1)[0]
    for rec in arr if isinstance(arr, list) else [arr]:
        p = rec.get("installPath") if isinstance(rec, dict) else None
        if p and os.path.realpath(p) == root:
            print(name); sys.exit(0)
# 命中不到（版本目录变了）时按 cache 布局推断：<market>/<plugin>/<version>
parts = root.rstrip("/").split(os.sep)
if "cache" in parts:
    i = len(parts) - 1 - parts[::-1].index("cache")
    if len(parts) > i + 2:
        print(parts[i + 2]); sys.exit(0)
sys.exit(1)
PYEOF
)"
        [[ -n "$n" ]] && { printf '%s\n' "$n"; return 0; }
    fi
    basename "$d"
}

# ── 各来源的候选文件 ────────────────────────────────────────────
skillconf_ccprivate_root() {
    printf '%s\n' "${CCPRIVATE_HOME:-${CCPRIVATE_DIR:-$HOME/git/ccprivate}}"
}

# 官方 pluginConfigs / pluginSecrets 的 key 形如 "<plugin>@<market>"。
# 不硬编码 market 名（用户的 marketplace 名可自定义）——改为扫描匹配 @ 前缀。
skillconf_official_key() {
    local name="$1" file="$2" section="$3"
    [[ -f "$file" ]] || return 1
    python3 - "$file" "$section" "$name" <<'PYEOF'
import json, sys
path, section, name = sys.argv[1:4]
try:
    d = json.load(open(path))
except Exception:
    sys.exit(1)
sec = d.get(section) or {}
# 精确命中 "<name>@<anything>"；无 @ 时也接受裸 name（--plugin-dir 装载场景）
for k in sec:
    if k == name or k.split("@", 1)[0] == name:
        print(k); sys.exit(0)
sys.exit(1)
PYEOF
}

# ── 单一取值实现（python 做解析，避免 yq 依赖）─────────────────
# 输出：TSV  "值 \t 来源标签"。找不到键 → 退出码 1。
skillconf_lookup() {
    local key="$1"
    local name dir ccpriv cfgdir cfgdir_env
    name="$(skillconf_plugin_name)" || return 1
    dir="$(skillconf_plugin_dir)" || dir=""
    ccpriv="$(skillconf_ccprivate_root)"
    cfgdir_env="${CLAUDE_PLUGIN_DATA:-}"
    cfgdir="$HOME/.claude/plugins/data/$name"

    # 1. 显式环境变量覆盖
    local envkey="SKILLCONF_$(printf '%s' "$key" | tr '[:lower:]-' '[:upper:]_')"
    if [[ -n "${!envkey:-}" ]]; then
        printf '%s\t%s\n' "${!envkey}" "env:$envkey"; return 0
    fi

    python3 - "$key" "$name" "$dir" "$ccpriv" "$cfgdir_env" "$cfgdir" "$HOME/.claude" <<'PYEOF'
import json, os, sys

key, name, pdir, ccpriv, cfg_env, cfg_default, claude_dir = sys.argv[1:8]

def yaml_load(p):
    try:
        import yaml
        with open(p) as f:
            return yaml.safe_load(f)
    except Exception:
        return None

def json_load(p):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return None

def dig(d, path):
    """按点号路径取值，如 'writing.case.base_token'"""
    if d is None:
        return None
    node = d
    for k in path.split("."):
        if isinstance(node, dict) and k in node:
            node = node[k]
        else:
            return None
    return node

candidates = []

# 2. CLAUDE_PLUGIN_DATA（官方持久目录，跨升级保留）
for base in [cfg_env, cfg_default]:
    if base:
        candidates.append((os.path.join(base, "config.json"), "plugin-data"))
        candidates.append((os.path.join(base, "config.yaml"), "plugin-data"))

# 3./4. 官方两个 JSON（key 形如 "<plugin>@<market>"）
def official(section, fname):
    d = json_load(os.path.join(claude_dir, fname)) or {}
    sec = d.get(section) or {}
    for k in sec:
        if k == name or k.split("@", 1)[0] == name:
            return sec[k]
    return None

pc = official("pluginConfigs", "settings.json")
if isinstance(pc, dict):
    # 实测结构：{"options": {...}}
    opts = pc.get("options", pc)
    candidates.append((opts, "settings.pluginConfigs"))

ps = official("pluginSecrets", ".credentials.json")
if isinstance(ps, dict):
    candidates.append((ps, "credentials.pluginSecrets"))

# 5./6. 私有仓（新位置 → 旧位置）
for sub, tag in [("conf", "ccprivate/conf"), ("skill", "ccprivate/skill")]:
    for ext in ("yaml", "yml", "json"):
        p = os.path.join(ccpriv, sub, f"{name}.{ext}")
        candidates.append((p, tag))

# 6.5 共享真值：多 plugin 同读一份，避免同一值（如 tenant_domain）在 N 个文件里重复。
# 排在 per-plugin 之后 → 优先级更低，per-plugin 可覆盖。
for ext in ("yaml", "yml", "json"):
    candidates.append((os.path.join(ccpriv, "conf", f"_shared.{ext}"), "ccprivate/conf/_shared"))

# 7./8. 旧路径
candidates.append((os.path.join(claude_dir, "skill-config", f"{name}.yaml"), "skill-config"))
if pdir:
    candidates.append((os.path.join(pdir, "config.yaml"), "plugin/config.yaml"))

for c in candidates:
    src, tag = c[0], c[1]
    if isinstance(src, dict):
        v = dig(src, key)
    else:
        if not os.path.isfile(src):
            continue
        v = dig(yaml_load(src) if src.endswith((".yaml", ".yml")) else json_load(src), key)
    if v is not None and v != "":
        print(f"{v}\t{tag}")
        sys.exit(0)

sys.exit(1)
PYEOF
}

# ── 公开 API ───────────────────────────────────────────────────
# skillconf_get <key> [default] — 输出值；缺失且有 default → 输出 default 并返回 0
skillconf_get() {
    local key="$1" default="${2-}" out
    if out="$(skillconf_lookup "$key")"; then
        printf '%s\n' "${out%%$'\t'*}"
        return 0
    fi
    if [[ -n "$default" ]]; then
        printf '%s\n' "$default"; return 0
    fi
    return 1
}

# skillconf_require <key> — 缺失时打印"缺哪个键、去哪填"并返回非零
skillconf_require() {
    local key="$1" name
    skillconf_get "$key" >/dev/null 2>&1 && return 0
    name="$(skillconf_plugin_name 2>/dev/null || echo '<plugin>')"
    {
        echo "[skillconf] 缺少配置项: $key  (plugin: $name)"
        echo "  三选一："
        echo "    a) claude plugin configure $name@<market>     # 弹窗填（推荐）"
        echo "    b) 写入 \$CLAUDE_PLUGIN_DATA/config.json : {\"$key\": \"...\"}"
        echo "    c) 写入 \$(skillconf_ccprivate_root)/conf/$name.yaml :"
        echo "         $key: <值>"
    } >&2
    return 1
}

# skillconf_path — 打印当前会命中的文件路径（诊断用；官方通道返回 <settings.json#pluginConfigs>）
skillconf_path() {
    local key="${1:-}" out
    [[ -z "$key" ]] && { echo "(需要键名)"; return 1; }
    out="$(skillconf_lookup "$key")" || { echo "(未命中任何源)"; return 1; }
    local tag="${out#*$'\t'}"
    case "$tag" in
        settings.pluginConfigs|credentials.pluginSecrets)
            echo "$HOME/.claude/<$tag>" ;;
        ccprivate/*) echo "$(skillconf_ccprivate_root)/${tag#ccprivate/}/$(skillconf_plugin_name).yaml" ;;
        plugin/config.yaml|skill-config|plugin-data) echo "<$tag>" ;;
        *) echo "<$tag>" ;;
    esac
}

# skillconf_diag [key...] — 逐键打印"值来自哪个源"，值本身脱敏
# key 省略时列出本 plugin 在各源里出现过的全部键名
skillconf_diag() {
    local name dir ccpriv
    name="$(skillconf_plugin_name)" || return 1
    dir="$(skillconf_plugin_dir)" || dir=""
    ccpriv="$(skillconf_ccprivate_root)"
    echo "plugin: $name"
    echo "  dir:     $dir"
    echo "  ccpriv:  $ccpriv"
    python3 - "$name" "$dir" "$ccpriv" "$HOME/.claude" "$@" <<'PYEOF'
import json, os, sys
name, pdir, ccpriv, claude_dir = sys.argv[1:5]
keys = sys.argv[5:]

def yaml_load(p):
    try:
        import yaml
        with open(p) as f: return yaml.safe_load(f)
    except Exception: return None

def json_load(p):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return None

# 收集各源的键集合
sources = []

def official(section, fname):
    d = json_load(os.path.join(claude_dir, fname)) or {}
    sec = d.get(section) or {}
    for k in sec:
        if k == name or k.split("@", 1)[0] == name:
            return sec[k]
    return None

for base, tag in [(os.environ.get("CLAUDE_PLUGIN_DATA"), "plugin-data"),
                  (os.path.join(os.path.expanduser("~"), ".claude/plugins/data", name), "plugin-data")]:
    if base:
        p = os.path.join(base, "config.json")
        if os.path.isfile(p): sources.append((json_load(p), tag))
pc = official("pluginConfigs", "settings.json")
if isinstance(pc, dict):
    sources.append((pc.get("options", pc), "settings.pluginConfigs"))
ps = official("pluginSecrets", ".credentials.json")
if isinstance(ps, dict): sources.append((ps, "credentials.pluginSecrets"))
for sub in ("conf", "skill"):
    for ext in ("yaml", "yml", "json"):
        p = os.path.join(ccpriv, sub, f"{name}.{ext}")
        if os.path.isfile(p):
            sources.append((yaml_load(p) if ext != "json" else json_load(p), f"ccprivate/{sub}/{name}.{ext}"))
p = os.path.join(claude_dir, "skill-config", f"{name}.yaml")
if os.path.isfile(p): sources.append((yaml_load(p), "skill-config"))
if pdir:
    p = os.path.join(pdir, "config.yaml")
    if os.path.isfile(p): sources.append((yaml_load(p), "plugin/config.yaml"))

def flatten(d, pre=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(flatten(v, f"{pre}{k}."))
    else:
        out[pre.rstrip(".")] = d
    return out

# 打印每个源的键
print("  已有源：")
for d, tag in sources:
    ks = sorted(flatten(d)) if isinstance(d, dict) else []
    print(f"    {tag}: {len(ks)} 键" + (f" -> {', '.join(ks[:8])}{'...' if len(ks)>8 else ''}" if ks else ""))
if not sources:
    print("    （无）")

if keys:
    print("  指定键命中：")
    for k in keys:
        hit = None
        for d, tag in sources:
            v = flatten(d).get(k)
            if v not in (None, ""):
                hit = (tag, v); break
        if hit:
            v = str(hit[1])
            shown = v if len(v) <= 12 else v[:6] + "…" + v[-2:]
            print(f"    {k} = {shown}   ← {hit[0]}")
        else:
            print(f"    {k} = (缺失)")
PYEOF
}

# ── 共享 conf 文件访问（多 skill 共用的真值）─────────────────────
# 与 skillconf_get 的区别：
#   skillconf_get  <key>              → 本 plugin 的私有配置（按 plugin 名定位文件）
#   skillconf_file <relpath> <key...> → 共享真值（如 writing/case.yaml），多个 skill 同读
# 两者共用 skillconf_ccprivate_root()，故"ccprivate 在哪"只有一处实现。
skillconf_file() {
    local rel="$1"
    local base
    base="$(skillconf_ccprivate_root)"
    [[ -f "$base/conf/$rel" ]] && { printf '%s\n' "$base/conf/$rel"; return 0; }
    # 迁移期兼容：旧代码写过 ../skill/... 这类相对穿透
    [[ -f "$base/$rel" ]] && { printf '%s\n' "$base/$rel"; return 0; }
    return 1
}

# 按点号路径逐级取值；支持列表索引（如 doc_index.3.title）
skillconf_file_get() {
    local rel="$1"; shift
    local f
    f="$(skillconf_file "$rel")" || return 1
    python3 - "$f" "$@" <<'PYEOF'
import sys
try:
    import yaml
except ImportError:
    sys.exit(2)
path, keys = sys.argv[1], sys.argv[2:]
try:
    suf = path.rsplit(".", 1)[-1].lower()
    with open(path) as fh:
        node = yaml.safe_load(fh) if suf in ("yaml", "yml") else __import__("json").load(fh)
except Exception:
    sys.exit(1)
if node is None:
    sys.exit(1)
for k in keys:
    if isinstance(node, dict) and k in node:
        node = node[k]
    elif isinstance(node, list) and k.isdigit() and int(k) < len(node):
        node = node[int(k)]
    else:
        sys.exit(1)
if node is None:
    sys.exit(1)
print(node if not isinstance(node, bool) else str(node).lower())
PYEOF
}

export -f skillconf_get skillconf_require skillconf_path skillconf_diag \
          skillconf_lookup skillconf_plugin_name skillconf_plugin_dir \
          skillconf_ccprivate_root skillconf_official_key \
          skillconf_file skillconf_file_get 2>/dev/null || true