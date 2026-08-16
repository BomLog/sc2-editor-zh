# -*- coding: utf-8 -*-
"""统计「中文+拉丁尾巴」里真正的未译英文词,按频次排序。
   区分:合法后缀(A/B/ID/AOE/UI/Boss/X/Y/Z...)vs 漏译英文词(Pain/Dragons/Ghouls...)"""
import re, sys, collections
sys.stdout.reconfigure(encoding='utf-8')

OBJ = r"D:\StarCraft II\Editor\LocalizedData\ObjectStrings.txt"
CAT = r"D:\StarCraft II\Editor\EditorCatalogStrings.txt"
CJK = re.compile(r'[\u4e00-\u9fff]')

# 合法保留:单/双字母编号、罗马数字、公认缩写、坐标轴
KEEP = set("""A B C D E F G H I J K L M N O P Q R S T U V W X Y Z
II III IV V VI VII VIII IX X XI XII
ID IDs UI AI AOE HP MP XP SP CP NP LM DPS FX SFX VFX GFX UV RGB HDR LOD
Boss NPC PC CD TOD DoT AoE OK GG WTF ATK DEF HUD FPS
""".split())

def tails(path, label):
    tail_re = re.compile(r'([\u4e00-\u9fff\)\]）】])[\-_ ]?([A-Za-z][A-Za-z0-9]*)$')
    cnt = collections.Counter()
    samples = collections.defaultdict(list)
    total = 0
    for ln in open(path, 'rb').read().decode('utf-8-sig').replace('\r\n', '\n').split('\n'):
        if not ln.strip() or ln.lstrip().startswith('//') or '=' not in ln:
            continue
        k, v = ln.split('=', 1)
        v = v.split('///')[0].strip()      # 去掉 /// 英文对照
        v = re.sub(r'\s*//.*$', '', v)     # 去掉行尾注释
        if not CJK.search(v):
            continue
        m = tail_re.search(v)
        if not m:
            continue
        total += 1
        w = m.group(2)
        cnt[w] += 1
        if len(samples[w]) < 3:
            samples[w].append(f'{k} = {v}')

    bad = {w: n for w, n in cnt.items() if w not in KEEP and not re.fullmatch(r'\d+', w)}
    keep_n = total - sum(bad.values())
    print('=' * 70)
    print(f'### {label}')
    print(f'  中文+拉丁尾 共 {total:,} 条')
    print(f'  合法后缀(A/ID/AOE/Boss/罗马数字等,无需改): {keep_n:,}')
    print(f'  疑似漏译英文词: {sum(bad.values()):,} 条 / {len(bad):,} 个不同词')
    print(f'  Top 60 漏译词:')
    for w, n in sorted(bad.items(), key=lambda x: -x[1])[:60]:
        print(f'    {n:5d}  {w:22s} 例: {samples[w][0][:78]}')
    return bad, samples

b1, s1 = tails(OBJ, 'ObjectStrings.txt')
b2, s2 = tails(CAT, 'EditorCatalogStrings.txt')

print()
print('=== 未译条目(值完全无中文) ===')
for path, label in ((OBJ, 'ObjectStrings.txt'), (CAT, 'EditorCatalogStrings.txt')):
    n = tot = 0
    ex = []
    for ln in open(path, 'rb').read().decode('utf-8-sig').replace('\r\n', '\n').split('\n'):
        if not ln.strip() or ln.lstrip().startswith('//') or '=' not in ln:
            continue
        tot += 1
        k, v = ln.split('=', 1)
        if not CJK.search(v):
            n += 1
            if len(ex) < 6:
                ex.append(f'{k} = {v}'[:80])
    print(f'  {label}: {n:,} / {tot:,} ({n*100.0/tot:.1f}%)')
    for e in ex:
        print(f'     {e}')
