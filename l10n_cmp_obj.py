# -*- coding: utf-8 -*-
"""本地 ObjectStrings vs 官方 zhCN objectstrings:键格式是否对得上 / 官方中文分布。"""
import os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
CJK = re.compile(r'[一-鿿]')
W = os.path.dirname(os.path.abspath(__file__))

def load(p):
    kv = {}
    with open(p, 'r', encoding='utf-8-sig', errors='replace') as f:
        for ln in f:
            ln = ln.rstrip('\r\n')
            if ln.strip() and '=' in ln and not ln.lstrip().startswith('//'):
                k, v = ln.split('=', 1)
                kv[k] = v
    return kv

L = load(r'D:\StarCraft II\Editor\LocalizedData\ObjectStrings.txt')
O = load(os.path.join(W, '_casc_zh_objectstrings.txt'))
G = load(os.path.join(W, '_casc_zh_gamestrings.txt'))
print(f'本地 ObjectStrings {len(L):,} 键   官方 objectstrings {len(O):,} 键   官方 gamestrings {len(G):,} 键')

inter = set(L) & set(O)
print(f'\n本地∩官方objectstrings = {len(inter):,}  ({len(inter)*100.0/len(O):.1f}% 的官方键被本地覆盖)')
lost = [k for k in inter if CJK.search(O[k]) and not CJK.search(L[k])]
gain = [k for k in inter if not CJK.search(O[k]) and CJK.search(L[k])]
print(f'  其中本地退化(官中→本英): {len(lost):,}    本地新增汉化(官英→本中): {len(gain):,}')
for k in lost[:5]:
    print(f'    退化 {k}  官方={O[k]}  本地={L[k]}')

# 官方 objectstrings 的中文分布
zk = [k for k, v in O.items() if CJK.search(v)]
print(f'\n官方 objectstrings 含中文 {len(zk):,},前缀分布:')
for k, n in collections.Counter(x.split('/')[0] for x in zk).most_common(12):
    print(f'    {k:<18} {n:6,d}')

# gamestrings 里的对象名键(2/3段式 Cat/Name/ID)
objlike = re.compile(r'^[A-Za-z]+/(Name|EditorName|Tooltip)/')
gobj = {k: v for k, v in G.items() if objlike.match(k)}
gz = sum(1 for v in gobj.values() if CJK.search(v))
print(f'\n官方 gamestrings 里的对象名键 {len(gobj):,} / 含中文 {gz:,}')
inter2 = set(L) & set(gobj)
lost2 = [k for k in inter2 if CJK.search(gobj[k]) and not CJK.search(L[k])]
print(f'  本地∩ = {len(inter2):,}   其中本地退化 = {len(lost2):,}')
for k in lost2[:5]:
    print(f'    退化 {k}  官方={gobj[k]}  本地={L[k]}')

# 三方都没有中文的对象名键 = 真正的"未命名"来源
allkeys = set(O) | set(gobj)
nozh = [k for k in allkeys
        if not CJK.search(O.get(k, '')) and not CJK.search(gobj.get(k, ''))
        and not CJK.search(L.get(k, ''))]
print(f'\n官方+本地三方均无中文的对象名键: {len(nozh):,}')
for k, n in collections.Counter(x.split('/')[0] for x in nozh).most_common(10):
    print(f'    {k:<18} {n:6,d}')
