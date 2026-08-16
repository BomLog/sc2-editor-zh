#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
全类别草稿并入 OB 汉化包 ObjectStrings.txt —— 从 _draft\<Cat>.txt 读取并追加。

安全策略:
  · 默认 dry-run, 只报告将写入多少条, 不动文件; 要落盘须显式加 --apply
  · --apply 时先备份为 ObjectStrings.txt.bak.<时间戳>
  · 只追加「包里还没有的键」; 已有译文一律不覆盖(除非 --overwrite-placeholder)
  · 默认只并 high 置信度, --conf low,none 可放宽

用法:
  python l10n_merge_all.py                          # 预演(high)全类别
  python l10n_merge_all.py --apply                  # 落盘
  python l10n_merge_all.py --cat Actor Sound        # 只并指定类别
  python l10n_merge_all.py --conf high,low --apply  # 放宽到 low
"""
import argparse
import datetime
import glob
import io
import os
import re
import shutil

GAME = r"D:\StarCraft II"
PACK = os.path.join(GAME, "Editor", "LocalizedData", "ObjectStrings.txt")
DRAFT_DIR = r"e:\Code\sc2\Work\_draft"
HAS_BOM = False


def dec(b):
    for e in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return b.decode(e)
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", "replace")


def has_cjk(s):
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def read_drafts(cats_filter, conf_ok):
    """-> [(key, value, cat)] 全类别草稿."""
    rows = []
    for fp in sorted(glob.glob(os.path.join(DRAFT_DIR, "*.txt"))):
        cat = os.path.basename(fp)[:-4]
        if cats_filter and cat not in cats_filter:
            continue
        for line in io.open(fp, encoding="utf-8"):
            if not line.strip() or line.startswith("//"):
                continue
            body, _, tail = line.partition("\t")
            conf = tail.replace("//", "").strip() if tail else ""
            if conf and conf not in conf_ok:
                continue
            if "=" not in body:
                continue
            k, _, v = body.partition("=")
            k, v = k.strip(), v.strip()
            if v:
                rows.append((k, v, cat))
    return rows


def read_pack():
    raw = open(PACK, "rb").read()
    text = dec(raw).replace("\r\n", "\n").replace("\r", "\n")
    global HAS_BOM
    HAS_BOM = raw[:3] == b"\xef\xbb\xbf"
    cur = {}
    for line in text.splitlines():
        if "=" in line and not line.startswith("//"):
            k, _, v = line.partition("=")
            cur[k.strip()] = v.split("\t")[0].strip()
    return text, cur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真正写入(默认只预演)")
    ap.add_argument("--conf", default="high", help="并入哪些置信度, 逗号分隔")
    ap.add_argument("--cat", nargs="*", default=[], help="只并入指定类别")
    ap.add_argument("--overwrite-placeholder", action="store_true",
                    help="用草稿替换包里 id=id 形式的占位行")
    a = ap.parse_args()
    conf_ok = {c.strip() for c in a.conf.split(",") if c.strip()}
    cats_filter = set(a.cat) if a.cat else set()

    rows = read_drafts(cats_filter, conf_ok)
    text, cur = read_pack()

    add, fix, skip = [], [], 0
    for k, v, cat in rows:
        old = cur.get(k)
        if old is None:
            add.append((k, v, cat))
        elif not has_cjk(old) and a.overwrite_placeholder:
            fix.append((k, v, old))
        else:
            skip += 1

    cats_hit = sorted(set(c for _, _, c in add))
    print("草稿命中 %d 条 (置信度 %s%s)"
          % (len(rows), ",".join(sorted(conf_ok)),
             ", 类别=" + ",".join(cats_filter) if cats_filter else " 全部类别"))
    print("  新增        : %d (涉及 %d 个类别)" % (len(add), len(cats_hit)))
    print("  替换占位    : %d%s" % (len(fix),
          "" if a.overwrite_placeholder else " (未开启 --overwrite-placeholder)"))
    print("  跳过(已有译): %d" % skip)

    if not a.apply:
        print("\n[预演] 未写入任何文件。确认无误后加 --apply。")
        for k, v, cat in add[:15]:
            print("   + %s=%s" % (k, v))
        if len(add) > 15:
            print("   ... 等 %d 条" % (len(add) - 15))
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
            if "=" in line:
                k = line.partition("=")[0].strip()
                if k in want:
                    lines[i] = "%s=%s" % (k, want[k])
        text = "\n".join(lines)

    # 追加新增, 按类别分组
    chunks = []
    bycat = {}
    for k, v, cat in add:
        bycat.setdefault(cat, []).append((k, v))
    for cat in sorted(bycat, key=lambda c: -len(bycat[c])):
        chunks.append("\n// ===== 自动补充: %s (%d 条, %s) =====" % (cat, len(bycat[cat]), stamp))
        for k, v in bycat[cat]:
            chunks.append("%s=%s" % (k, v))

    enc = "utf-8-sig" if HAS_BOM else "utf-8"
    with io.open(PACK, "w", encoding=enc, newline="\r\n") as w:
        w.write(text.rstrip("\n") + "\n" + "\n".join(chunks) + "\n")

    print("已写入: %s  (+%d 新增, %d 占位替换)" % (PACK, len(add), len(fix)))
    print("涉及类别: %s" % ", ".join(cats_hit))
    print("重启编辑器生效。若结果不满意, 用备份文件还原即可。")


if __name__ == "__main__":
    main()
