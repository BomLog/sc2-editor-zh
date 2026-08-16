# -*- coding: utf-8 -*-
"""细看 3 个确认加载文件的缺陷内容,判断该修还是该留。"""
import os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\StarCraft II\Editor'
CJK = re.compile(r'[一-鿿]')

for fn in ('EditorStrings.txt', 'EditorCategoryStrings.txt', 'EditorCatalogStrings.txt'):
    p = os.path.join(ROOT, fn)
    with open(p, 'r', encoding='utf-8-sig', errors='replace') as f:
        lines = f.read().replace('\r\n', '\n').split('\n')
    print(f'===== {fn}  ({len(lines):,} 行) =====')
    seen, bare, dup, empty, tl = {}, [], [], [], []
    for i, ln in enumerate(lines, 1):
        if not ln.strip() or ln.lstrip().startswith('//'):
            continue
        if '=' not in ln:
            bare.append((i, ln)); continue
        k, v = ln.split('=', 1)
        if k in seen:
            dup.append((i, k, seen[k], v))
        seen[k] = v
        if not v.partition(' //')[0].strip():
            empty.append((i, k))
        if v.count('~') % 2:
            tl.append((i, k, v))
    if bare:
        print(f'  裸行 {len(bare)}:')
        for i, ln in bare:
            print(f'    L{i}: {ln[:90]!r}')
    if dup:
        print(f'  重复键 {len(dup)}:')
        for i, k, a, b in dup[:6]:
            print(f'    L{i} {k}\n        先={a[:60]}\n        后={b[:60]}')
    if empty:
        print(f'  空值 {len(empty)}: ' + ', '.join(f'L{i}:{k}' for i, k in empty[:6]))
    if tl:
        print(f'  ~ 不成对 {len(tl)},样例:')
        for i, k, v in tl[:8]:
            print(f'    L{i} {k}={v[:80]}')
        # ~ 的用途分布
        c = collections.Counter()
        for _, _, v in tl:
            c[v.count('~')] += 1
        print(f'    ~ 个数分布: {dict(sorted(c.items()))}')
    print()
