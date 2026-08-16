# -*- coding: utf-8 -*-
"""统计所有仍未汉化条目里的高频未知 token,按频次排序输出待补词表。"""
import os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from l10n_engine import Engine, CJK, split_ident, KEEP

W = os.path.dirname(os.path.abspath(__file__))
ED = r'D:\StarCraft II\Editor\LocalizedData'
eng = Engine()
PH = re.compile(r'~[^~]*~|<[^<>]*>|%\d+|#[A-Za-z_]\w*|\{[^{}]*\}')


def load_kv(p):
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


srcs = {
    'trigger': load_kv(os.path.join(W, '_casc_zh_triggerstrings.txt')),
    'trigger_local': load_kv(os.path.join(ED, 'TriggerStrings.txt')),
    'object': load_kv(os.path.join(ED, 'ObjectStrings.txt')),
}
unk = collections.Counter()
ctx = {}
for name, kv in srcs.items():
    for k, v in kv.items():
        vis = v.partition(' //')[0]
        if not vis.strip() or CJK.search(vis):
            continue
        zh, full = eng.translate(vis)
        if full and CJK.search(zh):
            continue
        clean = PH.sub(' ', vis)
        for t in split_ident(clean):
            if t.isdigit() or t.upper() in KEEP:
                continue
            tl = t.lower()
            if tl in eng.tokmap or tl in eng.phrase:
                continue
            if len(tl) < 3:
                continue
            unk[tl] += 1
            ctx.setdefault(tl, vis[:60])

print(f'未知 token 种类 {len(unk):,}  出现总次数 {sum(unk.values()):,}')
print('\nTop 120 高频未知 token(补这些收益最大):')
out = []
for t, n in unk.most_common(120):
    print(f'    {n:6,d}  {t:<24} 例: {ctx[t]}')
    out.append(f'{t}\t{n}\t{ctx[t]}')
with open(os.path.join(W, '_gap_tokens.txt'), 'w', encoding='utf-8') as f:
    for t, n in unk.most_common(1500):
        f.write(f'{t}\t{n}\t{ctx[t]}\n')
print(f'\n-> _gap_tokens.txt (Top1500)')
