# -*- coding: utf-8 -*-
"""诊断 Editor\LocalizedData\ 下每个文件的真实用途与键格式,定位正确落点"""
import os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')

D = r"D:\StarCraft II\Editor\LocalizedData"
CJK = re.compile(r'[\u4e00-\u9fff]')

for fn in ['111GameStrings.txt', 'GameStrings.txt', 'TriggerStrings.txt',
           'ConversationStrings.txt', 'Errors.txt', 'ObjectStrings.txt']:
    p = os.path.join(D, fn)
    if not os.path.exists(p):
        continue
    txt = open(p, 'rb').read().decode('utf-8-sig', 'replace')
    lines = [l for l in txt.replace('\r\n', '\n').split('\n') if l.strip()]
    kv = [l for l in lines if '=' in l and not l.lstrip().startswith('//')]
    pref = collections.Counter(l.split('/', 1)[0] if '/' in l.split('=', 1)[0]
                               else l.split('=', 1)[0][:14] for l in kv)
    zh = sum(1 for l in kv if CJK.search(l.split('=', 1)[1]))
    print('=' * 72)
    print(f'{fn}   {os.path.getsize(p):,} 字节   {len(lines):,} 行   键 {len(kv):,}   含中文 {zh:,}')
    print('  键前缀 Top12: ' + ', '.join(f'{k}={n}' for k, n in pref.most_common(12)))
    for l in kv[:6]:
        print(f'    {l[:110]}')
