import ctypes, json, subprocess, time
from ctypes import wintypes
from pathlib import Path

class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wintypes.DWORD), ("PartitionId", wintypes.WORD),
                ("RegionSize", ctypes.c_size_t), ("State", wintypes.DWORD),
                ("Protect", wintypes.DWORD), ("Type", wintypes.DWORD)]

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.OpenProcess.restype = wintypes.HANDLE
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.ReadProcessMemory.restype = wintypes.BOOL

exe = r"D:\StarCraft II\Support64\SC2Editor_x64.exe"
p = subprocess.Popen([exe], cwd=r"D:\StarCraft II")
result = {"pid": p.pid, "alive_before_scan": False, "hits": {}, "regions": 0, "bytes": 0}
try:
    time.sleep(20)
    result["alive_before_scan"] = p.poll() is None
    if result["alive_before_scan"]:
        h = k32.OpenProcess(0x0410, False, p.pid)
        needles = {}
        for text in ["演算体 - ACss", "默认武器", "潜地中", "正在飞行"]:
            needles[text + " [utf8]"] = text.encode("utf-8")
        hits = {k: [] for k in needles}
        addr = 0
        mbi = MBI()
        while addr < 0x7FFFFFFFFFFF:
            n = k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi))
            if not n:
                break
            base = int(mbi.BaseAddress or 0)
            size = int(mbi.RegionSize)
            nxt = base + size
            if nxt <= addr:
                break
            if mbi.State == 0x1000 and not (mbi.Protect & 0x101) and size > 0:
                off = 0
                while off < size:
                    take = min(8 * 1024 * 1024, size - off)
                    buf = ctypes.create_string_buffer(take)
                    got = ctypes.c_size_t()
                    if k32.ReadProcessMemory(h, ctypes.c_void_p(base + off), buf, take, ctypes.byref(got)) and got.value:
                        data = buf.raw[:got.value]
                        result["bytes"] += got.value
                        for key, needle in needles.items():
                            pos = data.find(needle)
                            if pos >= 0 and len(hits[key]) < 3:
                                hits[key].append(hex(base + off + pos))
                    off += take
                    if take == 0:
                        break
                result["regions"] += 1
            addr = nxt
        k32.CloseHandle(h)
        result["hits"] = hits
finally:
    if p.poll() is None:
        p.terminate()
        try:
            p.wait(5)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait(5)
    result["exit_code_after_test"] = p.returncode
    Path(r"E:\Code\sc2\Work\verify_actor_fix.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
