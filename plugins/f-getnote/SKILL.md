---
name: f-getnote
user-invocable: true
description: |
  得到大脑（Get笔记）操作 — 保存笔记、搜索笔记、管理知识库、查看博主内容/直播。
  Use when 用户说"记笔记"/"存笔记"、"搜笔记"、"我的笔记"、"知识库"、
  "得到大脑"/"get笔记"、"查看博主"/"直播摘要"、或想操作得到大脑中的内容。
allowed-tools: Bash
---

# f-getnote — 得到大脑（Get笔记）操作

通过 `getnote` CLI 管理得到大脑笔记和知识库。CLI 已认证，凭证存 `~/.getnote/config.json`。

## 前置条件

调用前确认 CLI 可用：

```bash
getnote auth status 2>&1 || echo "NEED_AUTH"
```

输出 `NEED_AUTH` 时引导用户运行 `getnote auth login` 或从 ccprivate 恢复凭证：

```bash
API_KEY=$(python3 -c "import json; print(json.load(open('$HOME/git/ccprivate/conf/getnote.json'))['api_key'])")
CLIENT_ID=$(python3 -c "import json; print(json.load(open('$HOME/git/ccprivate/conf/getnote.json'))['client_id'])")
getnote auth login --api-key "$API_KEY" --client-id "$CLIENT_ID"
```

## 命令速查

所有命令加 `-o json` 输出结构化数据供解析。

### 保存笔记

```bash
getnote save "<文字或URL>" --title "标题" --tag "标签"
getnote save "https://example.com" --title "好文章" --tag "待读"
getnote save "随手记的想法" --tag "灵感"
getnote save ./screenshot.png --title "设计稿"
```

- URL → 链接笔记（异步，CLI 自动轮询）
- 图片路径 → 图片笔记
- 其他文字 → 文字笔记

### 查看笔记

```bash
getnote notes -o json                    # 最近 20 条
getnote notes --all -o json              # 全部笔记
getnote note <id> -o json                # 笔记详情
getnote note <id> --field content        # 只看内容/总结
getnote note <id> --field web_content    # 链接笔记原文
getnote note <id> --field audio_original # 录音转写原文
```

**关键**：不同笔记类型原文在不同字段：

| 笔记类型 | 原文字段 | AI总结字段 |
|---------|---------|-----------|
| 文字笔记 | `content` | `content` |
| 链接笔记 | `web_content` | `content` |
| 录音笔记 | `audio_original` | `content` |
| 博主内容 | `post_media_text` (via `kb blogger-content`) | `content` |
| 直播 | `post_media_text` (via `kb live`) | `post_summary` |

用户说"读原文"时，先查 `note_type`，再取对应字段。

### 搜索笔记

```bash
getnote search "<关键词>" -o json           # 全局语义搜索，最多10条
getnote search "<关键词>" --kb <topic_id> -o json  # 限定知识库
```

### 更新/删除笔记

```bash
getnote note update <id> --title "新标题"
getnote note update <id> --content "新内容"   # 仅文字笔记
getnote note update <id> --tag "tag1,tag2"   # 替换所有标签
getnote note delete <id> -y                   # 删除（进回收站）
getnote note share <id>                       # 生成分享链接
```

### 标签

```bash
getnote tag list <note_id> -o json           # 查看标签
getnote tag add <note_id> "标签名"            # 添加
getnote tag remove <note_id> <tag_id>         # 删除（需 tag ID，非名称）
```

### 知识库

```bash
getnote kbs -o json                          # 列出我的知识库
getnote kbs-sub -o json                      # 订阅的知识库
getnote kb <topic_id> -o json                # 知识库内笔记
getnote kb <topic_id> --all -o json          # 全部笔记
getnote kb create "名称" --desc "描述"        # 创建（日限50）
getnote kb add <topic_id> <note_id> ...      # 加入知识库（最多20条/次）
getnote kb remove <topic_id> <note_id> ...   # 移出知识库
```

### 博主内容

```bash
getnote kb bloggers <topic_id> -o json                # 博主列表
getnote kb blogger-contents <topic_id> <follow_id>    # 内容列表
getnote kb blogger-content <topic_id> <post_id> -o json  # 内容详情（含原文）
```

### 直播

```bash
getnote kb lives <topic_id> -o json                   # 已完成的直播
getnote kb live <topic_id> <live_id> -o json          # 直播详情（AI摘要+转写）
getnote kb live-follow <topic_id> <url>               # 订阅直播到知识库
```

### 配额

```bash
getnote quota -o json
```

## 常用工作流

### 工作流 1：边聊边记

用户说"帮我记一下..."时：
```bash
getnote save "<内容>" --tag "<上下文标签>"
```

### 工作流 2：搜索回忆

用户问"我之前记过关于X的..."时：
```bash
getnote search "<关键词>" -o json
# 如有结果，展示标题+摘要，询问是否需要完整内容
```

### 工作流 3：整理到知识库

```bash
# 先搜索找到目标笔记
getnote search "<关键词>" -o json
# 查看知识库列表
getnote kbs -o json
# 加入知识库
getnote kb add <topic_id> <note_id>
```

### 工作流 4：阅读博主/直播内容

```bash
# 1. 找知识库
getnote kbs -o json
# 2. 查博主
getnote kb bloggers <topic_id> -o json
# 3. 内容列表
getnote kb blogger-contents <topic_id> <follow_id> -o json
# 4. 看全文
getnote kb blogger-content <topic_id> <post_id> -o json
```

## 注意事项

- Note ID 是 int64，JSON 解析时当字符串处理，避免 JS 精度丢失
- 搜索最多返回 10 条；浏览用 `getnote notes --all`
- 知识库创建日限 50 个，北京时间 00:00 重置
- 订阅知识库只能读，不能增删笔记
- `--tag` 更新是替换语义，不是追加；部分修改用 `tag add/remove`
- 链接笔记和图片笔记是异步创建，CLI 自动轮询等待

## 输出约定

- 操作完成后给出笔记链接：`https://biji.com/note/{note_id}`
- 多条结果用简洁列表展示（标题 + 日期 + 摘要片段）
- 搜索结果标注相关性分数（score）
