# -*- coding: utf-8 -*-
"""对象名总构建:
   1) 官方中文优先回填(修 868 条退化)
   2) 词典新译三方均无中文的键
   3) 双落点输出: ObjectStrings.txt 全量 + GameStrings.txt 增量(只写含中文的键)
   默认 dry-run,--apply 才写盘。
"""
import os, re, sys, shutil, time, collections
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from l10n_engine import Engine, CJK

W = os.path.dirname(os.path.abspath(__file__))
ED = r'D:\StarCraft II\Editor\LocalizedData'
APPLY = '--apply' in sys.argv
TS = time.strftime('%Y%m%d_%H%M%S')


def load_lines(p):
    with open(p, 'r', encoding='utf-8-sig', errors='replace') as f:
        return f.read().replace('\r\n', '\n').split('\n')


def load_kv(p):
    kv = {}
    if not os.path.isfile(p):
        return kv
    for ln in load_lines(p):
        if ln.strip() and '=' in ln and not ln.lstrip().startswith('//'):
            k, v = ln.split('=', 1)
            kv[k] = v
    return kv


def visible(v):
    """解析器可见部分(' //' 之后是注释)"""
    return v.partition(' //')[0]


OBJ = os.path.join(ED, 'ObjectStrings.txt')
GS = os.path.join(ED, 'GameStrings.txt')
off_o = load_kv(os.path.join(W, '_casc_zh_objectstrings.txt'))
off_g = load_kv(os.path.join(W, '_casc_zh_gamestrings.txt'))
loc_g = load_kv(GS)
lines = load_lines(OBJ)
eng = Engine()

# 官方权威中文表(gamestrings 优先,它是显示用的)
auth = {}
for k, v in off_o.items():
    if CJK.search(visible(v)):
        auth[k] = visible(v)
for k, v in off_g.items():
    if CJK.search(visible(v)):
        auth[k] = visible(v)
print(f'官方权威中文键 {len(auth):,}')

st = collections.Counter()
newtr = collections.Counter()
out = []
seen = set()
samples = {'backfill': [], 'trans': [], 'miss': []}

for ln in lines:
    if not ln.strip():
        continue
    if ln.lstrip().startswith('//') or '=' not in ln:
        out.append(ln); st['passthru'] += 1; continue
    k, v = ln.split('=', 1)
    if k in seen:
        st['dup'] += 1; continue
    seen.add(k)
    vis = visible(v)
    if CJK.search(vis):
        # 已有中文:若官方也有中文且不同,信官方? -> 不动,保留本地(本地更全)
        out.append(f'{k}={v}'); st['keep_zh'] += 1; continue
    # 无中文
    a = auth.get(k)
    if a:
        out.append(f'{k}={a}'); st['backfill'] += 1
        if len(samples['backfill']) < 8:
            samples['backfill'].append(f'{k}: {vis} -> {a}')
        continue
    # 词典新译
    zh, full = eng.translate(vis)
    if full and CJK.search(zh):
        out.append(f'{k}={zh}'); st['trans'] += 1
        newtr[k.split('/')[0]] += 1
        if len(samples['trans']) < 12:
            samples['trans'].append(f'{k}: {vis} -> {zh}')
        continue
    out.append(f'{k}={v}'); st['miss'] += 1
    if len(samples['miss']) < 12:
        samples['miss'].append(f'{k}: {vis}')

print(f'\nObjectStrings 处理: 保留中文 {st["keep_zh"]:,}  官方回填 {st["backfill"]:,}  '
      f'词典新译 {st["trans"]:,}  仍缺 {st["miss"]:,}  注释/分隔 {st["passthru"]:,}  去重 {st["dup"]:,}')
tot = st['keep_zh'] + st['backfill'] + st['trans'] + st['miss']
zh_after = st['keep_zh'] + st['backfill'] + st['trans']
print(f'  键总数 {tot:,}   汉化率 {zh_after*100.0/tot:.1f}%  (原 {st["keep_zh"]*100.0/tot:.1f}%)')
print('\n  回填样例:');  [print('    ' + s) for s in samples['backfill']]
print('  新译样例:');    [print('    ' + s) for s in samples['trans']]
print('  仍缺样例:');    [print('    ' + s) for s in samples['miss']]
print('\n  新译前缀 Top12: ' + ', '.join(f'{a}={b}' for a, b in newtr.most_common(12)))

# ---- 双落点: GameStrings 增量 ----
final = {}
for ln in out:
    if '=' in ln and not ln.lstrip().startswith('//'):
        k, v = ln.split('=', 1)
        final[k] = v
add_g = {k: v for k, v in final.items() if CJK.search(visible(v)) and k not in loc_g}
print(f'\nGameStrings 双落点: 本地现有 {len(loc_g)} 键,追加 {len(add_g):,} 条含中文键 '
      f'(不覆盖本地已有,官方英文键一律不写 => 零退化)')

if not APPLY:
    print('\n[dry-run] 加 --apply 写盘')
    sys.exit(0)

for path, payload in ((OBJ, None), (GS, None)):
    if os.path.isfile(path):
        bak = f'{path}.bak.{TS}'
        shutil.copy2(path, bak)
        print(f'备份 {os.path.basename(bak)}')

tmp = OBJ + '.tmp'
with open(tmp, 'w', encoding='utf-8', newline='') as f:
    f.write('\ufeff')
    for ln in out:
        f.write(ln + '\r\n')
os.replace(tmp, OBJ)
print(f'写入 ObjectStrings.txt  {len(out):,} 行')

g_lines = load_lines(GS) if os.path.isfile(GS) else []
g_lines = [l for l in g_lines if l.strip() != '']
tmp = GS + '.tmp'
with open(tmp, 'w', encoding='utf-8', newline='') as f:
    f.write('\ufeff')
    for ln in g_lines:
        f.write(ln + '\r\n')
    f.write(f'// ==== 对象名汉化(ObjectStrings 镜像, {TS}) ====\r\n')
    for k in sorted(add_g):
        f.write(f'{k}={add_g[k]}\r\n')
os.replace(tmp, GS)
print(f'写入 GameStrings.txt  原 {len(g_lines)} 行 + {len(add_g):,} 条')
