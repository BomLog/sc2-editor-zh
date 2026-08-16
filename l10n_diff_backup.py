# -*- coding: utf-8 -*-
"""对比当前 ObjectStrings.txt 与各备份,查是否丢失条目"""
import os, re, sys, glob, collections
sys.stdout.reconfigure(encoding='utf-8')

D = r"D:\StarCraft II\Editor\LocalizedData"
CUR = os.path.join(D, "ObjectStrings.txt")
CJK = re.compile(r'[\u4e00-\u9fff]')

def load(p):
    txt = open(p, 'rb').read().decode('utf-8-sig', 'replace')
    d = {}
    for ln in txt.replace('\r\n', '\n').split('\n'):
        if ln.strip() and '=' in ln:
            k, v = ln.split('=', 1)
            d[k] = v
    return d

files = [CUR] + sorted(glob.glob(os.path.join(D, "ObjectStrings*.bak*"))) \
              + sorted(glob.glob(os.path.join(D, "ObjectStrings_backup*")))

print(f'{"文件":48s} {"字节":>12s} {"键数":>8s} {"含中文":>8s}')
data = {}
for f in files:
    d = load(f)
    zh = sum(1 for v in d.values() if CJK.search(v))
    data[f] = d
    print(f'{os.path.basename(f):48s} {os.path.getsize(f):12,d} {len(d):8,d} {zh:8,d}')

cur = data[CUR]
big = max((f for f in files if f != CUR), key=lambda f: len(data[f]))
print()
print(f'=== 当前 vs 最大备份 {os.path.basename(big)} ===')
b = data[big]
lost = set(b) - set(cur)
gain = set(cur) - set(b)
lost_zh = {k for k in lost if CJK.search(b[k])}
print(f'  当前独有(新增): {len(gain):,}')
print(f'  备份独有(丢失): {len(lost):,}   其中已汉化的: {len(lost_zh):,}')

c = collections.Counter(k.split('/', 1)[0] for k in lost_zh)
print('  丢失的已汉化条目按分类:')
for cat, n in c.most_common(30):
    print(f'    {cat:24s} {n:6,d}')
print('  样例:')
for k in list(lost_zh)[:15]:
    print(f'    {k} = {b[k]}')

chg = [(k, b[k], cur[k]) for k in (set(b) & set(cur)) if b[k] != cur[k]]
print(f'\n  两边都有但值不同: {len(chg):,}')
for k, o, n in chg[:10]:
    print(f'    {k}\n      备份: {o}\n      当前: {n}')
