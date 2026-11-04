#!/bin/bash
# fcore/lib/path.sh — 路径与配置解析（唯一实现）
#
# 取代此前 15 处各自维护的回退链（变量名有 $CCPRIVATE_HOME / $CCPRIVATE_DIR /
# 裸 $HOME/git/ccprivate 三种并存），以及 27 份 _skillconf_boot.sh/py 副本。
#
# 优先级（高 → 低）：
#   1. 环境变量 F_<KEY>                       显式覆盖（调试/CI）
#   2. ${CLAUDE_PLUGIN_DATA}/config.json      官方持久目录（plugin 安装，跨升级保留）
#   3. ~/.claude/plugins/data/<plugin>/config.json   同上（Bash 工具里没有该 env 时的兜底）
#   4. settings_pluginConfig  → settings.json 官方 pluginConfigs
#   5. .credentials.json → pluginSecrets      官方敏感通道
#   6. <ccprivate>/conf/<plugin>.yaml         私有仓真值（自用主通道）
#   7. <ccprivate>/conf/_shared.yaml          跨 plugin 共享真值
#   8. ~/.claude/skill-config/<plugin>.yaml   **用户自填规范落点**（不在 cache 下，升级不覆盖）
#   9. <plugin目录>/config.yaml               旧通道（迁移期兼容）

_F_HOME_BASE="${F_HOME_BASE:-$HOME}"
_F_CLAUDE_DIR="$_F_HOME_BASE/.claude"

# 用户自填配置的规范目录：不在 plugins/cache/<market>/<plugin>/<version>/ 之内，
# 故 /plugin update 整目录替换时不会被碰到。
f_user_config_dir() {
    printf '%s\n' "$_F_CLAUDE_DIR/skill-config"
}

# 用户数据目录（课程进度/案例索引这类**可变状态**，不是配置）
f_userdata_dir() {
    local plugin="${1:?plugin name required}"
    printf '%s\n' "$(f_user_config_dir)/data/$plugin"
}

# ccprivate 根（独立用户没有，返回非零）
f_ccprivate_root() {
    local r="${CCPRIVATE_HOME:-${CCPRIVATE_DIR:-$HOME/git/ccprivate}}"
    [[ -d "$r" ]] || return 1
    printf '%s\n' "$r"
}

# 定位 plugin 目录。CLAUDE_PLUGIN_ROOT 只在 hook/MCP/LSP 进程里有，Bash 工具里没有。
# 故从 source 时刻的调用方路径反推；跨 plugin 取值用 F_PLUGIN_DIR / F_PLUGIN_NAME。
_F_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}")" 2>/dev/null && pwd || true)"
case "$(basename "${_F_SOURCE_DIR:-}")" in
    references|scripts|lib|bin) _F_SOURCE_DIR="$(dirname "$_F_SOURCE_DIR")" ;;
esac

f_plugin_dir() {
    [[ -n "${F_PLUGIN_DIR:-}" && -d "$F_PLUGIN_DIR" ]] && { printf '%s\n' "$F_PLUGIN_DIR"; return 0; }
    [[ -n "${CLAUDE_PLUGIN_ROOT:-}" && -d "$CLAUDE_PLUGIN_ROOT" ]] && { printf '%s\n' "$CLAUDE_PLUGIN_ROOT"; return 0; }
    [[ -n "${_F_SOURCE_DIR:-}" && -d "$_F_SOURCE_DIR" ]] && { printf '%s\n' "$_F_SOURCE_DIR"; return 0; }
    return 1
}

