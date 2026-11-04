# fmoocrec 格式约束、委派规则与维护

## 课程推荐格式约束

生成学习路径/课程推荐时：

1. **表格必须 XML + colgroup=822**（飞书 Wiki 渲染要求）
2. **不手动编号**（飞书自动编号）
3. **不用 H4+**（最深 H3）
4. **不用 `---` 分割线**
5. **课程链接必须是完整可点击 URL**（禁止 bit.ly 等短链接，易失效）
6. **每门课必须同时列出免费方案和证书方案**（双轨）
7. **证书信息必须包含验证方式**
8. **图表必须用 `<whiteboard type="mermaid">` XML 语法**，禁止 ASCII 字符画或 Markdown fenced code block（Markdown mermaid code block 不会自动转换为白板，只有 XML `<whiteboard>` 标签会）

   ```xml
   <!-- ✅ 正确 -->
   <whiteboard type="mermaid">
   timeline
       title 三阶段路线
       阶段一 : 内容A
       阶段二 : 内容B
   </whiteboard>
   ```
   
   ```markdown
   <!-- ❌ 错误：Markdown mermaid 代码块不会自动转白板 -->
   ```mermaid
   timeline
       title 三阶段路线
   ```
   ```
   
   ```text
   <!-- ❌ 错误：ASCII 字符画不是图表 -->
   阶段一 ─── 阶段二 ─── 阶段三
   ```
   
   支持的 mermaid 类型：flowchart, pie, gantt, timeline, mindmap。不支持 radar-beta, quadrantChart, sankey-beta, block-beta, architecture-beta。图表渲染 → ffeishu 工作流 G（图子文档约定）。

## 飞书操作委派规则

| 操作 | 执行者 | 命令/工具 |
|------|--------|----------|
| 创建 wiki doc | ffeishu skill（先调 Skill） | `lark-cli docs +create` |
| 更新 wiki doc | ffeishu skill（先调 Skill） | `lark-cli docs +update --command str_replace` |
| 创建 Base/表 | fmoocrec 直接 | `lark-cli base +base-create` |
| 写进度记录 | fmoocrec 直接 | `lark-cli base +record-batch-create` |
| 读进度记录 | fmoocrec 直接 | `lark-cli base +record-list --format json` |
| 课程查询 | fmoocrec 直接 | Supabase API 或 `mcp__supabase__execute_sql` |
| 课程搜索/更新 | fmoocrec 直接 | Tavily/WebSearch |

**关键**: 写飞书 doc 前必须先调 `ffeishu` Skill（全局飞书规则硬前置条件）。Base 操作不需要。

## 常见陷阱

| ❌ 错误 | ✅ 正确 |
|---------|--------|
| `lark-cli docs +create --markdown` | `--doc-format markdown --content -` |
| `--folder-token` 用于 wiki | `--parent-token` + wiki node token |
| 不调 ffeishu 直接裸调 lark-cli docs | 先 `Skill("ffeishu")` 再执行 lark-cli |
| Supabase REST API 直连 | 用管理 API (`api.supabase.com`) + access token |
| stderr 被当作错误 | lark-cli 日志行在 stdout，WSL 注入行需过滤 |
| `--content` 中换行符直接写 | 用 heredoc `cat << 'EOF' \| lark-cli ...` |
| 图表用 ASCII 字符画或 Markdown mermaid 代码块 | 用 `<whiteboard type="mermaid">` XML 语法 |
| str_replace 用默认 XML 格式匹配 URL | 用 `--doc-format markdown`（XML 下 URL 包在 `<a href>` 中无法匹配） |
| MIT 课程用 bit.ly 短链接 | 用 Supabase 中的 edX 完整 URL |
| 课程 URL 有空格（如 `MITxT 7.00x`） | 用 `+` 连接（`MITxT+7.00x`） |
| `--content @/tmp/file` 绝对路径 | 必须相对路径：`--content @./file` 或 heredoc |

## 课程数据库维护

### 查询 Supabase

```bash
# 管理 API（推荐，因为 service_role key 不在本地）
curl -s "https://api.supabase.com/v1/projects/<your-supabase-project-id>/database/query" \
  -H "Authorization: Bearer <your-supabase-access-token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM courses WHERE stage='\''core'\'' ORDER BY id;"}'
```

### 添加新课程

```sql
INSERT INTO courses (...) VALUES (...);
```

### 刷新课程状态

```sql
UPDATE courses SET is_active = true, last_verified_date = CURRENT_DATE WHERE url LIKE '%edx.org%';
```

## 参考文件

- `references/bio-curriculum.md` — 完整课程体系 + 先修关系图
- `references/certificate-guide.md` — 证书获取、验证、LinkedIn 挂载
- `references/platform-guide.md` — 平台定价、免费策略、语言支持对比
- `scripts/bio-progress.py` — Base 进度读写 Python 工具