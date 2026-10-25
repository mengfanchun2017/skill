#!/usr/bin/env python3
"""扫描 PDF 里的 secN 标记，输出章节起始页 -> secpages.json"""
import json, os, re, fitz
T = os.environ.get('BUILD_DIR', './pdfbuild')
BOOK = os.environ.get('BOOK_TITLE', '文档合订本')
d = fitz.open(os.path.join(T, BOOK + '.pdf'))
pages = {}
for i in range(d.page_count):
    for m in re.finditer(r'sec\d+', d[i].get_text()):
        pages.setdefault(m.group(0), i + 1)
json.dump(pages, open(os.path.join(T, 'secpages.json'), 'w'))
print('pages', d.page_count, 'located', len(pages))
