# -*- coding: utf-8 -*-
"""触发器汉化构建:
   基底 = 官方 zhCN triggerstrings 合并(55,043 键 / 21,558 中文)
   叠加 = 本地已有中文  +  词典新译
   保护 = ~param~ / <占位符> / %1 %2 / #ID 一律原样保留
   默认 dry-run,--apply 才写盘。
"""
import os, re, sys, shutil, time, collections
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from l10n_engine import Engine, CJK

W = os.path.dirname(os.path.abspath(__file__))
ED = r'D:\StarCraft II\Editor\LocalizedData'
TRG = os.path.join(ED, 'TriggerStrings.txt')
APPLY = '--apply' in sys.argv
TS = time.strftime('%Y%m%d_%H%M%S')

# 占位符:~Xxx~ / <Xxx> / %1 / #Xxx / {Xxx}
PH = re.compile(r'~[^~]*~|<[^<>]*>|%\d+|#[A-Za-z_]\w*|\{[^{}]*\}')
# 高价值前缀(编辑器界面直接可见)
PRIOR = ('FunctionDef/Name', 'ParamDef/Name', 'PresetValue/Name', 'Category/Name',
         'Preset/Name', 'FunctionDef/Grammar', 'FunctionDef/Hint', 'ParamDef/Hint',
         'SubFuncType/Name', 'Label/Name', 'Library/Name')


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
    return v.partition(' //')[0]


def tr_with_ph(en, eng, allow_token=True):
    """保护占位符后翻译:占位符切段,只译段间文本"""
    spans = [(m.start(), m.end(), m.group(0)) for m in PH.finditer(en)]
    if not spans:
        return eng.translate(en, allow_token)
    segs, ok_all, any_zh, last = [], True, False, 0
    for s, e, g in spans:
        seg = en[last:s]
        if seg.strip():
            zh, full = eng.translate(seg.strip(), allow_token)
            segs.append(zh)
            ok_all &= full
            any_zh |= bool(CJK.search(zh))
        elif seg:
            segs.append(seg)
        segs.append(g)                       # 占位符原样
        last = e
    tail = en[last:]
    if tail.strip():
        zh, full = eng.translate(tail.strip(), allow_token)
        segs.append(zh); ok_all &= full; any_zh |= bool(CJK.search(zh))
    elif tail:
        segs.append(tail)
    return ''.join(segs), ok_all and any_zh


off = load_kv(os.path.join(W, '_casc_zh_triggerstrings.txt'))
loc_lines = load_lines(TRG)
loc = load_kv(TRG)
eng = Engine()

auth = {k: visible(v) for k, v in off.items() if CJK.search(visible(v))}
print(f'官方触发器中文 {len(auth):,} / 共 {len(off):,} 键')
print(f'本地触发器 {len(loc):,} 键 / {sum(1 for v in loc.values() if CJK.search(visible(v))):,} 中文')

st = collections.Counter()
samples = {'backfill': [], 'trans': [], 'trans_sent': [], 'miss': []}
out, seen = [], set()

def handle(k, v, from_official=False):
    """-> 输出行"""
    vis = visible(v)
    if CJK.search(vis):
        st['keep_zh' if not from_official else 'off_zh'] += 1
        return f'{k}={v}'
    a = auth.get(k)
    if a:
        st['backfill'] += 1
        if len(samples['backfill']) < 6:
            samples['backfill'].append(f'{k}\n        {vis}\n     -> {a}')
        return f'{k}={a}'
    # 句子类(Grammar/Hint/Tooltip/Desc)禁 token 拼接,只认整句权威译文
    sentence = bool(re.search(r'/(Grammar|Hint|Tooltip|Desc|Description|Comment)/', k))
    zh, full = tr_with_ph(vis, eng, allow_token=not sentence)
    if full and CJK.search(zh):
        st['trans_sent' if sentence else 'trans'] += 1
        bag = samples['trans_sent'] if sentence else samples['trans']
        if len(bag) < 8:
            bag.append(f'{k}\n        {vis}\n     -> {zh}')
        return f'{k}={zh}'
    st['miss'] += 1
    if len(samples['miss']) < 8:
        samples['miss'].append(f'{k} = {vis}')
    return f'{k}={v}'

# 1) 保留本地原有行序 + 注释
for ln in loc_lines:
    if not ln.strip():
        continue
    if ln.lstrip().startswith('//') or '=' not in ln:
        out.append(ln); st['passthru'] += 1; continue
    k, v = ln.split('=', 1)
    if k in seen:
        st['dup'] += 1; continue
    seen.add(k)
    out.append(handle(k, v))

# 2) 追加官方独有键(20,737 条中文 + 其余英文也补上,英文的走词典新译)
addn = 0
tailout = []
for k in sorted(off):
    if k in seen:
        continue
    seen.add(k)
    tailout.append(handle(k, off[k], from_official=True))
    addn += 1

tot = len(seen)
zh_after = (st['keep_zh'] + st['off_zh'] + st['backfill']
            + st['trans'] + st['trans_sent'])
print(f'\n本地行处理: 已中文 {st["keep_zh"]:,}  官方回填 {st["backfill"]:,}  '
      f'词典新译(名词) {st["trans"]:,}  整句权威命中 {st["trans_sent"]:,}  '
      f'仍缺 {st["miss"]:,}  注释 {st["passthru"]:,}  去重 {st["dup"]:,}')
print(f'追加官方独有键 {addn:,}(其中官方自带中文 {st["off_zh"]:,})')
print(f'\n合计 {tot:,} 键  含中文 {zh_after:,} ({zh_after*100.0/tot:.1f}%)')
print(f'  原本地: {len(loc):,} 键 / {sum(1 for v in loc.values() if CJK.search(visible(v))):,} 中文 (12.2%)')

for name, ttl in (('backfill', '官方回填'), ('trans', '词典新译(名词)'),
                  ('trans_sent', '整句权威命中'), ('miss', '仍缺')):
    print(f'\n  {ttl}样例:')
    for s in samples[name]:
        print('    ' + s)

# 高价值前缀覆盖率
final = {}
for ln in out + tailout:
    if '=' in ln and not ln.lstrip().startswith('//'):
        k, v = ln.split('=', 1); final[k] = v
print('\n  高价值前缀覆盖:')
for p in PRIOR:
    ks = [k for k in final if k.startswith(p + '/')]
    if not ks: continue
    z = sum(1 for k in ks if CJK.search(visible(final[k])))
    print(f'    {p:<22} {z:6,d}/{len(ks):6,d}  {z*100.0/len(ks):5.1f}%')

if not APPLY:
    print('\n[dry-run] 加 --apply 写盘')
    sys.exit(0)

shutil.copy2(TRG, f'{TRG}.bak.{TS}')
print(f'\n备份 TriggerStrings.txt.bak.{TS}')
tmp = TRG + '.tmp'
with open(tmp, 'w', encoding='utf-8', newline='') as f:
    f.write('\ufeff')
    for ln in out:
        f.write(ln + '\r\n')
    f.write(f'// ==== 官方 zhCN 触发器基底补全 ({addn} 条, {TS}) ====\r\n')
    for ln in tailout:
        f.write(ln + '\r\n')
os.replace(tmp, TRG)
print(f'写入 TriggerStrings.txt  {len(out) + len(tailout) + 1:,} 行')
