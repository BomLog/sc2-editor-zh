#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
把校对过的演算体草稿并入 OB 汉化包的 ObjectStrings.txt。

安全策略:
  · 默认 dry-run, 只报告将写入多少条, 不动文件; 要落盘须显式加 --apply
  · --apply 时先备份为 ObjectStrings.txt.bak.<时间戳>
  · 只追加「包里还没有的键」; 已有译文一律不覆盖(除非 --overwrite-placeholder)
  · 默认只并 high 置信度, --conf low,none 可放宽

用法:
  python l10n_actor_merge.py                          # 预演(high)
  python l10n_actor_merge.py --apply                  # 落盘(high)
  python l10n_actor_merge.py --conf high,low --apply  # 放宽到 low
  python l10n_actor_merge.py --mod core --apply       # 只并某个 mod 段
"""
import argparse
import datetime
import io
import os
import re
import shutil

GAME = r"D:\StarCraft II"
PACK = os.path.join(GAME, "Editor", "LocalizedData", "ObjectStrings.txt")
DRAFT = r"e:\Code\sc2\Work\_actor_draft.txt"
PREFIX = "Actor/Name/"
HAS_BOM = False   # 由 read_pack() 按原文件探测, 写回时保持一致


def dec(b):
    for e in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return b.decode(e)
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", "replace")


def has_cjk(s):
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def read_draft(conf_ok, mod_filter):
    """-> [(key, value, mod)] 按草稿里的 mod 分段解析。"""
    rows, mod = [], "?"
    for line in dec(open(DRAFT, "rb").read()).splitlines():
        m = re.match(r"//\s*=====\s*(.+?)\s+待补", line)
        if m:
            mod = m.group(1)
            continue
        if not line.startswith(PREFIX) or "=" not in line:
            continue
        body, _, tail = line.partition("\t")
        conf = tail.replace("//", "").strip() or "?"
        if conf not in conf_ok:
            continue
        if mod_filter and mod.lower() != mod_filter.lower():
            continue
        k, _, v = body.partition("=")
        if v.strip():
            rows.append((k.strip(), v.strip(), mod))
    return rows


def read_pack():
    raw = open(PACK, "rb").read()
    # 先归一换行, 写回时再统一转 CRLF; 否则原文的 \r\n 会被二次转义成 \r\r\n
    text = dec(raw).replace("\r\n", "\n").replace("\r", "\n")
    global HAS_BOM
    HAS_BOM = raw[:3] == b"\xef\xbb\xbf"
    cur = {}
    for line in text.splitlines():
        if line.startswith(PREFIX) and "=" in line:
            k, _, v = line.partition("=")
            cur[k.strip()] = v.split("\t")[0].strip()
    return text, cur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真正写入(默认只预演)")
    ap.add_argument("--conf", default="high", help="并入哪些置信度, 逗号分隔")
    ap.add_argument("--mod", default="", help="只并入某个 mod 段")
    ap.add_argument("--overwrite-placeholder", action="store_true",
                    help="用草稿替换包里 id=id 形式的占位行")
    a = ap.parse_args()
    conf_ok = {c.strip() for c in a.conf.split(",") if c.strip()}

    rows = read_draft(conf_ok, a.mod)
    text, cur = read_pack()

    add, fix, skip = [], [], 0
    for k, v, mod in rows:
        old = cur.get(k)
        if old is None:
            add.append((k, v, mod))
        elif not has_cjk(old) and a.overwrite_placeholder:
            fix.append((k, v, old))
        else:
            skip += 1

    print("草稿命中 %d 条(置信度 %s%s)" % (len(rows), ",".join(sorted(conf_ok)),
                                     ", mod=" + a.mod if a.mod else ""))
    print("  新增        : %d" % len(add))
    print("  替换占位    : %d%s" % (len(fix), "" if a.overwrite_placeholder else " (未开启 --overwrite-placeholder)"))
    print("  跳过(已有译): %d" % skip)

    if not a.apply:
        print("\n[预演] 未写入任何文件。确认无误后加 --apply。")
        for k, v, mod in add[:10]:
            print("   + %s=%s   [%s]" % (k, v, mod))
        return

    if not add and not fix:
        print("\n无需改动。")
        return

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = PACK + ".bak." + stamp
    shutil.copy2(PACK, bak)
    print("\n已备份: %s" % bak)

    # 替换占位行
    if fix:
        lines = text.splitlines()
        want = {k: v for k, v, _ in fix}
        for i, line in enumerate(lines):
            if line.startswith(PREFIX) and "=" in line:
                k = line.partition("=")[0].strip()
                if k in want:
                    lines[i] = "%s=%s" % (k, want[k])
        text = "\n".join(lines)

    # 追加新增, 按 mod 分组
    chunks = []
    bymod = {}
    for k, v, mod in add:
        bymod.setdefault(mod, []).append((k, v))
    for mod in sorted(bymod):
        chunks.append("\n// ===== 自动补充: %s (%s) =====" % (mod, stamp))
        for k, v in bymod[mod]:
            chunks.append("%s=%s" % (k, v))

    enc = "utf-8-sig" if HAS_BOM else "utf-8"   # 保持与原文件一致
    with io.open(PACK, "w", encoding=enc, newline="\r\n") as w:
        w.write(text.rstrip("\n") + "\n" + "\n".join(chunks) + "\n")

    print("已写入: %s  (+%d 新增, %d 占位替换)" % (PACK, len(add), len(fix)))
    print("重启编辑器生效。若结果不满意, 用备份文件还原即可。")


if __name__ == "__main__":
    main()
