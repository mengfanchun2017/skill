#!/bin/bash
# doctor.sh — fcore 体检（L0 健康检查）
#
# 用法：
#   source lib/doctor.sh
#   f_doctor            # 全量体检，返回 0=全绿
#   f_doctor --json     # JSON 输出

_f_doctor_check() {
    local name="$1" status="$2" detail="$3"
    printf '  %s  %-20s %s\n' "$status" "$name" "$detail"
}

f_doctor() {
    local json=false
    [[ "${1:-}" == "--json" ]] && json=true

    local all_ok=true
    local -a results=()

    _dr() {
        local name="$1" ok="$2" detail="$3"
        if $json; then
            results+=("{\"check\":\"$name\",\"ok\":$ok,\"detail\":\"$detail\"}")
        else
            if [[ "$ok" == "true" ]]; then
                printf '  ✅  %-20s %s\n' "$name" "$detail"
            else
                printf '  ❌  %-20s %s\n' "$name" "$detail"
                all_ok=false
            fi
        fi
    }

    # 1. lark-cli
    if command -v lark-cli &>/dev/null; then
        local lark_ver; lark_ver=$(lark-cli --version 2>/dev/null | head -1)
        _dr "lark-cli" "true" "${lark_ver:-installed}"
    else
        _dr "lark-cli" "false" "未安装"
    fi

    # 2. OfficeCLI
    if command -v officecli &>/dev/null; then
        local oc_ver; oc_ver=$(officecli --version 2>/dev/null | head -1)
        _dr "OfficeCLI" "true" "${oc_ver:-installed}"
        # libicu check
        if ldd "$(command -v officecli)" 2>/dev/null | grep -q libicu; then
            if ldconfig -p 2>/dev/null | grep -q libicu; then
                : # ok
            else
                _dr "  libicu" "false" "OfficeCLI 需要 libicu（apt install libicu78）"
            fi
        fi
    else
        _dr "OfficeCLI" "false" "未安装"
    fi

    # 3. uv
    if command -v uv &>/dev/null; then
        local uv_ver; uv_ver=$(uv --version 2>/dev/null | head -1)
        _dr "uv" "true" "${uv_ver:-installed}"
    else
        _dr "uv" "false" "未安装"
    fi

    # 4. 代理（配置了但不可达则告警）
    local proxy="${HTTPS_PROXY:-${https_proxy:-${HTTP_PROXY:-${http_proxy:-}}}}"
    if [[ -n "$proxy" ]]; then
        local host="${proxy#*://}"; host="${host%:*}"
        if timeout 2 bash -c "echo >/dev/tcp/$host/7897" 2>/dev/null; then
            _dr "proxy" "true" "$proxy"
        else
            _dr "proxy" "false" "配置了但不可达: $proxy"
        fi
    else
        _dr "proxy" "true" "未配置（直连）"
    fi

    # 5. Git 配置
    if git config --global user.name &>/dev/null && git config --global user.email &>/dev/null; then
        _dr "git config" "true" "$(git config --global user.name)"
    else
        _dr "git config" "false" "缺少 user.name/email"
    fi
    # gh auth
    if gh auth status 2>/dev/null; then
        _dr "gh auth" "true" "可用"
    else
        _dr "gh auth" "false" "PAT 失效/未配置"
    fi

    # 6. ccprivate
    local ccpriv; ccpriv=$(f_ccprivate_root 2>/dev/null || true)
    if [[ -n "$ccpriv" && -d "$ccpriv" ]]; then
        _dr "ccprivate" "true" "$ccpriv"
    else
        _dr "ccprivate" "false" "未找到（独立模式可忽略）"
    fi

    # 7. fcore 自身
    if f_conf_get "fcore.test" "ok" &>/dev/null; then
        _dr "fcore" "true" "配置系统正常"
    else
        _dr "fcore" "false" "配置系统异常"
    fi

    # 8. 飞书 auth
    local lark_rc=0
    f_lark_need_auth &>/dev/null || lark_rc=$?
    case $lark_rc in
        0) _dr "feishu auth" "true" "已授权" ;;
        1) _dr "feishu auth" "false" "lark-cli 未安装" ;;
        2) _dr "feishu auth" "false" "未授权/过期" ;;
    esac

    if $json; then
        local IFS=','
        echo "[${results[*]}]"
    fi

    $all_ok
}
