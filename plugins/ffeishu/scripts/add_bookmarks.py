#!/usr/bin/env python3
"""给合成 PDF 加书签（outline）+ 元数据"""
import json, re, fitz, os

T = os.environ.get('BUILD_DIR', './pdfbuild')
BOOK = os.environ.get('BOOK_TITLE', '文档合订本')
PDF = os.path.join(T, BOOK + '.pdf')
docs = json.load(open(os.path.join(T, 'docs.json'), encoding='utf-8'))
sec = json.load(open(os.path.join(T, 'secpages.json'), encoding='utf-8'))


CN = {'week4-chevron-refineries': 'Chevron 炼油厂生产计划优化', 'week4-zara': 'Zara 全球配送网络重构', 'week5-kroger': 'Kroger 药房库存仿真优化', 'week5-intel': 'Intel 资本投资决策优化', 'week6-internal-markets': 'JR Keller：内部市场与人力配置', 'week6-paying-more': 'Matthew Bidwell：外招与内部流动', 'week8-phytopharm': 'Phytopharm 研发估值与许可谈判', 'week8-polio': '脊灰根除与集成分析模型', 'week8-bank-one': 'Bank One 信用卡额度与定价管理'}


WEEKS = {1: '描述性分析：获取洞察', 2: '描述性分析：描述与预测未来事件', 3: '预测分析：用数据做预测', 4: '预测与规范性分析：应用与工具箱', 5: '预测分析：决策工具', 6: '预测分析：预测员工绩效', 7: '规范性分析：提供改变行为的建议', 8: '规范性分析：确定最优结果', 9: '商业分析综合应用'}


def pretty(t):
    m = re.match(r'wharton-business-analytics-week(\d+)-update$', t)
    if m:
        w = int(m.group(1))
        return f'Week {w}　{WEEKS.get(w, "")}'.rstrip('　')
    m = re.match(r'wharton-business-analytics-(.+)-update$', t)
    if m and m.group(1) in CN:
        return CN[m.group(1)]
    return t


# slug 顺序 = docs 顺序
order = [d['title'] for d in docs]
slug = {t: f'sec{i+1}' for i, t in enumerate(order)}

GROUPS = [
    ('导航与总览', lambda t: t == 'Wharton BADTI refresh' or t.startswith('BADTI ')),
    ('课程单元', lambda t: re.match(r'wharton-business-analytics-week\d+-update$', t)),
    ('案例精读', lambda t: not t.startswith('BADTI ') and t != 'Wharton BADTI refresh'
     and not re.match(r'wharton-business-analytics-week\d+-update$', t)),
]

d = fitz.open(PDF)
toc = [[1, '封面', 1], [1, '目录', 2]]
for gname, pred in GROUPS:
    items = [t for t in order if pred(t)]
    if not items:
        continue
    first = sec.get(slug[items[0]], 1)
    toc.append([1, gname, first])
    for t in items:
        toc.append([2, pretty(t), sec.get(slug[t], first)])

d.set_toc(toc)
d.set_metadata({
    'title': BOOK,
    'author': 'Wharton / Emeritus（中文精读 + 2024—2026 演进）',
    'subject': '商业分析课程复习材料：3 篇总览 + 9 篇单元 + 9 篇案例',
    'keywords': '商业分析, 描述性分析, 预测性分析, 规范性分析, Wharton, 复习',
    'creator': 'ffeishu / lark-cli',
})
out = os.path.join(T, BOOK + '.final.pdf')
d.save(out, garbage=3, deflate=True)
d.close()
print('bookmarks:', len(toc), '| saved', out, os.path.getsize(out) // 1024, 'KB')