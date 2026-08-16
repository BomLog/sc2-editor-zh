# -*- coding: utf-8 -*-
"""从 CASC 抽官方 zhCN 字符串文件:
   1) 确认官方把「数据对象名」(Actor/Name/...) 放在哪个文件 -> 定位正确落点
   2) 导出官方 TriggerStrings 译文供合并
"""
import os, re, sys, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dds_viewer'))
sys.stdout.reconfigure(encoding='utf-8')
import casc_reader as CR

CJK = re.compile(r'[一-鿿]')
OUT = os.path.dirname(os.path.abspath(__file__))

g = CR.find_game_dir()
print(f'游戏目录: {g}')
c = CR.Casc()
c.open(g)

paths = c.list_paths(('strings.txt',))
print(f'CASC 内 *strings.txt 共 {len(paths)} 个')

byname = collections.Counter(p.rsplit('\\', 1)[-1] for p in paths)
print('按文件名: ' + ', '.join(f'{k}={v}' for k, v in byname.most_common(12)))

zh = [p for p in paths if 'zhcn' in p or 'zhCN'.lower() in p]
print(f'\nzhCN 相关 {len(zh)} 个,样例:')
for p in zh[:12]:
    print(f'  {p}')

def analyze(p):
    try:
        raw = c.read(p)
    except Exception as e:
        return None
    txt = raw.decode('utf-8-sig', 'replace')
    kv = {}
    for ln in txt.replace('\r\n', '\n').split('\n'):
        if ln.strip() and '=' in ln and not ln.lstrip().startswith('//'):
            k, v = ln.split('=', 1)
            kv[k] = v
    n_zh = sum(1 for v in kv.values() if CJK.search(v))
    pref = collections.Counter(k.split('/')[0] for k in kv)
    return kv, n_zh, pref

print('\n' + '=' * 72)
print('各 zhCN 文件内容画像(重点看 Actor/Model/Effect 等对象名前缀出现在哪)')
for p in sorted(zh):
    r = analyze(p)
    if not r:
        print(f'  [读取失败] {p}')
        continue
    kv, n_zh, pref = r
    obj = sum(n for k, n in pref.items()
              if k in ('Actor', 'Model', 'Effect', 'Unit', 'Abil', 'Behavior',
                       'Validator', 'Requirement', 'Button', 'Sound', 'Weapon', 'Upgrade'))
    print(f'\n  {p}')
    print(f'    键 {len(kv):,}  含中文 {n_zh:,}  「数据对象名」类键 {obj:,}')
    print(f'    前缀 Top10: ' + ', '.join(f'{k}={n}' for k, n in pref.most_common(10)))

# 导出官方 TriggerStrings(所有 locale 里挑中文最多的那个)
best, bestn = None, -1
for p in paths:
    if not p.endswith('triggerstrings.txt'):
        continue
    r = analyze(p)
    if r and r[1] > bestn:
        best, bestn = (p, r[0]), r[1]
if best:
    p, kv = best
    out = os.path.join(OUT, '_casc_trigger_zh.txt')
    with open(out, 'w', encoding='utf-8') as f:
        for k, v in kv.items():
            f.write(f'{k}={v}\n')
    print(f'\n官方 TriggerStrings 最佳: {p}')
    print(f'  {len(kv):,} 键 / 含中文 {bestn:,}  ->  已导出 {out}')

c.close()
