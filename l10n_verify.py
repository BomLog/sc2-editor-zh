# -*- coding: utf-8 -*-
"""落盘后独立复核:格式合法性 / 重复键 / 空值 / 占位符完整 / 汉化率。"""
import os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
CJK = re.compile(r'[一-鿿]')
ED = r'D:\StarCraft II\Editor\LocalizedData'
PH = re.compile(r'~[^~]*~|%\d+')

for name in ('ObjectStrings.txt', 'GameStrings.txt', 'TriggerStrings.txt',
             'Errors.txt'):
    p = os.path.join(ED, name)
    if not os.path.isfile(p):
        print(f'{name}: 不存在'); continue
    raw = open(p, 'rb').read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    txt = raw.decode('utf-8-sig', 'replace')
    crlf = txt.count('\r\n')
    lines = txt.replace('\r\n', '\n').split('\n')
    kv, dup, empty, badfmt, cmt, blank = {}, 0, 0, 0, 0, 0
    for ln in lines:
        if not ln.strip():
            blank += 1; continue
        if ln.lstrip().startswith('//'):
            cmt += 1; continue
        if '=' not in ln:
            badfmt += 1; continue
        k, v = ln.split('=', 1)
        if k in kv:
            dup += 1; continue
        vis = v.partition(' //')[0]
        if not vis.strip():
            empty += 1
        kv[k] = v
    zh = sum(1 for v in kv.values() if CJK.search(v.partition(' //')[0]))
    # 占位符对称性(~xxx~ 必须成对)
    ph_bad = [k for k, v in kv.items() if v.count('~') % 2]
    print(f'{name}')
    print(f'  {len(raw):>12,} B  BOM={"有" if bom else "无"}  CRLF={crlf:,}  '
          f'行 {len(lines):,}(空 {blank:,} 注释 {cmt:,})')
    print(f'  键 {len(kv):,}  中文 {zh:,} ({zh*100.0/max(1,len(kv)):.1f}%)  '
          f'重复 {dup}  空值 {empty}  无等号 {badfmt}  ~不成对 {len(ph_bad)}')
    if ph_bad[:3]:
        for k in ph_bad[:3]:
            print(f'    ~异常 {k}={kv[k][:70]}')
    print()
