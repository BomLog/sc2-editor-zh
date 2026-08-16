# -*- coding: utf-8 -*-
"""修 EditorCatalogStrings.txt:
   1) 被换行切断的值(孤立行合回上一行)
   2) 占位符模板行 EDSTR_ENTRYTYPE_xxxxx=你的翻译
   3) 空右值行(键= )删除,让编辑器回退显示原始英文/ID,而非空白
   默认 dry-run,加 --apply 写入。"""
import os, re, sys, shutil, datetime, collections
sys.stdout.reconfigure(encoding='utf-8')

CAT = r"D:\StarCraft II\Editor\EditorCatalogStrings.txt"
APPLY = '--apply' in sys.argv

txt = open(CAT, 'rb').read().decode('utf-8-sig')
lines = txt.replace('\r\n', '\n').split('\n')
trail_nl = lines and lines[-1] == ''
if trail_nl:
    lines.pop()

out, fixed_join, dropped_ph, dropped_empty = [], [], [], []
for i, ln in enumerate(lines, 1):
    s = ln.strip()
    if not s:
        out.append(ln)
        continue
    if s.startswith('//'):
        out.append(ln)
        continue

    # 1) 无 '=' 且非注释非空 -> 被切断的值,合回上一条 key=value
    if '=' not in ln:
        j = len(out) - 1
        while j >= 0 and (not out[j].strip() or out[j].lstrip().startswith('//')):
            j -= 1
        if j >= 0 and '=' in out[j]:
            fixed_join.append((i, out[j], ln))
            out[j] = out[j] + ln
        else:
            out.append(ln)          # 找不到宿主,原样留着
        continue

    k, v = ln.split('=', 1)
    # 2) 占位符模板
    if k == 'EDSTR_ENTRYTYPE_xxxxx' or v.strip() == '你的翻译':
        dropped_ph.append((i, ln))
        continue
    # 3) 空右值
    if v == '':
        dropped_empty.append((i, k))
        continue
    out.append(ln)

print(f'{CAT}')
print(f'  原始 {len(lines):,} 行  ->  {len(out):,} 行')
print(f'\n1) 合回被切断的值: {len(fixed_join)}')
for i, host, frag in fixed_join:
    print(f'   L{i} 碎片 {frag!r}')
    print(f'        合并后 -> {host + frag}')
print(f'\n2) 删占位符模板行: {len(dropped_ph)}')
for i, ln in dropped_ph:
    print(f'   L{i}: {ln}')
print(f'\n3) 删空右值行: {len(dropped_empty)}')
c = collections.Counter(re.match(r'(EDSTR_[A-Z]+)_', k).group(1)
                        if re.match(r'(EDSTR_[A-Z]+)_', k) else '(other)'
                        for _, k in dropped_empty)
for p, n in c.most_common():
    print(f'   {p:24s} {n}')
print('   样例: ' + ', '.join(k for _, k in dropped_empty[:3]))

# 复核:输出里不该再有裸行/重复键
keys = collections.Counter(l.split('=', 1)[0] for l in out
                           if '=' in l and not l.lstrip().startswith('//'))
bare = [l for l in out if l.strip() and '=' not in l and not l.lstrip().startswith('//')]
print(f'\n复核: 裸行 {len(bare)}   重复键 {sum(1 for v in keys.values() if v > 1)}   唯一键 {len(keys):,}')

if not APPLY:
    print('\n[dry-run] 加 --apply 执行写入')
    sys.exit(0)

bak = CAT + '.bak.' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copy2(CAT, bak)
tmp = CAT + '.tmp'
with open(tmp, 'wb') as f:
    f.write(b'\xef\xbb\xbf')
    f.write(('\r\n'.join(out) + '\r\n').encode('utf-8'))
os.replace(tmp, CAT)
print(f'\n已写入  {len(out):,} 行, {os.path.getsize(CAT):,} 字节')
print(f'备份 -> {os.path.basename(bak)}')
