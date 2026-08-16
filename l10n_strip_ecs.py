# -*- coding: utf-8 -*-
"""剥离 EditorCatalogStrings.txt 值末尾的 ECS#### 追踪码。
   解析器规则(sub_140193E80 state4):值里遇 ' //' 即截断为注释,
   所以只处理 ' //' 之前的可见部分,注释原样保留。
   默认 dry-run,加 --apply 写入。"""
import os, re, sys, shutil, datetime
sys.stdout.reconfigure(encoding='utf-8')

CAT = r"D:\StarCraft II\Editor\EditorCatalogStrings.txt"
APPLY = '--apply' in sys.argv
ECS = re.compile(r'ECS\d{4}$')

txt = open(CAT, 'rb').read().decode('utf-8-sig')
lines = txt.replace('\r\n', '\n').split('\n')
if lines and lines[-1] == '':
    lines.pop()

out, hits = [], []
for i, ln in enumerate(lines, 1):
    if not ln.strip() or ln.lstrip().startswith('//') or '=' not in ln:
        out.append(ln)
        continue
    k, v = ln.split('=', 1)
    head, sep, tail = v.partition(' //')     # head = 解析器可见部分
    if not ECS.search(head):                 # 只碰含 ECS 的行,其余原样保留
        out.append(ln)
        continue
    new = ECS.sub('', head).rstrip()
    if not new:                              # 剥完变空,保守跳过
        out.append(ln)
        hits.append((i, k, head, '<跳过:剥完为空>'))
        continue
    out.append(f'{k}={new}{sep}{tail}')
    hits.append((i, k, head, new))

print(f'{CAT}')
print(f'  剥离 {len(hits)} 条')
for i, k, o, n in hits[:20]:
    print(f'   L{i} {k}\n       {o}  ->  {n}')
if len(hits) > 20:
    print(f'   ... 其余 {len(hits)-20} 条同型')

rest = sum(1 for l in out if '=' in l and not l.lstrip().startswith('//')
           and re.search(r'ECS\d{4}$', l.split('=', 1)[1].partition(' //')[0]))
print(f'  复核: 剩余尾部ECS {rest}   总行 {len(out):,}')

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
