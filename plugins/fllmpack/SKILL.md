---
name: fllmpack
user-invocable: true
description: |
  LLM 预设配置导出/导入 — 把本机 LLM 预设（内置+自定义）打包成不含任何 API key 的
  配置包，发给同事导入后各自填 key。导出物自包含（附脚本副本），收件方无需装本 skill
  即可导入。默认输出 C:\claudepack（WSL /mnt/c/claudepack）。
  用法：用户说"导出 LLM 配置"/"打包 LLM"/"把模型配置给同事"/"导入 LLM 配置"/"导入预设包"触发。
allowed-tools: Read, Write, Bash
---

# fllmpack — LLM 预设配置导出/导入

把 LLM 预设**定义**（base_url / model / 上下文窗口等）打包分发，**key 永不进包**，收件方自己填。

## 配置来源（三层，读取时合并）

| 文件 | 内容 | 含 key |
|------|------|--------|
| `ccconfig/conf/llmnormal.json` | 内置预设（开源模板） | ✗ |
| `ccprivate/conf/llmprivate.json` | 自定义预设（私有） | ✗ |
| `ccprivate/conf/llm.json` | 纯 key：`{llms:{name:{key}}}` | ✓ **不进包** |

导出 = 合并前两者，剥掉任何 key 字段。
导入 = 写回 `llmprivate.json` + 在 `llm.json` 建空 key 记录。

## 命令

脚本路径：`~/.claude/skills/fllmpack/llmpack.py`
（ccprivate 用户可直接用 `python3 $HOME/git/skill/plugins/fllmpack/llmpack.py`）

```bash
# 导出（默认全部预设，输出 /mnt/c/claudepack/llm-pack-<时间戳>/ + .tar.gz）
python3 ~/.claude/skills/fllmpack/llmpack.py export
python3 ~/.claude/skills/fllmpack/llmpack.py export --preset officedsflash --preset homedsflash
python3 ~/.claude/skills/fllmpack/llmpack.py export --out /mnt/c/claudepack    # 显式指定
python3 ~/.claude/skills/fllmpack/llmpack.py export --sanitize   # 额外清内网 IP/域名，给公司外的人

# 导入（支持 presets.json / .tar.gz / 解压目录）
python3 ~/.claude/skills/fllmpack/llmpack.py import /mnt/c/claudepack/llm-pack-XXX.tar.gz
python3 ~/.claude/skills/fllmpack/llmpack.py import presets.json --overwrite --set-current officedsflash
python3 ~/.claude/skills/fllmpack/llmpack.py import presets.json --no-key-prompt   # 非交互

# 查看
python3 ~/.claude/skills/fllmpack/llmpack.py list      # 预设 + 来源 + key 有无 + base_url
python3 ~/.claude/skills/fllmpack/llmpack.py status    # 路径/文件存在性诊断
```

## 工作流

### 导出给同事
1. `export`（内网同事）或 `export --sanitize`（公司外的人——清掉内网 IP 和域名）
2. 产物：`/mnt/c/claudepack/llm-pack-<ts>/`{presets.json, README.md, fllmpack.py} + 同名 `.tar.gz`
3. 把 **tar.gz** 发给同事（Windows 路径 `C:\claudepack\...`，方便拖拽）

### 同事导入
```bash
python3 fllmpack.py import presets.json     # 包自带脚本，无需装 skill
```
脚本会：备份 `llmprivate.json` → 写入预设 → 在 `llm.json` 建空 key → 交互询问 key。
之后 `bash ~/git/ccconfig/lib/init-llm.sh <预设名>` 切换，**重启 session** 生效。

## 注意
- **key 永不进包**。导出时按字段名（key/api_key/token/secret 等）过滤，`presets.json` 里只会是定义
- `--sanitize` 只影响 `base_url`/`url`/`host_header`；内网预设（如 `homedsflash` 指向 `100.x.x.x`）**不加 `--sanitize` 给外部人 = 泄露内网地址**
- 导入默认**不覆盖**同名预设，要覆盖加 `--overwrite`
- 无 ccprivate 的机器（纯 Claude Code 用户）导入到 `~/.claude/fllmpack/presets.json`，需手工并入其 LLM 配置
- 输出目录优先 `$FLLMPACK_OUT`，其次 `/mnt/c/claudepack`（WSL），非 WSL 落 `~/claudepack`