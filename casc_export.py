# -*- coding: utf-8 -*-
"""导出官方 zhCN 基底:gamestrings / triggerstrings / objectstrings 全 mod 合并。
   后加载的 mod 覆盖先加载的(按路径深度+名称排序近似加载序)。"""
import os, re, sys, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dds_viewer'))
sys.stdout.reconfigure(encoding='utf-8')
import casc_reader as CR

CJK = re.compile(r'[一-鿿]')
OUT = os.path.dirname(os.path.abspath(__file__))
c = CR.Casc(); c.open(CR.find_game_dir())
paths = c.list_paths(('strings.txt',))

def read_kv(p):
    try:
        txt = c.read(p).decode('utf-8-sig', 'replace')
    except Exception:
        return None
    kv = {}
    for ln in txt.replace('\r\n', '\n').split('\n'):
        if ln.strip() and '=' in ln and not ln.lstrip().startswith('//'):
            k, v = ln.split('=', 1)
            kv[k] = v
    return kv

# 排除单张地图(.sc2map),只要 mod / campaign 级
def is_mod_level(p):
    return '.sc2map\\' not in p

for kind in ('gamestrings.txt', 'triggerstrings.txt', 'objectstrings.txt'):
    sel = sorted(p for p in paths
                 if p.endswith(kind) and 'zhcn' in p and is_mod_level(p))
    merged, srcs, fail = {}, 0, 0
    for p in sel:
        kv = read_kv(p)
        if kv is None:
            fail += 1
            continue
        srcs += 1
        merged.update(kv)
    zh = sum(1 for v in merged.values() if CJK.search(v))
    pref = collections.Counter(k.split('/')[0] for k in merged)
    out = os.path.join(OUT, '_casc_zh_' + kind.replace('.txt', '') + '.txt')
    with open(out, 'w', encoding='utf-8') as f:
        for k, v in sorted(merged.items()):
            f.write(f'{k}={v}\n')
    print(f'{kind:20s} 源 {len(sel):4d}(成功 {srcs}, 失败 {fail})  '
          f'合并键 {len(merged):7,d}  含中文 {zh:7,d} ({zh*100.0/max(1,len(merged)):5.1f}%)')
    print(f'{"":20s} 前缀 Top10: ' + ', '.join(f'{k}={n}' for k, n in pref.most_common(10)))
    print(f'{"":20s} -> {os.path.basename(out)}')
c.close()