f_plugin_name() {
    [[ -n "${F_PLUGIN_NAME:-}" ]] && { printf '%s\n' "$F_PLUGIN_NAME"; return 0; }
    local d; d="$(f_plugin_dir)" || return 1
    # /plugin install 的目录是 cache/<market>/<plugin>/<version>/，basename 会得到版本号。
    # 先反查 installed_plugins.json（权威），再按 cache 布局取上一层。
    local reg="$_F_CLAUDE_DIR/plugins/installed_plugins.json"
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

# 按点号路径取值的候选文件列表（JSON 输出，按优先级）。
# 单一实现：bash 与 python 脚本共用同一顺序，避免两套链漂移。
f_config_candidates() {
    local name="$1"
    python3 - "$name" "$_F_CLAUDE_DIR" "${CLAUDE_PLUGIN_DATA:-}" \
        "$(f_ccprivate_root 2>/dev/null || true)" "$(f_user_config_dir)" <<'PYEOF'
import json, os, sys
name, claude_dir, data_env, ccpriv, user_dir = sys.argv[1:6]
c = []
# 2/3. 官方持久目录
for base in filter(None, [data_env, os.path.join(claude_dir, "plugins", "data", name)]):
    c += [{"p": os.path.join(base, "config.json"), "src": "plugin-data"},
          {"p": os.path.join(base, "config.yaml"), "src": "plugin-data"}]
# 4/5. 官方两个 JSON（key 形如 "<plugin>@<market>"）
c += [{"p": os.path.join(claude_dir, "settings.json"), "src": "settings.pluginConfigs"},
      {"p": os.path.join(claude_dir, ".credentials.json"), "src": "credentials.pluginSecrets"}]
# 6/7. 私有仓
if ccpriv:
    for sub, tag in [("conf", "ccprivate/conf"), ("skill", "ccprivate/skill")]:
        for ext in ("yaml", "yml", "json"):
            c.append({"p": os.path.join(ccpriv, sub, f"{name}.{ext}"), "src": tag})
    for ext in ("yaml", "yml", "json"):
        c.append({"p": os.path.join(ccpriv, "conf", f"_shared.{ext}"), "src": "ccprivate/conf/_shared"})
# 8. 用户自填（升级不覆盖）
for ext in ("yaml", "yml", "json"):
    c.append({"p": os.path.join(user_dir, f"{name}.{ext}"), "src": "skill-config"})
print(json.dumps(c))
PYEOF
}

# f_conf_get <key> [default] — 按键名取值。点号路径支持嵌套（a.b.c）。
f_conf_get() {
    local key="$1" default="${2-}" plugin out
    plugin="$(f_plugin_name 2>/dev/null || echo "")"
    # 1. 环境变量覆盖
    local envkey="F_$(printf '%s' "$key" | tr '[:lower:].-' '[:upper:]__')"
    if [[ -n "${!envkey:-}" ]]; then
        printf '%s\n' "${!envkey}"; return 0
    fi
    [[ -n "$plugin" ]] || { [[ -n "$default" ]] && { printf '%s\n' "$default"; return 0; }; return 1; }
    local cands
    cands="$(f_config_candidates "$plugin")"
    out="$(printf '%s' "$cands" | python3 -c '
import json, os, sys
key, plugin = sys.argv[1], sys.argv[2]
KEY = key
cands = json.load(sys.stdin)
def _emit(v):
    """只输出单值。命中 dict/list 说明 key 路径不完整，直接把 Python repr 当值用是个坑
    （实测 fcore conf get wiki_nodes.default 吐出 "{'token': 'xxx'}"），故明确报错。
    stderr 被外层 2>/dev/null 吞掉，必须走 stdout 并用 MAGIC 前缀让 bash 侧识别。"""
    if isinstance(v, (dict, list)):
        if isinstance(v, dict):
            msg = "%s 是嵌套结构，不是单值。子键: %s\\n用法: fcore conf get <key>.%s" % (
                KEY, ", ".join(sorted(v)), sorted(v)[0])
        else:
            msg = "%s 是列表，不是单值。用下标: fcore conf get <key>.0" % KEY
        print("__FCORE_ERR__" + msg); sys.exit(2)
    print(v if not isinstance(v, bool) else str(v).lower())

def dig(node, path):
    for k in path.split("."):
        if isinstance(node, dict) and k in node: node = node[k]
        elif isinstance(node, list) and k.isdigit() and int(k) < len(node): node = node[int(k)]
        else: return None
    return node
def load(p):
    try:
        if p.endswith((".yaml", ".yml")):
            import yaml; return yaml.safe_load(open(p))
        return json.load(open(p))
    except Exception: return None
for c in cands:
    p, src = c["p"], c["src"]
    if not os.path.isfile(p): continue
    d = load(p)
    if d is None: continue
    if src in ("settings.pluginConfigs", "credentials.pluginSecrets"):
        sec = d.get(src.split(".")[1]) or {}
        for k in sec:
            if k.split("@", 1)[0] != plugin: continue
            raw = sec[k]
            v = raw.get("options", raw) if isinstance(raw, dict) else None
            v = dig(v, key) if isinstance(v, dict) else None
            if v in (None, ""): continue
            _emit(v); sys.exit(0)
        continue
    v = dig(d, key)
    if v in (None, ""): continue
    _emit(v); sys.exit(0)
sys.exit(1)
' "$key" "$plugin" 2>/dev/null)" || true
    if [[ -n "$out" ]]; then printf '%s\n' "$out"; return 0; fi
    if [[ -n "$default" ]]; then printf '%s\n' "$default"; return 0; fi
    return 1
}

# f_conf_set <key> <value> — 写入用户自填文件（升级不覆盖的那个位置）
f_conf_set() {
    local key="$1" val="$2" plugin dir file
    plugin="$(f_plugin_name)" || return 1
    dir="$(f_user_config_dir)"; mkdir -p "$dir"
    file="$dir/$plugin.yaml"
    python3 - "$file" "$key" "$val" <<'PYEOF'
import sys, os
path, key, val = sys.argv[1:4]
try:
    import yaml
except ImportError:
    sys.stderr.write("[fcore] 需要 PyYAML: pip install pyyaml\n"); sys.exit(2)
d = {}
if os.path.isfile(path):
    try: d = yaml.safe_load(open(path)) or {}
    except Exception: d = {}
node = d
parts = key.split(".")
for k in parts[:-1]:
    if not isinstance(node.get(k), dict): node[k] = {}
    node = node[k]
node[parts[-1]] = val
with open(path, "w") as f:
    f.write("# 用户自填配置 — 由 fcore conf set 维护，/plugin update 不会覆盖此文件\n")
    yaml.safe_dump(d, f, allow_unicode=True, sort_keys=False)
print(path)
PYEOF
}

# f_conf_require <key> — 缺失时打印"去哪填"并返回非零
f_conf_require() {
    f_conf_get "$1" >/dev/null 2>&1 && return 0
    local plugin; plugin="$(f_plugin_name 2>/dev/null || echo '<plugin>')"
    {
        echo "[fcore] 缺少配置: $1  (plugin: $plugin)"
        echo "  任选其一："
        echo "    a) fcore conf set $1 <值>          # 写到 $(f_user_config_dir)/$plugin.yaml（推荐，升级不丢）"
        echo "    b) claude plugin configure $plugin  # 官方弹窗"
        echo "    c) mkdir -p \$(f_ccprivate_root)/conf 后写入 $plugin.yaml"
        echo "  不填也能用：相关能力降级，跳过需要该值的步骤。"
    } >&2
    return 1
}

# f_conf_path <key> — 打印该键命中的文件（诊断）
f_conf_path() {
    local key="$1" plugin
    plugin="$(f_plugin_name 2>/dev/null || echo "")"
    [[ -n "$plugin" ]] || { echo "(无 plugin)"; return 1; }
    f_config_candidates "$plugin" | python3 -c '
import json, os, sys
key, plugin = sys.argv[1], sys.argv[2]
for c in json.load(sys.stdin):
    p = c["p"]
    if not os.path.isfile(p): continue
    try:
        d = (__import__("yaml").safe_load(open(p)) if p.endswith((".yaml",".yml")) else json.load(open(p))) or {}
    except Exception: continue
    node = d
    ok = True
    for k in key.split("."):
        if isinstance(node, dict) and k in node: node = node[k]
        else: ok = False; break
    if ok and node not in (None, ""):
        print(p); sys.exit(0)
print("(未命中任何源)"); sys.exit(1)
' "$key" "$plugin"
}

# f_conf_file <relpath> — 取**用户数据文件**的绝对路径（不是配置）。
#
# 与 f_conf_get 的区别：那个按 key 查配置值，这个按相对路径取整个文件
# （课程进度 fcourse/<slug>.yaml 这种结构自由的用户数据）。
# 查找顺序：ccprivate/conf/ → 用户数据目录 → plugin 目录。
# 都不存在时输出"期望路径"（用户数据目录下），调用方可直接创建。
f_conf_file() {
    local rel="$1" plugin f
    plugin="$(f_plugin_name 2>/dev/null || echo "")"
    if f="$(f_ccprivate_root 2>/dev/null)"; then
        [[ -f "$f/conf/$rel" ]] && { printf '%s\n' "$f/conf/$rel"; return 0; }
        [[ -f "$f/$rel" ]] && { printf '%s\n' "$f/$rel"; return 0; }
    fi
    if [[ -n "$plugin" ]]; then
        local ud; ud="$(f_userdata_dir "$plugin")"
        [[ -f "$ud/$rel" ]] && { printf '%s\n' "$ud/$rel"; return 0; }
        [[ -d "$ud" ]] || mkdir -p "$ud" 2>/dev/null
        printf '%s\n' "$ud/$rel"; return 0
    fi
    return 1
}

# f_conf_files <subdir> — 列出用户数据目录里符合前缀的文件（课程列表用）
f_conf_files() {
    local pattern="$1" plugin roots
    plugin="$(f_plugin_name 2>/dev/null || echo "")"
    { f_ccprivate_root 2>/dev/null | sed 's|$|/conf|'
      [[ -n "$plugin" ]] && f_userdata_dir "$plugin"; } | while read -r d; do
        [[ -d "$d" ]] || continue
        compgen -G "$d/$pattern" 2>/dev/null || true
    done
}

export -f f_user_config_dir f_userdata_dir f_ccprivate_root f_plugin_dir f_plugin_name \
          f_config_candidates f_conf_get f_conf_set f_conf_require f_conf_path f_conf_file f_conf_files 2>/dev/null || true
