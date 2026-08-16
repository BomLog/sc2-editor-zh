# -*- coding: utf-8 -*-
"""对比本地部署文件 vs 官方 zhCN 基底:确认本地是否在"覆盖并劣化"官方汉化。"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
CJK = re.compile(r'[一-鿿]')
W = os.path.dirname(os.path.abspath(__file__))
ED = r'D:\StarCraft II\Editor\LocalizedData'

def load(p):
    kv = {}
    if not os.path.isfile(p):
        return kv
    with open(p, 'r', encoding='utf-8-sig', errors='replace') as f:
        for ln in f:
            ln = ln.rstrip('\r\n')
            if ln.strip() and '=' in ln and not ln.lstrip().startswith('//'):
                k, v = ln.split('=', 1)
                kv[k] = v
    return kv

for local_name, off_name in (('TriggerStrings.txt', '_casc_zh_triggerstrings.txt'),
                             ('GameStrings.txt',    '_casc_zh_gamestrings.txt'),
                             ('111GameStrings.txt', '_casc_zh_gamestrings.txt')):
    L = load(os.path.join(ED, local_name))
    O = load(os.path.join(W, off_name))
    if not L:
        print(f'--- {local_name}: 不存在,跳过'); continue
    lz = sum(1 for v in L.values() if CJK.search(v))
    # 官方有中文、本地也有该键但本地是英文 => 本地覆盖导致汉化丢失
    lost = [k for k, v in O.items()
            if CJK.search(v) and k in L and not CJK.search(L[k])]
    # 官方有中文、本地根本没这个键 => 若整文件替换,这条也丢
    missing = [k for k, v in O.items() if CJK.search(v) and k not in L]
    extra = [k for k in L if k not in O]
    print(f'--- {local_name}  本地 {len(L):,} 键 / {lz:,} 中文    官方基底 {len(O):,} 键')
    print(f'    同键但本地退化为英文 : {len(lost):,}')
    print(f'    官方有中文本地无此键 : {len(missing):,}')
    print(f'    本地独有(官方没有)  : {len(extra):,}')
    for k in lost[:6]:
        print(f'      退化 {k}\n            官方={O[k]}\n            本地={L[k]}')
    for k in missing[:4]:
        print(f'      缺失 {k}={O[k]}')
