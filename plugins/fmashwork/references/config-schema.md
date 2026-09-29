# fmashwork config.yaml 字段说明

> 真实配置文件路径：`ccprivate/skill/fmashwork.yaml`（通过 init-skill.sh symlink 到 `~/.claude/skills/fmashwork/config.yaml`）。
> 公开仓库仅放 `config.yaml.example`（占位符），独立用户用 `cp config.yaml.example config.yaml` 填值。

## 字段

### feishu

| 字段 | 必填 | 说明 |
|------|------|------|
| `space_id` | 是 | 飞书知识库 space_id，wiki +node-list 时需要 |
| `root_node_token` | 是 | meshwork 孵化项目根 wiki 节点 token |
| `root_node_url` | 是 | 根节点 URL，新文档默认父目录 |

### shared_dir

WSL ↔ Windows 共享目录，厂商网页下载的文件落地到这里。
Windows 用户典型路径：`/mnt/c/Users/<username>/3dprints`。

### printer

| 字段 | 说明 |
|------|------|
| `model` | 拓竹机型（X1C / P1S / A1 / H2D 等） |
| `studio_windows_path` | Bambu Studio Windows 安装路径，handoff 时提示用户 |

### channels

厂商网页版 URL，目前固定两个（混元3D、Meshy 官方）。**勿填第三方假站**（如 meshyai.net）。

## 验证

跑 `python3 scripts/fmashwork.py check-env --config`，脚本会读 `config.yaml` 并校验路径可达性 / URL 格式。
