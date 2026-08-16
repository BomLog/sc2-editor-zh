# -*- coding: utf-8 -*-
"""全量扫描 Editor 下所有字符串文件的解析器致命缺陷。
   重点:IDA 已确认加载的 3 个 Editor*.txt + 109 个 *Hints.txt。"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
CJK = re.compile(r'[一-鿿]')
ROOT = r'D:\StarCraft II\Editor'
CONFIRMED = {'editorstrings.txt', 'editorcatalogstrings.txt', 'editorcategorystrings.txt'}

rows = []
for dirpath, _, files in os.walk(ROOT):
    for fn in files:
        low = fn.lower()
        if not low.endswith('.txt') or '.bak' in low:
            continue
        p = os.path.join(dirpath, fn)
        try:
            raw = open(p, 'rb').read()
        except Exception:
            continue
        txt = raw.decode('utf-8-sig', 'replace')
        bare = dup = empty = tilde = keys = 0
        seen = set()
        for ln in txt.replace('\r\n', '\n').split('\n'):
            if not ln.strip() or ln.lstrip().startswith('//'):
                continue
            if '=' not in ln:
                bare += 1; continue
            k, v = ln.split('=', 1)
            keys += 1
            if k in seen:
                dup += 1
            seen.add(k)
            if not v.partition(' //')[0].strip():
                empty += 1
            if v.count('~') % 2:
                tilde += 1
        kind = ('★确认加载' if low in CONFIRMED
                else ('☆Hints(确认加载)' if low.endswith('hints.txt') else '  其它'))
        if bare or dup or empty or tilde:
            rows.append((kind, os.path.relpath(p, ROOT), keys, bare, dup, empty, tilde))

if not rows:
    print('全部干净:无裸行 / 无重复键 / 无空值 / 无 ~ 不成对')
else:
    print(f'{"类别":<18}{"文件":<46}{"键":>8}{"裸行":>6}{"重复":>6}{"空值":>6}{"~":>5}')
    for r in sorted(rows, key=lambda x: (x[0], -x[3])):
        print(f'{r[0]:<18}{r[1][:44]:<46}{r[2]:>8,}{r[3]:>6}{r[4]:>6}{r[5]:>6}{r[6]:>5}')
    print(f'\n有缺陷文件 {len(rows)} 个,裸行合计 {sum(r[3] for r in rows):,}  '
          f'重复 {sum(r[4] for r in rows):,}  空值 {sum(r[5] for r in rows):,}  '
          f'~不成对 {sum(r[6] for r in rows):,}')
