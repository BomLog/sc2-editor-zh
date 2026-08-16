# -*- coding: utf-8 -*-
"""细查 EditorCatalogStrings.txt 的格式错/空值/额外= 三类问题"""
import re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')

CAT = r"D:\StarCraft II\Editor\EditorCatalogStrings.txt"
raw = open(CAT, 'rb').read()
txt = raw.decode('utf-8-sig')
lines = txt.replace('\r\n', '\n').split('\n')
if lines and lines[-1] == '':
    lines.pop()

print('### 1) 格式错行(无=)上下文')
for i, ln in enumerate(lines, 1):
    if ln.strip() and '=' not in ln:
        for j in range(max(1, i - 3), min(len(lines), i + 3) + 1):
            mark = '>>>' if j == i else '   '
            print(f'{mark} L{j}: {lines[j-1]!r}')
        print('   ' + '-' * 50)

print()
print('### 2) 值含额外=的行(40条)')
n = 0
for i, ln in enumerate(lines, 1):
    if '=' not in ln:
        continue
    k, v = ln.split('=', 1)
    if '=' in v:
        n += 1
        if n <= 40:
            print(f'  L{i}: {k} = {v}')
print(f'  合计 {n}')

print()
print('### 3) 空值行按前缀分布')
c = collections.Counter()
empties = []
for i, ln in enumerate(lines, 1):
    if ln.endswith('=') and ln.count('=') == 1:
        k = ln[:-1]
        m = re.match(r'(EDSTR_[A-Z]+)_', k)
        c[m.group(1) if m else '(other)'] += 1
        empties.append((i, k))
for p, n in c.most_common():
    print(f'  {p:35s} {n}')
print('  样例:', ', '.join(k for _, k in empties[:3]))

print()
print('### 4) OB Custom Additions 段落(L19883起)')
for j in range(19878, min(len(lines), 19900)):
    print(f'  L{j+1}: {lines[j]}')

print()
print('### 5) CValidator ENTRYTYPE 统计')
val = [ln for ln in lines if ln.startswith('EDSTR_ENTRYTYPE_CValidator')]
print(f'  CValidator* 条目数: {len(val)}')
zh = sum(1 for ln in val if re.search(r'[\u4e00-\u9fff]', ln.split('=', 1)[1]))
print(f'  其中值含中文: {zh}')
for ln in val[:8]:
    print(f'    {ln}')
print('   ...')
for ln in val[-5:]:
    print(f'    {ln}')
