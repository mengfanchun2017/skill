#!/bin/bash
# doctor.sh — fcore 体检 + 自修复（L0）
#
# 用法：
#   source lib/doctor.sh
#   f_doctor              只检不修，返回 0=全绿
#   f_doctor --fix        检查 + 自动修复可修项
#   f_doctor --json       只检，JSON 输出

_f_doctor_check() {
    local name="$1" status="$2" detail="$3"
    printf '  %s  %-20s %s\n' "$status" "$name" "$detail"
}

# 静默运行安装命令。成功=不影响 all_ok，失败=不阻止其他修复。
_try_fix() {
    local label="$1" cmd="$2"
    echo "  🔧  正在修复 $label..."
    if eval "$cmd" 2>/dev/null; then
        echo "  ✅  $label 已修复"
        return 0
    else
        echo "  ⚠️   $label 修复失败（可忽略或手动装）"
        return 1
    fi
}

f_doctor() {
    local fix_mode=false json=false
    for arg in "$@"; do
        [[ "$arg" == "--fix" ]] && fix_mode=true
        [[ "$arg" == "--json" ]] && json=true
    done

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

    # ====== 1. lark-cli ======
    if command -v lark-cli &>/dev/null; then
        local lv; lv=$(lark-cli --version 2>/dev/null | head -1)
        _dr "lark-cli" "true" "${lv:-installed}"
    else
        _dr "lark-cli" "false" "未安装"
        $fix_mode && _try_fix "lark-cli" "npm install -g @larksuite/cli 2>&1"
    fi

    # ====== 2. OfficeCLI + libicu ======
    if command -v officecli &>/dev/null; then
        local ov; ov=$(officecli --version 2>/dev/null | head -1)
        _dr "OfficeCLI" "true" "${ov:-installed}"
        if ldd "$(command -v officecli)" 2>/dev/null | grep -q libicu; then
            if ! ldconfig -p 2>/dev/null | grep -q libicu; then
                _dr "  libicu" "false" "OfficeCLI 需要 libicu"
                $fix_mode && _try_fix "libicu" "sudo apt-get install -y libicu78 2>/dev/null || sudo apt-get install -y libicu74 2>/dev/null || sudo apt-get install -y libicu72 2>/dev/null || true"
            fi
        fi
    else
        _dr "OfficeCLI" "false" "未安装"
        $fix_mode && _try_fix "OfficeCLI" "curl -fsSL https://d.officecli.ai/install.sh | bash"
    fi

    # ====== 3. uv ======
    if command -v uv &>/dev/null; then
        local uv_ver; uv_ver=$(uv --version 2>/dev/null | head -1)
        _dr "uv" "true" "${uv_ver:-installed}"
    else
        _dr "uv" "false" "未安装"
        $fix_mode && _try_fix "uv" "curl -LsSf https://astral.sh/uv/install.sh | sh"
    fi

    # ====== 4. proxy ======
    local proxy="${HTTPS_PROXY:-${https_proxy:-${HTTP_PROXY:-${http_proxy:-}}}}"
    if [[ -n "$proxy" ]]; then
        local host="${proxy#*://}"; host="${host%:*}"
        if timeout 2 bash -c "echo >/dev/tcp/$host/7897" 2>/dev/null; then
            _dr "proxy" "true" "$proxy"
        else
            _dr "proxy" "false" "配置了但不可达: $proxy"
            # 不可自动修 — 网络问题
        fi
    else
        _dr "proxy" "true" "未配置（直连）"
    fi

    # ====== 5. git config + gh auth ======
    if git config --global user.name &>/dev/null && git config --global user.email &>/dev/null; then
        _dr "git config" "true" "$(git config --global user.name)"
    else
        _dr "git config" "false" "缺少 user.name/email"
        if $fix_mode && gh auth status 2>/dev/null; then
            local gh_name gh_email
            gh_name=$(gh api user --jq '.name // .login' 2>/dev/null || echo "")
            gh_email=$(gh api user --jq '.email' 2>/dev/null || echo "")
            [[ -n "$gh_name" ]]  && git config --global user.name "$gh_name"
            [[ -n "$gh_email" ]] && git config --global user.email "$gh_email"
            if git config --global user.name &>/dev/null && git config --global user.email &>/dev/null; then
                echo "  ✅  git config 已从 GitHub 自动设置"
            fi
        fi
    fi
    if gh auth status >/dev/null 2>&1; then
        _dr "gh auth" "true" "可用"
    else
        _dr "gh auth" "false" "PAT 失效/未配置"
        # 不可自动修 — 需用户续期
    fi

    # ====== 6. ccprivate ======
    local ccpriv; ccpriv=$(f_ccprivate_root 2>/dev/null || true)
    if [[ -n "$ccpriv" && -d "$ccpriv" ]]; then
        _dr "ccprivate" "true" "$ccpriv"
    else
        _dr "ccprivate" "false" "未找到（独立模式可忽略）"
    fi

    # ====== 7. fcore 自身 ======
    if f_conf_get "fcore.test" "ok" &>/dev/null; then
        _dr "fcore" "true" "配置系统正常"
    else
        _dr "fcore" "false" "配置系统异常"
    fi

    # ====== 8. 飞书 auth ======
    local lark_rc=0
    f_lark_need_auth &>/dev/null || lark_rc=$?
    case $lark_rc in
        0) _dr "feishu auth" "true" "已授权" ;;
        1) _dr "feishu auth" "false" "lark-cli 未安装" ;;
        2) _dr "feishu auth" "false" "未授权/过期"
           if $fix_mode; then
               echo "  🔧  飞书需重新授权 — 启动 QR 扫码..."
               local qr_out
               qr_out=$(lark-cli auth login --scope "docx:document:create,docx:document:readonly,drive:drive:readonly,base:base:readonly,base:base:write" --no-wait --json 2>&1 || true)
               local vu; vu=$(echo "$qr_out" | python3 -c "import json,sys; print(json.load(sys.stdin).get('verification_url',''))" 2>/dev/null || true)
               if [[ -n "$vu" ]]; then
                   echo "  🔗  请扫码: $vu"
                   echo "  扫码后等待授权完成...（约 60s）"
               else
                   echo "  ⚠️  无法启动 QR 授权，手动: lark-cli auth login"
               fi
           fi
           ;;
    esac

    if $json; then
        local IFS=','
        echo "[${results[*]}]"
    fi

    $all_ok
}
