#!/bin/bash
# 把一个 wiki 节点及其全部子文档导出为一本带目录/书签的 PDF
#
# 用法:
#   bash export_whole_tree_pdf.sh <root_wiki_node_token> <root_obj_token> <输出目录> "<书名>" ["总览标题前缀 ..."]
#
# 例:
#   bash export_whole_tree_pdf.sh BiMZwuUpeih5o6ky8QfceiDUn9d PbAkd0EF4o42CZx2FV2cbejCnwh \
#        /tmp/pdfbuild "Wharton商业分析复习课程" "BADTI "
#
# 依赖: lark-cli（已 auth）、python3 + pymupdf、node + playwright-core + chromium
# 产出: <输出目录>/<书名>.pdf（含封面、目录+页码、章节标签、画板图、书签）
#
# 流程: 抓内容 → 导画板图 → DocxXML→HTML → chromium 打印 → 回填页码 → 加书签
set -euo pipefail

ROOT_NODE="${1:?root wiki node token}"
ROOT_OBJ="${2:?root obj token}"
OUT="${3:?output dir}"
BOOK="${4:?book title}"
OVERVIEW_PREFIX="${5:-}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPACE="${LARK_SPACE_ID:-7626581506382728129}"
export PATH="$HOME/.local/bin:$PATH"
export LARKSUITE_CLI_CONFIG_DIR="${LARKSUITE_CLI_CONFIG_DIR:-$HOME/.lark-cli-ailab}"
CHROME="${PW_CHROME:-$HOME/.local/state/pw-chromium/chrome}"
NODE_MODULES="${PW_NODE_MODULES:-}"

mkdir -p "$OUT/boards"

# ---- 1. 抓取内容 + 画板图 ----
cat > "$OUT/_grab.py" <<'PY'
import json, os, re, subprocess, sys
ROOT_NODE, ROOT_OBJ, OUT, PREFIX = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
SPACE = os.environ.get('LARK_SPACE_ID', '7626581506382728129')

def run(a):
    r = subprocess.run(a, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return '\n'.join(l for l in r.stdout.split('\n') if not l.startswith('[lark-cli]'))

def node_list(p):
    return json.loads(run(['lark-cli','wiki','+node-list','--space-id',SPACE,
                           '--parent-node-token',p,'--as','user','--page-size','50']))['data'].get('nodes') or []

def fetch(o):
    return json.loads(run(['lark-cli','docs','+fetch','--api-version','v2','--doc',o,
                           '--as','user','--detail','full']))['data']['document']['content']

nodes = {n['title']: n for n in node_list(ROOT_NODE)}
# 排序：总览前缀在前，其余按标题（week 顺序自然排）
def key(t):
    m = re.match(r'.*week(\d+)-update$', t)
    return (0, '') if t.startswith(PREFIX) else (1, int(m.group(1)) if m else 99, t)
titles = sorted(nodes, key=key)

docs = [{'title': 'ROOT', 'kind': 'root', 'content': fetch(ROOT_OBJ)}]
for t in titles:
    n = nodes[t]
    docs.append({'title': t, 'content': fetch(n['obj_token']),
                 'node': n['node_token'], 'obj': n['obj_token']})

btoks = [m.group(1) for d in docs for m in re.finditer(r'<whiteboard[^>]*token="([^"]+)"', d['content'])]
ok = 0
for tok in btoks:
    p = os.path.join(OUT, 'boards', tok + '.jpg')
    if not (os.path.exists(p) and os.path.getsize(p) > 2000):
        run(['lark-cli','whiteboard','+export','--whiteboard-token',tok,
             '--output-type','preview','--output',p,'--as','user'])
    if os.path.exists(p) and os.path.getsize(p) > 2000: ok += 1

json.dump(docs, open(os.path.join(OUT, 'docs.json'), 'w'), ensure_ascii=False)
# 锚点映射（供 PDF 内部链接）
anchors = {d.get('node'): d['title'] for d in docs if d.get('node')}
json.dump(anchors, open(os.path.join(OUT, 'anchors.json'), 'w'), ensure_ascii=False)
print(f'docs={len(docs)} boards={ok}/{len(btoks)}')
PY
LARK_SPACE_ID="$SPACE" LARKSUITE_CLI_CONFIG_DIR="$LARKSUITE_CLI_CONFIG_DIR" PATH="$PATH" \
  python3 "$OUT/_grab.py" "$ROOT_NODE" "$ROOT_OBJ" "$OUT" "$OVERVIEW_PREFIX"

# ---- 2. DocxXML -> HTML ----
BUILD_DIR="$OUT" BOOK_TITLE="$BOOK" python3 "$HERE/docxxml2html.py"

# ---- 3..5. 打印 PDF → 收敛页码 → 加书签（迭代 2 轮足够：加页码会轻微改变分页）----
for i in 1 2; do
  BUILD_DIR="$OUT" BOOK_TITLE="$BOOK" CHROME="$CHROME" NODE_MODULES="$NODE_MODULES" \
    node "$HERE/html2pdf.js"
  BUILD_DIR="$OUT" BOOK_TITLE="$BOOK" python3 "$HERE/collect_pages.py" || true
done
BUILD_DIR="$OUT" BOOK_TITLE="$BOOK" python3 "$HERE/add_bookmarks.py"

echo "✅ $OUT/$BOOK.pdf"