---
name: getnote
user-invocable: true
description: |
  得到大脑(Get笔记) 集成 — MCP 工具驱动。笔记 CRUD、语义搜索、知识库管理、图片上传、博主内容、直播。
  Use when 用户说"记笔记"/"保存到得到"/"搜笔记"/"搜知识库"/"我的笔记"/"知识库"/"博主"/"直播"/"上传图片到得到"。
allowed-tools: Bash, Read, Write,
  mcp__getnote__add_note_tags, mcp__getnote__batch_add_notes_to_topic,
  mcp__getnote__create_topic, mcp__getnote__create_topic_directory,
  mcp__getnote__delete_note, mcp__getnote__delete_note_tag,
  mcp__getnote__delete_topic_directory, mcp__getnote__follow_topic_blogger,
  mcp__getnote__follow_topic_live, mcp__getnote__get_blogger_content_detail,
  mcp__getnote__get_knowledge_file_capabilities, mcp__getnote__get_knowledge_file_upload_token,
  mcp__getnote__get_live_detail, mcp__getnote__get_note,
  mcp__getnote__get_note_attachments, mcp__getnote__get_note_chapters,
  mcp__getnote__get_note_marks, mcp__getnote__get_note_original,
  mcp__getnote__get_note_quick_note, mcp__getnote__get_note_task_progress,
  mcp__getnote__get_note_timeline, mcp__getnote__get_note_todos,
  mcp__getnote__get_note_transcript, mcp__getnote__get_quota,
  mcp__getnote__get_sprout, mcp__getnote__get_upload_config,
  mcp__getnote__get_upload_token, mcp__getnote__list_notes,
  mcp__getnote__list_sprouts, mcp__getnote__list_subscribe_topics,
  mcp__getnote__list_topic_blogger_contents, mcp__getnote__list_topic_bloggers,
  mcp__getnote__list_topic_directories, mcp__getnote__list_topic_lives,
  mcp__getnote__list_topic_notes, mcp__getnote__list_topics,
  mcp__getnote__recall, mcp__getnote__recall_knowledge,
  mcp__getnote__remove_note_from_topic, mcp__getnote__save_note,
  mcp__getnote__share_note, mcp__getnote__update_note,
  mcp__getnote__update_topic_directory, mcp__getnote__upload_image,
  mcp__getnote__upload_knowledge_file
---

# getnote — 得到大脑 MCP 集成

45 个 MCP tools 覆盖得到大脑全部功能。所有操作通过 MCP tool call 直接执行，不走 Bash CLI。

## 配置

