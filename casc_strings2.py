# -*- coding: utf-8 -*-
"""聚焦核心 mod:官方把数据对象名放在 ObjectStrings 还是 GameStrings?
   并导出官方 zhCN 译文(对象名 + 触发器)供合并。"""
import os, re, sys, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dds_viewer'))
sys.stdout.reconfigure(encoding='utf-8')
import casc_reader as CR

CJK = re.compile(r'[一-鿿]')
OUT = os.path.dirname(os.path.abspath(__file__))
OBJPREF = ('Actor', 'Model', 'Effect', 'Unit', 'Abil', 'Behavior', 'Validator',
           'Requirement', 'Button', 'Sound', 'Weapon', 'Upgrade', 'Mover',
           'Turret', 'Footprint', 'Light', 'Accumulator', 'DataCollection')

c = CR.Casc(); c.open(CR.find_game_dir())
paths = c.list_paths(('strings.txt',))

# 只要主 mod(不含 .sc2map/战役地图),且是 zhcn 或 enus
MAIN = ('mods\\core.sc2mod', 'mods\\liberty.sc2mod', 'mods\\swarm.sc2mod',
        'mods\\void.sc2mod', 'mods\\libertymulti.sc2mod', 'mods\\voidmulti.sc2mod',
        'mods\\starcoop', 'mods\\novastoryassets', 'campaigns\\liberty.sc2campaign\\base.sc2data',
        'campaigns\\swarm.sc2campaign\\base.sc2data', 'campaigns\\void.sc2campaign\\base.sc2data')

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

sel = [p for p in paths
       if any(p.startswith(m) for m in MAIN)
       and ('zhcn' in p or 'enus' in p)
       and p.rsplit('\\', 1)[-1] in ('objectstrings.txt', 'gamestrings.txt')]
print(f'主 mod 目标文件 {len(sel)} 个\n')
print(f'{"文件":72s} {"键":>7s} {"中文":>7s} {"对象名键":>8s}')
tot = collections.Counter()
for p in sorted(sel):
    kv = read_kv(p)
    if kv is None:
        print(f'{p:72s}  [读取失败]')
        continue
    zh = sum(1 for v in kv.values() if CJK.search(v))
    obj = sum(1 for k in kv if k.split('/')[0] in OBJPREF)
    short = p.replace('\\base.sc2data', '').replace('.sc2data', '').replace('localizeddata\\', '')
    print(f'{short:72s} {len(kv):7,d} {zh:7,d} {obj:8,d}')
    tag = ('obj' if p.endswith('objectstrings.txt') else 'game') + ('/zh' if 'zhcn' in p else '/en')
    tot[tag + ' 键'] += len(kv); tot[tag + ' 对象名'] += obj; tot[tag + ' 中文'] += zh

print('\n汇总:')
for k in sorted(tot):
    print(f'  {k:16s} {tot[k]:,}')
c.close()
