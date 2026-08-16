# -*- coding: utf-8 -*-
"""修 IDA 确认加载的 Editor*.txt:
   EditorStrings.txt      10 裸行 -> 注释, 3 重复键 -> 去重, 1 空值 -> 删
   EditorCategoryStrings.txt  1 空值 -> 删
   EditorCatalogStrings.txt   不动(1824 个 ~ 是译者分隔符,非占位符)
   默认 dry-run,--apply 才写盘。
"""
import os, sys, shutil, time, collections
sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\StarCraft II\Editor'
APPLY = '--apply' in sys.argv
TS = time.strftime('%Y%m%d_%H%M%S')

for fn in ('EditorStrings.txt', 'EditorCategoryStrings.txt'):
    p = os.path.join(ROOT, fn)
    raw = open(p, 'rb').read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    crlf = b'\r\n' in raw
    lines = raw.decode('utf-8-sig', 'replace').replace('\r\n', '\n').split('\n')
    st = collections.Counter()
    out, seen = [], {}
    for ln in lines:
        if not ln.strip():
            out.append(ln); continue
        if ln.lstrip().startswith('//'):
            out.append(ln); st['cmt'] += 1; continue
        if '=' not in ln:
            out.append('// ' + ln); st['tocomment'] += 1; continue
        k, v = ln.split('=', 1)
        if not v.partition(' //')[0].strip():
            st['dropempty'] += 1; continue
        if k in seen:
            if seen[k] == v:
                st['dropdup'] += 1; continue        # 完全相同,直接去重
            st['dupdiff'] += 1                      # 值不同:保留后者(覆盖语义)
        seen[k] = v
        out.append(f'{k}={v}')
        st['ok'] += 1
    print(f'{fn}: 键 {st["ok"]:,}  裸行转注释 {st["tocomment"]}  '
          f'删同值重复 {st["dropdup"]}  异值重复 {st["dupdiff"]}  删空值 {st["dropempty"]}')
    if APPLY and (st['tocomment'] or st['dropdup'] or st['dropempty']):
        shutil.copy2(p, f'{p}.bak.{TS}')
        tmp = p + '.tmp'
        nl = '\r\n' if crlf else '\n'
        with open(tmp, 'w', encoding='utf-8', newline='') as f:
            if bom:
                f.write('\ufeff')
            f.write(nl.join(out))
            if not out[-1] == '':
                f.write(nl)
        os.replace(tmp, p)
        print(f'   -> 已写入(BOM={"保留" if bom else "无"} 换行={"CRLF" if crlf else "LF"},'
              f'备份 .bak.{TS})')

if not APPLY:
    print('\n[dry-run] 加 --apply 写盘')
