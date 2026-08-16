# -*- coding: utf-8 -*-
"""部署到 IDA 代码确认的落点 LocalizedData/ObjectStringsProduct.txt。
   证据: off_144C25EF0[2] 被 sub_140AD2860 @0x140ad2afc 引用并解析;
         而 LocalizedData/ObjectStrings.txt 的全局 0x144C25E70 有 0 个代码引用。
   只写含中文的键(英文键一律不写 => 对官方字符串零退化)。
"""
import os, re, sys, shutil, time
sys.stdout.reconfigure(encoding='utf-8')
CJK = re.compile(r'[一-鿿]')
ED = r'D:\StarCraft II\Editor\LocalizedData'
APPLY = '--apply' in sys.argv
TS = time.strftime('%Y%m%d_%H%M%S')
SRC = os.path.join(ED, 'ObjectStrings.txt')
DST = os.path.join(ED, 'ObjectStringsProduct.txt')

kv = {}
with open(SRC, 'r', encoding='utf-8-sig', errors='replace') as f:
    for ln in f:
        ln = ln.rstrip('\r\n')
        if not ln.strip() or ln.lstrip().startswith('//') or '=' not in ln:
            continue
        k, v = ln.split('=', 1)
        if CJK.search(v.partition(' //')[0]):
            kv[k] = v

old = 0
if os.path.isfile(DST):
    with open(DST, 'r', encoding='utf-8-sig', errors='replace') as f:
        old = sum(1 for ln in f if '=' in ln and not ln.lstrip().startswith('//'))

print(f'源 ObjectStrings.txt 含中文键 {len(kv):,}')
print(f'目标 ObjectStringsProduct.txt {"已存在 " + format(old, ",") + " 键(将覆盖)" if old else "不存在(新建)"}')
print(f'  ★ 这是 IDA 确认被 sub_140AD2860 解析的路径')
print(f'  ✗ ObjectStrings.txt 全局 0x144C25E70 零代码引用 => 那个落点是死的')

if not APPLY:
    print('\n[dry-run] 加 --apply 写盘')
    sys.exit(0)

if os.path.isfile(DST):
    shutil.copy2(DST, f'{DST}.bak.{TS}')
    print(f'备份 ObjectStringsProduct.txt.bak.{TS}')
tmp = DST + '.tmp'
with open(tmp, 'w', encoding='utf-8', newline='') as f:
    f.write('\ufeff')
    f.write(f'// 对象名汉化 {len(kv)} 条 ({TS})\r\n')
    f.write('// 落点依据: IDA off_144C25EF0[2] <- sub_140AD2860 @0x140ad2afc\r\n')
    for k in sorted(kv):
        f.write(f'{k}={kv[k]}\r\n')
os.replace(tmp, DST)
print(f'写入 ObjectStringsProduct.txt  {len(kv):,} 键  {os.path.getsize(DST):,} B')
