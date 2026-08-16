# -*- coding: utf-8 -*-
"""探查 enUS 是否可读(本地是否下载了 enUS 数据),并按库前缀细分触发器覆盖率。"""
import os, re, sys, collections, ctypes
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dds_viewer'))
sys.stdout.reconfigure(encoding='utf-8')
import casc_reader as CR

CJK = re.compile(r'[一-鿿]')
W = os.path.dirname(os.path.abspath(__file__))
c = CR.Casc(); c.open(CR.find_game_dir())
paths = c.list_paths(('strings.txt',))

en = sorted(p for p in paths if p.endswith('triggerstrings.txt') and 'enus' in p)
zh = sorted(p for p in paths if p.endswith('triggerstrings.txt') and 'zhcn' in p)
print(f'索引中 enus triggerstrings {len(en)} 个 / zhcn {len(zh)} 个')
ok = 0
for p in en[:8]:
    try:
        d = c.read(p)
        ok += 1
        print(f'  [OK  {len(d):>8,}B] {p}')
    except Exception as e:
        print(f'  [FAIL {ctypes.get_last_error():>5}] {p}  ({e})')
print(f'前 8 个 enus 读取成功 {ok}/8')

# 试试其它 locale
for loc in ('enus', 'zhtw', 'kokr', 'dede', 'frfr', 'ruru', 'eses'):
    sel = [p for p in paths if p.endswith('gamestrings.txt') and loc in p]
    if not sel:
        continue
    try:
        c.read(sel[0]); r = 'OK'
    except Exception:
        r = 'FAIL'
    print(f'  locale {loc:6s} 索引 {len(sel):4d} 个,首个读取 {r}')
c.close()

# 库前缀细分
def load_kv(p):
    kv = {}
    with open(p, 'r', encoding='utf-8-sig', errors='replace') as f:
        for ln in f:
            ln = ln.rstrip('\r\n')
            if ln.strip() and '=' in ln and not ln.lstrip().startswith('//'):
                k, v = ln.split('=', 1)
                kv[k] = v
    return kv

O = load_kv(os.path.join(W, '_casc_zh_triggerstrings.txt'))
lib = re.compile(r'^FunctionDef/Name/lib_([A-Za-z0-9]+)_')
agg = collections.defaultdict(lambda: [0, 0])
for k, v in O.items():
    m = lib.match(k)
    if not m:
        continue
    a = agg[m.group(1)]
    a[1] += 1
    if CJK.search(v.partition(' //')[0]):
        a[0] += 1
print('\n官方 FunctionDef/Name 按库覆盖(Top20 按总量):')
for name, (z, t) in sorted(agg.items(), key=lambda x: -x[1][1])[:20]:
    print(f'    lib_{name:<12} {z:5,d}/{t:5,d}  {z*100.0/t:5.1f}%')
