# fpdf 执行流程（4 步，全部走 scripts/run.sh）

## 执行流程（4 步，全部走 `scripts/run.sh`）

### Step 0: 前置检查（自动，缺什么装什么）

**`run.sh` 会自动调 `setup.sh` 补齐**，通常不必手动跑。手动检查/安装时：

```bash
bash ~/.claude/skills/fpdf/scripts/setup.sh          # 检查 + 缺啥装啥（需 sudo 时提示）
bash ~/.claude/skills/fpdf/scripts/setup.sh --check  # 只检查不安装
```

检查 5 项：

| 依赖 | 缺失时怎么装 | 是否阻断 |
|------|-------------|---------|
| `uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | **阻断** |
| `lark-cli` | `npm i -g @larksuite/cli`，装入 PATH（或落 `~/.local/bin`） | **阻断** |
| 飞书授权 | `lark-cli auth login`（走扫码，一次性） | **阻断** |
| MinerU token | https://mineru.net → API 管理 → 建 token；填法：`fcore conf set mineru.token <token>`（落 `~/.claude/skill-config/fpdf.yaml`，升级不覆盖） | **阻断**（默认 precision 档） |
| `poppler-utils` | 自动按平台装（apt / brew / dnf / pacman / apk）；装不上**只提示不阻断** | 不阻断 |

> **token 口径**：`run.sh` 默认走 precision 档（排版必需），缺 token 时 `parse.py` 直接
> `exit 3`。所以 MinerU token 标为**阻断**——不是"能跑 flash 档"就算过。
> 真要跑纯文本降级版，得显式 `--tier flash`。
>
> **cccconfig 用户**：上面两条（lark-cli / MinerU token）在 ccconfig 环境里有一键命令
> `bash ~/git/ccconfig/init-option.sh larkcli` 和 `... mineru key`，可用可不用；
> 独立用户直接用 `npm i -g` / 网页建 token 即可，不依赖 ccconfig。

**为什么 poppler 不阻断**：解析/渲染主路径走 pymupdf（`parse.py` 内用），poppler 只在需要
`pdftotext`/`pdfimages`/`pdftoppm` 这类命令行快速抽取时用得上；装不上不影响主流程。
无 TTY 的自动会话里 `sudo` 会挂，故 setup.sh 先判 `sudo -n` 再决定装还是提示。

> **飞书授权口径**：唯一可信信号是 `lark-cli auth status` 的 `identities.user.available`。
> `config.json` 里的 `users[]` 是「登录过」的记录，token 过期仍残留 → 拿它判断会假阳性。

### Step 1-4: 跑编排器

```bash
# 默认：只落飞书
bash ~/.claude/skills/fpdf/scripts/run.sh "<pdf路径>"

# 加 Word 导出
bash ~/.claude/skills/fpdf/scripts/run.sh "<pdf路径>" --word

# 加译文版
bash ~/.claude/skills/fpdf/scripts/run.sh "<pdf路径>" --trans

# 指定标题 / 父文档 / 工作目录
bash ~/.claude/skills/fpdf/scripts/run.sh "<pdf路径>" \
  --title "文档标题" --parent "<wiki节点token>" --word
```

`run.sh` 四阶段：**解析**（MinerU Precision）→ **渲染**（DocxXML）→ **上传飞书** → **可选 Word 导出**。
最后一行 stdout 是 JSON（`doc_url` / `trans_doc_url` / `word_path`），其余进度到 stderr。

### Step 5: 向用户输出

**必须**给出完整飞书链接（markdown 格式，独占一行）：

```
[文档标题](https://<tenant>.feishu.cn/docx/<token>)
```

Word 导出路径、译文文档链接一并给出。多链接用列表。

## 父文档（所有输出落在此处）