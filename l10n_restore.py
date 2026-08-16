# -*- coding: utf-8 -*-
"""从最全备份恢复 ObjectStrings.txt(去重、保留 BOM+CRLF)。
   默认 dry-run,加 --apply 才写入。"""
import os, re, sys, shutil, datetime, collections
sys.stdout.reconfigure(encoding='utf-8')

D = r"D:\StarCraft II\Editor\LocalizedData"
CUR = os.path.join(D, "ObjectStrings.txt")
SRC = os.path.join(D, "ObjectStrings_backup_20260815.txt")
APPLY = '--apply' in sys.argv
CJK = re.compile(r'[\u4e00-\u9fff]')

raw = open(SRC, 'rb').read()
txt = raw.decode('utf-8-sig')
lines = txt.replace('\r\n', '\n').split('\n')

# --- 源文件健康检查 ---
seen, out, dup, badfmt, empty, cmt = {}, [], 0, [], [], 0
for i, ln in enumerate(lines, 1):
    if not ln.strip():
        continue
    if ln.lstrip().startswith('//'):     # 生成器分段注释,原样保留
        cmt += 1
        out.append(ln)
        continue
    if '=' not in ln:
        badfmt.append((i, ln))
        out.append(ln)                  # 分段标记,原样保留
        continue
    k, v = ln.split('=', 1)
    if k in seen:
        dup += 1
        if seen[k] != v:
            print(f'  !! 重复键值冲突 L{i} {k}: {seen[k]!r} vs {v!r}')
        continue
    if v == '':
        empty.append(k)
        continue          # 空值直接丢弃,编辑器会显示原始ID而不是空白
    seen[k] = v
    out.append(f'{k}={v}')

cats = collections.Counter(k.split('/', 1)[0] for k in seen)
zh = sum(1 for v in seen.values() if CJK.search(v))
print(f'源: {os.path.basename(SRC)}')
print(f'  原始行 {len(lines):,}  →  有效键 {len(seen):,}  '
      f'(去重 {dup:,}, 弃空值 {len(empty):,}, 注释 {cmt}, 格式错 {len(badfmt)})')
print(f'  含中文 {zh:,} ({zh*100.0/len(seen):.1f}%)   分类 {len(cats)}')
for i, ln in badfmt[:5]:
    print(f'  格式错 L{i}: {ln[:70]}')
print('  Top分类:', ', '.join(f'{c}={n}' for c, n in cats.most_common(8)))

curkeys = set()
for ln in open(CUR, 'rb').read().decode('utf-8-sig').replace('\r\n', '\n').split('\n'):
    if ln.strip() and '=' in ln:
        curkeys.add(ln.split('=', 1)[0])
print(f'\n当前文件键 {len(curkeys):,}   恢复后净增 {len(set(seen) - curkeys):,}   '
      f'当前独有(会丢失) {len(curkeys - set(seen)):,}')

if not APPLY:
    print('\n[dry-run] 加 --apply 执行写入')
    sys.exit(0)

bak = CUR + '.bak.pre_restore_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copy2(CUR, bak)
tmp = CUR + '.tmp'
with open(tmp, 'wb') as f:
    f.write(b'\xef\xbb\xbf')
    f.write(('\r\n'.join(out) + '\r\n').encode('utf-8'))
os.replace(tmp, CUR)
print(f'\n已写入 {CUR}')
print(f'  {len(out):,} 行, {os.path.getsize(CUR):,} 字节')
print(f'  旧文件备份 -> {os.path.basename(bak)}')