> 📖 完整说明 → [config.aiagt.dev](https://config.aiagt.dev/getnote)

**ccconfig 用户**：MCP server 配置由 `init-mcp.sh` 管理，Key 在 `ccprivate/conf/claude.json`。运行 `bash init-mcp.sh keys` 交互填 Key。
**独立用户**：在 `~/.claude/settings.json` 的 `mcpServers` 中添加 getnote MCP server：
```json
{
  "mcpServers": {
    "getnote": {
      "command": "npx",
      "args": ["-y", "@getnote/mcp"],
      "env": {
        "GETNOTE_API_KEY": "<your-api-key>",
        "GETNOTE_CLIENT_ID": "<your-client-id>"
      }
    }
  }
}
```

获取 API Key 和 Client ID：打开 [biji.com/openapi](https://www.biji.com/openapi) → 创建应用。
- API Key 格式：`gk_live_xxx`
- Client ID 格式：`cli_xxx`

## 意图 → Tool 映射

### 笔记 CRUD

| 用户说 | Tool |
|--------|------|
| "记笔记"/"保存"/"记录下来" | `save_note` |
| "我的笔记"/"最近笔记" | `list_notes` |
| "查看笔记"/"打开笔记" | `get_note` |
| "更新笔记"/"修改笔记" | `update_note` |
| "删除笔记" | `delete_note` |
| "分享笔记" | `share_note` |
| "笔记进度"/"处理状态" | `get_note_task_progress` |

### 笔记原文直读（v1.8 新增）

按 note_type 直接取原文字段，不读 AI 摘要。链接→网页原文，录音→转写，文字→正文。

| 用户说 | Tool |
|--------|------|
| "读原文"/"看原文" | `get_note_original` |
| "转写文本"/"录音原文" | `get_note_transcript` |
| "时间线"/"结构化时间线" | `get_note_timeline` |
| "章节"/"章节时间线" | `get_note_chapters` |
| "标记"/"笔记标记" | `get_note_marks` |
| "待办"/"从会议提取待办" | `get_note_todos` |
| "快捷笔记" | `get_note_quick_note` |
| "附件"/"笔记里的图片音频" | `get_note_attachments` |

### 标签

| 用户说 | Tool |
|--------|------|
| "加标签"/"打标签" | `add_note_tags` |
| "删标签"/"去掉标签" | `delete_note_tag` |

### 搜索

| 用户说 | Tool |
|--------|------|
| "搜笔记"/"搜索"/"查找" | `recall` |
| "搜知识库"/"在知识库搜" | `recall_knowledge` |

### 知识库

| 用户说 | Tool |
|--------|------|
| "我的知识库"/"知识库列表" | `list_topics` / `list_subscribe_topics` |
| "创建知识库" | `create_topic` |
| "知识库里有什么"/"查看知识库笔记" | `list_topic_notes` |
| "加入知识库"/"添加到知识库" | `batch_add_notes_to_topic` |
| "移出知识库" | `remove_note_from_topic` |
| "知识库目录"/"文件夹结构" | `list_topic_directories` |
| "创建文件夹" | `create_topic_directory` |
| "重命名文件夹"/"移动文件夹" | `update_topic_directory` |
| "删除文件夹"（破坏性，须用户确认） | `delete_topic_directory` |

### 博主内容

| 用户说 | Tool |
|--------|------|
| "博主列表"/"关注了哪些博主" | `list_topic_bloggers` |
| "博主发了什么"/"博主内容" | `list_topic_blogger_contents` |
| "查看博主内容详情" | `get_blogger_content_detail` |
| "订阅博主"/"关注抖音博主到知识库" | `follow_topic_blogger` |

### 直播

| 用户说 | Tool |
|--------|------|
| "直播列表"/"有什么直播" | `list_topic_lives` |
| "直播详情" | `get_live_detail` |
| "预约直播"/"关注直播" | `follow_topic_live` |

### 知识库文件上传（v1.8 新增）

| 用户说 | Tool |
|--------|------|
| "上传文件到知识库"/"传 PDF 到知识库" | `get_knowledge_file_capabilities` → `get_knowledge_file_upload_token` → `upload_knowledge_file` |

### 发芽报告

| 用户说 | Tool |
|--------|------|
| "发芽报告"/"每月发芽" | `list_sprouts` |
| "发芽原文"/"读发芽报告" | `get_sprout` |

### 图片上传

| 用户说 | Tool |
|--------|------|
| "上传图片"/"传图到得到" | `get_upload_config` → `get_upload_token` → `upload_image` |

### 配额

| 用户说 | Tool |
|--------|------|
| "配额"/"还剩多少" | `get_quota` |

## 常用工作流

### 1. 会议/对话笔记 → 打标签 → 入知识库

```
1. save_note(content="会议纪要：...", title="XX会议")
2. add_note_tags(note_id="<id>", tags=["会议", "AI"])
3. batch_add_notes_to_topic(topic_id="<kb_id>", note_ids=["<id>"])
```

### 2. 搜索 → 查看详情 → 补充笔记

```
1. recall(query="RAG 架构")
2. get_note(note_id="<result_id>")
3. update_note(note_id="<id>", content="...补充内容")
```

### 3. 研究 → 保存到得到（与 fresearchframe 协作）

```
1. fresearchframe 执行搜索研究
2. 整理结论后 save_note(content="研究结论：...")
3. add_note_tags(tags=["调研", "<topic>"])
```

### 4. 上传图片

```
1. get_upload_config() → 获取上传配置
2. get_upload_token(config) → 获取上传 token
3. upload_image(token, image_path) → 上传
```

## 参数约定

- **笔记标题**: 中文简洁标题，不超 30 字。会议笔记格式 `YYYY-MM-DD <主题>会议纪要`
- **内容格式**: Markdown。AI 生成内容用 `> 🤖 AI 生成` 标注
- **标签**: 小写下划线，如 `ai`, `meeting`, `research`。中文可用但推荐英文
- **知识库**: 按主题组织。一个项目一个 KB，不跨项目混用

## 集成

- `fresearchframe` — 研究完成后 `save_note` 保存结论
- `flogme` — SUM/OKR 总结时可搜笔记做回顾
- `fdiagram` — 生成的架构图可 `upload_image` 到得到
- `ffeishu` — 飞书文档内容可提取后 `save_note` 到得到

## 升级

MCP server: `npm update -g @getnote/mcp`（或 `init-skill.sh update` 自动更新）
Skill: `git -C ~/git/claude-skills pull`（init-skill.sh sync 自动拉取）
