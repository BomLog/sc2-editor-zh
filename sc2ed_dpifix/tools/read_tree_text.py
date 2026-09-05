"""Objective measurement: walk SysTreeView32 items of the SC2 editor and
classify visible text as Chinese / English / other via TVM_GETITEMW."""
import ctypes
import ctypes.wintypes as wintypes
import sys

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
# 64-bit safety: without these ctypes truncates handles/pointers to c_int
user32.SendMessageW.argtypes = [
    wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = ctypes.c_ssize_t
kernel32.VirtualAllocEx.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
kernel32.VirtualAllocEx.restype = ctypes.c_void_p
kernel32.VirtualFreeEx.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD]
kernel32.VirtualFreeEx.restype = wintypes.BOOL
kernel32.WriteProcessMemory.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t)]
kernel32.WriteProcessMemory.restype = wintypes.BOOL
kernel32.ReadProcessMemory.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t)]
kernel32.ReadProcessMemory.restype = wintypes.BOOL
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE

PID_TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 38628
PROCESS_RIGHTS = 0x1F0FFF  # PROCESS_ALL_ACCESS-ish (VM ops + read/write)
TV_FIRST = 0x1100
TVM_GETNEXTITEM = TV_FIRST + 10
TVM_GETITEMW = TV_FIRST + 62
TVM_GETCOUNT = TV_FIRST + 5
TVM_EXPAND = TV_FIRST + 2
WM_SETREDRAW = 0x000B
TVE_EXPAND = 0x0001
TVGN_ROOT = 0x0000
TVGN_NEXT = 0x0001
TVGN_CHILD = 0x0004

EXPAND_ALL = "--expand" in sys.argv
DUMP_EN = None
if "--dump-en" in sys.argv:
    DUMP_EN = sys.argv[sys.argv.index("--dump-en") + 1]
MAX_ITEMS = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 60000

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumChildWindows.argtypes = [wintypes.HWND, WNDENUMPROC, wintypes.LPARAM]


def window_pid(h):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
    return pid.value


def window_class(h):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(h, buf, 256)
    return buf.value


def window_text(h):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(h, buf, 256)
    return buf.value


def collect_treeviews():
    """Return {top_level_hwnd: [treeview_hwnds]} for the editor process."""
    tops = []
    result = {}

    @WNDENUMPROC
    def top_cb(h, l):
        if window_pid(h) == PID_TARGET and user32.IsWindowVisible(h):
            tops.append(h)
        return True
    user32.EnumWindows(top_cb, 0)

    for top in tops:
        trees = []

        @WNDENUMPROC
        def child_cb(h, l):
            if window_pid(h) == PID_TARGET and window_class(h) == "SysTreeView32":
                trees.append(h)
            return True
        user32.EnumChildWindows(top, child_cb, 0)
        if trees:
            result[top] = trees
    return result


# TVITEMW layout (x64): mask(4)+pad(4) hItem(8) state(4)+pad(4) stateMask(4)+pad(4)
# pszText(8) cchTextMax(4)+pad(4) iImage(4) iSelectedImage(4) cChildren(4) lParam(8)
TVITEMW_SIZE = 72
TEXT_MAX = 512


