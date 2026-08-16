from pathlib import Path
EXP = Path(r"E:\Code\sc2\Work\casc_export")

def has_cjk(s):
    for ch in s:
        if "\u3400" <= ch <= "\u9fff":
            return True
    return False

for p in sorted(EXP.glob("*.txt")):
    raw = p.read_bytes()
    # try utf-8-sig and gbk
    u = raw.decode("utf-8-sig", errors="replace")
    g = raw.decode("gbk", errors="replace")
    # count replacement chars and CJK
    u_rep = u.count("\ufffd")
    g_rep = g.count("\ufffd")
    u_cjk = sum(1 for ch in u if "\u3400" <= ch <= "\u9fff")
    g_cjk = sum(1 for ch in g if "\u3400" <= ch <= "\u9fff")
    print(f"{p.stem:35s} size={len(raw):8d}  utf8(rep={u_rep},cjk={u_cjk})  gbk(rep={g_rep},cjk={g_cjk})")
