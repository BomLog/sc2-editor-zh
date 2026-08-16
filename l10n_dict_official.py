# -*- coding: utf-8 -*-
"""从官方 zhCN 字符串的 `中文 /// English` 双语对照行,提取权威 英文→中文 词典。
   同时用 同键跨文件(objectstrings英文 vs gamestrings中文)补充配对。"""
import os, re, sys, json, collections
sys.stdout.reconfigure(encoding='utf-8')
CJK = re.compile(r'[一-鿿]')
W = os.path.dirname(os.path.abspath(__file__))

def load(p):
    kv = {}
    with open(os.path.join(W, p), 'r', encoding='utf-8-sig', errors='replace') as f:
        for ln in f:
            ln = ln.rstrip('\r\n')
            if ln.strip() and '=' in ln and not ln.lstrip().startswith('//'):
                k, v = ln.split('=', 1)
                kv[k] = v
    return kv

G = load('_casc_zh_gamestrings.txt')
O = load('_casc_zh_objectstrings.txt')
T = load('_casc_zh_triggerstrings.txt')

# 词典: en(lower) -> Counter(zh)
pair = collections.defaultdict(collections.Counter)

def add(en, zh):
    en = en.strip(); zh = zh.strip()
    if not en or not zh: return
    if not CJK.search(zh): return
    if CJK.search(en): return
    if len(en) > 60 or len(zh) > 40: return
    if not re.search(r'[A-Za-z]', en): return
    pair[en.lower()][zh] += 1

# 1) `中文 /// English` 内建双语
n_dual = 0
for src in (G, O, T):
    for k, v in src.items():
        if ' /// ' in v:
            zh, _, en = v.partition(' /// ')
            if CJK.search(zh) and not CJK.search(en):
                add(en, zh); n_dual += 1
print(f'双语对照行(/// ): {n_dual:,}')

# 2) 同键跨文件配对: objectstrings 是英文原名, gamestrings 同键是中文
n_cross = 0
for k, ven in O.items():
    if CJK.search(ven): continue
    vzh = G.get(k)
    if vzh and CJK.search(vzh):
        add(ven, vzh.partition(' /// ')[0]); n_cross += 1
print(f'跨文件同键配对    : {n_cross:,}')

# 3) 官方 objectstrings 内部: Cat/Name/ID 英文 + 同 ID 的 Cat/EditorName 中文 之类
#    以及 gamestrings 内 Tooltip 不用;跳过

best = {}
for en, c in pair.items():
    zh, n = c.most_common(1)[0]
    # 冲突过多的丢弃(同一英文多种译法且票数接近)
    if len(c) > 1 and c.most_common(2)[1][1] >= n:
        continue
    best[en] = zh

print(f'去冲突后词条      : {len(best):,}')

# 拆出单词级 token 词典(用于组合翻译)
tok = {k: v for k, v in best.items() if ' ' not in k}
print(f'  其中单 token    : {len(tok):,}')

out = os.path.join(W, 'l10n_dict_official.json')
with open(out, 'w', encoding='utf-8') as f:
    json.dump({'_note': '官方 zhCN 提取: /// 双语 + 跨文件同键配对',
               'phrase': best, 'token': tok}, f, ensure_ascii=False, indent=0)
print(f'-> {os.path.basename(out)}')
for en in list(tok)[:15]:
    print(f'    {en} -> {tok[en]}')
