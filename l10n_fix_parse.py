# -*- coding: utf-8 -*-
"""修解析器致命缺陷:
   1) 无等号裸行 -> 转成 `// ` 注释(state 0 见 // 直接跳行,不再抛 Invalid key)
   2) 空值行     -> 删除(让编辑器回退英文,而非显示空白)
   3) ~ 不成对   -> 补回缺失的 ~(官方自身翻译 bug,会让语法文本错乱)
   默认 dry-run,--apply 才写盘。
"""
import os, re, sys, shutil, time, collections
sys.stdout.reconfigure(encoding='utf-8')
ED = r'D:\StarCraft II\Editor\LocalizedData'
APPLY = '--apply' in sys.argv
TS = time.strftime('%Y%m%d_%H%M%S')
CJK = re.compile(r'[一-鿿]')

# 缺失左 ~ 的模式: 中文/空格 后紧跟 裸标识符 + ~ (如 "至（offsetX~," / "的soundLink~")
FIX_TILDE = re.compile(r'(?<![~\w])([A-Za-z_]\w*)~')


def fix_tilde(v):
    """补回缺失的左 ~:对每个未配对的 `word~` 补成 `~word~`"""
    if v.count('~') % 2 == 0:
        return v, False
    # 从左到右扫描,配对状态机
    out, i, inside = [], 0, False
    while i < len(v):
        ch = v[i]
        if ch == '~':
            inside = not inside
            out.append(ch); i += 1; continue
        if not inside:
            m = re.match(r'([A-Za-z_]\w*)~', v[i:])
            if m:
                # 这是一个缺左 ~ 的占位符
                out.append('~' + m.group(0))
                i += m.end(); continue
        out.append(ch); i += 1
    r = ''.join(out)
    if r.count('~') % 2 == 0:
        return r, True
    # 仍不成对:尾部游离 ~(如 `~unitType~生产的单位类型数量~`)直接剥掉
    if r.endswith('~') and (r[:-1].count('~') % 2 == 0):
        return r[:-1], True
    return v, False


for name in ('ObjectStrings.txt', 'GameStrings.txt', 'TriggerStrings.txt'):
    p = os.path.join(ED, name)
    if not os.path.isfile(p):
        print(f'{name}: 不存在\n'); continue
    with open(p, 'r', encoding='utf-8-sig', errors='replace') as f:
        lines = f.read().replace('\r\n', '\n').split('\n')
    st = collections.Counter()
    out, samples = [], collections.defaultdict(list)
    for ln in lines:
        if not ln.strip():
            continue
        if ln.lstrip().startswith('//'):
            out.append(ln); st['cmt'] += 1; continue
        if '=' not in ln:
            out.append('// ' + ln)                 # 关键修复
            st['tocomment'] += 1
            if len(samples['tocomment']) < 5:
                samples['tocomment'].append(ln[:70])
            continue
        k, v = ln.split('=', 1)
        nv, fixed = fix_tilde(v)
        if not nv.partition(' //')[0].strip():
            st['dropempty'] += 1          # 含"整值只有一个 ~"的官方垃圾条目
            samples['dropempty'].append(k)
            continue
        if fixed:
            st['tilde'] += 1
            if len(samples['tilde']) < 4:
                samples['tilde'].append(f'{k}\n        旧={v[:80]}\n        新={nv[:80]}')
            v = nv
        out.append(f'{k}={v}')
        st['ok'] += 1
    print(f'{name}: 键 {st["ok"]:,}  注释 {st["cmt"]:,}  '
          f'裸行转注释 {st["tocomment"]:,}  删空值 {st["dropempty"]:,}  修~ {st["tilde"]:,}')
    for t, ttl in (('tocomment', '转注释'), ('dropempty', '删空值'), ('tilde', '修~')):
        if samples[t]:
            print(f'    {ttl}: ' + ('' if t == 'tilde' else ', ').join(
                samples[t][:5]) if t != 'tilde' else f'    {ttl}:')
            if t == 'tilde':
                for s in samples[t]:
                    print('      ' + s)
    if APPLY and (st['tocomment'] or st['dropempty'] or st['tilde']):
        shutil.copy2(p, f'{p}.bak.{TS}')
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='') as f:
            f.write('\ufeff')
            for ln in out:
                f.write(ln + '\r\n')
        os.replace(tmp, p)
        print(f'    -> 已写入(备份 .bak.{TS})')
    print()

if not APPLY:
    print('[dry-run] 加 --apply 写盘')