def read_tree_texts(hproc, htree, max_items=MAX_ITEMS):
    """Walk all items of htree, return list of unicode strings."""
    remote_tvitem = kernel32.VirtualAllocEx(
        hproc, None, TVITEMW_SIZE, 0x3000, 0x04)  # MEM_COMMIT|RESERVE, PAGE_READWRITE
    remote_text = kernel32.VirtualAllocEx(
        hproc, None, TEXT_MAX * 2, 0x3000, 0x04)
    if not remote_tvitem or not remote_text:
        raise OSError("VirtualAllocEx failed")

    class TVITEMW(ctypes.Structure):
        _fields_ = [
            ("mask", wintypes.UINT), ("hItem", ctypes.c_void_p),
            ("state", wintypes.UINT), ("stateMask", wintypes.UINT),
            ("pszText", ctypes.c_void_p), ("cchTextMax", ctypes.c_int),
            ("iImage", ctypes.c_int), ("iSelectedImage", ctypes.c_int),
            ("cChildren", ctypes.c_int), ("lParam", ctypes.c_void_p),
        ]

    def send(msg, wp, lp):
        r = user32.SendMessageW(htree, msg, wp, lp)
        return 0 if r is None else r

    count = send(TVM_GETCOUNT, 0, 0)
    texts = []

    def get_item_text(hitem):
        it = TVITEMW()
        it.mask = 0x0001  # TVIF_TEXT
        it.hItem = ctypes.c_void_p(hitem)
        it.pszText = ctypes.c_void_p(remote_text)
        it.cchTextMax = TEXT_MAX
        buf = bytes(it)
        written = ctypes.c_size_t(0)
        kernel32.WriteProcessMemory(hproc, remote_tvitem, buf, len(buf), ctypes.byref(written))
        ok = send(TVM_GETITEMW, 0, remote_tvitem)
        if not ok:
            return None
        raw = (ctypes.c_ushort * TEXT_MAX)()
        read = ctypes.c_size_t(0)
        kernel32.ReadProcessMemory(hproc, remote_text, raw, TEXT_MAX * 2, ctypes.byref(read))
        n = 0
        while n < TEXT_MAX and raw[n] != 0:
            n += 1
        return "".join(chr(c) for c in raw[:n])

    def walk(parent, depth, seen):
        if EXPAND_ALL and depth <= 10:
            send(TVM_EXPAND, TVE_EXPAND, parent)  # editor populates children lazily
        hitem = send(TVM_GETNEXTITEM, TVGN_CHILD, parent)
        while hitem and len(texts) < max_items and hitem not in seen:
            seen.add(hitem)
            t = get_item_text(hitem)
            if t is not None:
                texts.append(t)
            if depth < 12:
                walk(hitem, depth + 1, seen)
            hitem = send(TVM_GETNEXTITEM, TVGN_NEXT, hitem)

    seen = set()
    if EXPAND_ALL:
        send(WM_SETREDRAW, 0, 0)  # speed up bulk expansion
    root = send(TVM_GETNEXTITEM, TVGN_ROOT, 0)
    while root and len(texts) < max_items and root not in seen:
        seen.add(root)
        if EXPAND_ALL:
            send(TVM_EXPAND, TVE_EXPAND, root)
        t = get_item_text(root)
        if t is not None:
            texts.append(t)
        walk(root, 1, seen)
        root = send(TVM_GETNEXTITEM, TVGN_NEXT, root)
    if EXPAND_ALL:
        send(WM_SETREDRAW, 1, 0)

    kernel32.VirtualFreeEx(hproc, remote_tvitem, 0, 0x8000)
    kernel32.VirtualFreeEx(hproc, remote_text, 0, 0x8000)
    return count, texts


def classify(s):
    cjk = sum(1 for ch in s if 0x4E00 <= ord(ch) <= 0x9FFF or 0x3000 <= ord(ch) <= 0x303F)
    if cjk > 0:
        return "zh"
    if s and all(ord(ch) < 128 for ch in s):
        return "en"
    return "other"


def main():
    trees_by_top = collect_treeviews()
    hproc = kernel32.OpenProcess(PROCESS_RIGHTS, False, PID_TARGET)
    if not hproc:
        print(f"OpenProcess({PID_TARGET}) failed err={kernel32.GetLastError()}")
        return 1
    grand = {"zh": 0, "en": 0, "other": 0}
    en_all = []
    for top, trees in trees_by_top.items():
        title = window_text(top)
        for htree in trees:
            declared, texts = read_tree_texts(hproc, htree)
            tally = {"zh": 0, "en": 0, "other": 0}
            for t in texts:
                tally[classify(t)] += 1
                if classify(t) == "en" and len(t.strip()) > 2:
                    en_all.append(t)
            for k in grand:
                grand[k] += tally[k]
            print(f"[{title[:40]}] tree=0x{htree:X} declared={declared} walked={len(texts)} "
                  f"zh={tally['zh']} en={tally['en']} other={tally['other']}")
    total = sum(grand.values())
    print(f"\nTOTAL: {total} items | zh={grand['zh']} en={grand['en']} other={grand['other']}")
    if total:
        print(f"Chinese: {grand['zh']/total*100:.1f}%  English: {grand['en']/total*100:.1f}%")
    if DUMP_EN:
        unique = sorted(set(t.strip() for t in en_all if t.strip()))
        with open(DUMP_EN, "w", encoding="utf-8") as fh:
            fh.write("\n".join(unique))
        print(f"\ndumped {len(unique)} unique English strings -> {DUMP_EN}")
    elif en_all:
        print("\nEnglish samples:")
        for s in sorted(set(en_all))[:25]:
            print(f"  {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
