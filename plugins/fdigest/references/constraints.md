# fdigest 关键约束与 workflow 边界

## 什么时候走 workflow（wf-fdigest）

`wf-fdigest` 是本 skill 的**确定性重活**部分：预检 → 索引 → 翻译 → 排版 → 格式断言，
跑完停在**交付前**。

**为什么拆出去**：实测首战 S-1 全流程 445 次 Bash 里，只有 18% 走到脚本，
49% 是现场手写 python 和格式返工。这些环节没有判断空间，只是要跑对——
该由代码编排，不该由模型每次重新发明。

**为什么停在交付前**：详解撰写要论断可复核、上传删除不可逆，这两件必须人看。
workflow 只保证「产物正确且可上传」，不替人做决定。

```bash
# 结构包已存在时
Workflow({name: "wf-fdigest", args: "<slug>"})
```

不在 workflow 范围内的（留在主上下文）：抓取源文件（要看 URL 是否可信）、
写分节详解（要判断什么值得说）、决定传哪个父节点、删哪些旧节点。

## 脚本清单

| 脚本 | 职责 | 输入 → 输出 |
|---|---|---|
| `extract.py` | 结构化抽取 | 源文件 → pages/heads/tables/images/text + manifest |
| `index.py` | 建段落级索引 | 结构包 → SQLite FTS5 |
| `search.py` | 中英文检索 | 查询 → 页码 + 章节 + 片段 + 飞书链接 |
| `llm.py` | **公共 LLM 层**（与 fpdf / transliter 共用） | 预设 + 协议自适应 + flock 并发闸 + 429 退避 |
| `prepare_images.py` | 下载 + 压缩原文图片 | manifest+images → `~/files/fdigest/<slug>-images/` |
| `build_zh.py` | 版面结构还原 + 嵌图 + 切段 | 结构包 → DocxXML / 按块数切好的 zh-parts |
| `translate_blocks.py` | 块级翻译（推荐） | 结构包 → zh-blocks/NNNN.json |
| `translate.py` | 逐行翻译（旧） | 结构包 → 逐页逐行 JSON |
| `render_zh.py` | 逐行译文拼装（旧） | 逐行 JSON → DocxXML |
| `parents_tpl.xml` 等 | 文档模板 | 占位符 → 可上传 XML |

## 与 fpdf 的关系