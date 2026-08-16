# -*- coding: utf-8 -*-
"""核查 TriggerStrings 的 3 类异常来源:官方原样 vs 本次引入。"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
W = os.path.dirname(os.path.abspath(__file__))
ED = r'D:\StarCraft II\Editor\LocalizedData'
TRG = os.path.join(ED, 'TriggerStrings.txt')


def load(p, want_lines=False):
    with open(p, 'r', encoding='utf-8-sig', errors='replace') as f:
        lines = f.read().replace('\r\n', '\n').split('\n')
    if want_lines:
        return lines
    kv = {}
    for ln in lines:
        if ln.strip() and '=' in ln and not ln.lstrip().startswith('//'):
            k, v = ln.split('=', 1)
            kv[k] = v
    return kv


cur = load(TRG)
off = load(os.path.join(W, '_casc_zh_triggerstrings.txt'))
baks = sorted(f for f in os.listdir(ED) if f.startswith('TriggerStrings.txt.bak'))
old = load(os.path.join(ED, baks[-1])) if baks else {}
print(f'当前 {len(cur):,}  官方 {len(off):,}  上一版 {len(old):,}  (bak={baks[-1] if baks else "无"})')

print('\n[1] ~ 不成对:')
for k, v in cur.items():
    if v.count('~') % 2:
        src = '官方原样' if off.get(k) == v else ('旧版原样' if old.get(k) == v else '★本次引入')
        print(f'  {src}  {k}')
        print(f'        当前={v[:90]}')
        if off.get(k) and off[k] != v:
            print(f'        官方={off[k][:90]}')

print('\n[2] 空值:')
for k, v in cur.items():
    if not v.partition(' //')[0].strip():
        src = '官方原样' if off.get(k) == v else ('旧版原样' if old.get(k) == v else '★本次引入')
        print(f'  {src}  {k}={v!r}   官方={off.get(k, "<无>")!r}')

print('\n[3] 无等号行(前 12 行 + 分类):')
lines = load(TRG, want_lines=True)
bad = [ln for ln in lines if ln.strip() and '=' not in ln and not ln.lstrip().startswith('//')]
print(f'  共 {len(bad)} 行')
for ln in bad[:12]:
    print(f'    {ln[:100]!r}')
oldlines = load(os.path.join(ED, baks[-1]), want_lines=True) if baks else []
oldbad = [ln for ln in oldlines if ln.strip() and '=' not in ln and not ln.lstrip().startswith('//')]
print(f'  上一版同类行 {len(oldbad)} 行 -> {"全部沿袭,非本次引入" if len(oldbad) >= len(bad) else "★本次新增"}')
