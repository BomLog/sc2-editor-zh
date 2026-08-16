# -*- coding: utf-8 -*-
"""审计已部署的汉化文件 ObjectStrings.txt / EditorCatalogStrings.txt"""
import io, os, re, sys, collections

sys.stdout.reconfigure(encoding='utf-8')

OBJ = r"D:\StarCraft II\Editor\LocalizedData\ObjectStrings.txt"
CAT = r"D:\StarCraft II\Editor\EditorCatalogStrings.txt"

CJK = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef]')

def load(p):
    raw = open(p, 'rb').read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    txt = raw.decode('utf-8-sig')
    crlf = txt.count('\r\n')
    lines = txt.replace('\r\n', '\n').split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    return bom, crlf, lines

def audit(path, label):
    print('=' * 70)
    print(f'### {label}')
    print(f'  路径: {path}')
    if not os.path.exists(path):
        print('  !! 文件不存在')
        return None
    bom, crlf, lines = load(path)
    sz = os.path.getsize(path)
    print(f'  大小: {sz:,} 字节   行数: {len(lines):,}   BOM: {bom}   CRLF行: {crlf:,}')

    bad_fmt, empty_val, keys = [], [], collections.Counter()
    ascii_val, artifact, ctrl, dbl_eq = [], [], [], 0
    cats = collections.Counter()
    for i, ln in enumerate(lines, 1):
        if not ln.strip():
            continue
        if '=' not in ln:
            bad_fmt.append((i, ln))
            continue
        k, v = ln.split('=', 1)
        keys[k] += 1
        if '=' in v:
            dbl_eq += 1
        if v == '':
            empty_val.append((i, k))
        elif not CJK.search(v):
            ascii_val.append((i, k, v))
        else:
            # 中文里夹了拉丁词尾碎片(词典替换残留)
            if re.search(r'[\u4e00-\u9fff]-?[A-Za-z]{1,8}$', v):
                artifact.append((i, k, v))
        if any(ord(c) < 32 for c in ln):
            ctrl.append(i)
        cats[k.split('/', 1)[0]] += 1

    print(f'  分类数: {len(cats)}')
    print(f'  唯一键: {len(keys):,}   重复键: {sum(1 for c in keys.values() if c > 1)}')
    print(f'  格式错(无=): {len(bad_fmt)}   空值: {len(empty_val)}   值含额外=: {dbl_eq}   含控制字符行: {len(ctrl)}')
    print(f'  未翻译(值无CJK): {len(ascii_val):,}  ({len(ascii_val)*100.0/max(1,len(lines)):.1f}%)')
    print(f'  疑似残留碎片: {len(artifact):,}')

    if bad_fmt:
        print('  -- 格式错样例:')
        for i, ln in bad_fmt[:5]:
            print(f'     L{i}: {ln[:80]}')
    if empty_val:
        print('  -- 空值样例:')
        for i, k in empty_val[:5]:
            print(f'     L{i}: {k}')
    if ascii_val:
        print('  -- 未翻译样例:')
        for i, k, v in ascii_val[:15]:
            print(f'     L{i}: {k} = {v}')
    if artifact:
        print('  -- 残留碎片样例:')
        for i, k, v in artifact[:20]:
            print(f'     L{i}: {k} = {v}')
    return keys, cats, ascii_val, artifact

audit(OBJ, 'ObjectStrings.txt (数据实例名)')
audit(CAT, 'EditorCatalogStrings.txt (编辑器UI类型/字段名)')
