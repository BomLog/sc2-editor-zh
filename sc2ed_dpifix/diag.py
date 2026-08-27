#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断: 直接启动编辑器能否存活, 补丁是否影响存活。
用法: python diag.py            # 打补丁启动并探活
      python diag.py --nopatch  # 不打补丁, 仅直接启动并探活
"""
import ctypes, os, sys, time
from ctypes import wintypes

EDITOR = r"D:\StarCraft II\Support64\SC2Editor_x64.exe"
WORKDIR = os.path.dirname(EDITOR)
PATCHES = [(0x138880, b"\xff\xd0", b"\x90\x90"), (0x3245792, b"\xff\xd0", b"\x90\x90")]
CREATE_SUSPENDED = 4
PAGE_EXECUTE_READWRITE = 0x40
STILL_ACTIVE = 259

k = ctypes.WinDLL("kernel32", use_last_error=True)
nt = ctypes.WinDLL("ntdll")
try:
    k.SetConsoleOutputCP(65001); sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

class SI(ctypes.Structure):
    _fields_=[("cb",wintypes.DWORD),("r1",wintypes.LPWSTR),("d",wintypes.LPWSTR),("t",wintypes.LPWSTR),
    ("a",wintypes.DWORD*8),("f",wintypes.DWORD),("sw",wintypes.WORD),("cb2",wintypes.WORD),
    ("r2",ctypes.c_void_p),("i",wintypes.HANDLE),("o",wintypes.HANDLE),("e",wintypes.HANDLE)]
class PI(ctypes.Structure):
    _fields_=[("hP",wintypes.HANDLE),("hT",wintypes.HANDLE),("pid",wintypes.DWORD),("tid",wintypes.DWORD)]
class PBI(ctypes.Structure):
    _fields_=[("r1",ctypes.c_void_p),("peb",ctypes.c_void_p),("r2",ctypes.c_void_p*2),("upid",ctypes.c_void_p),("r3",ctypes.c_void_p)]

nopatch = "--nopatch" in sys.argv
os.environ["__COMPAT_LAYER"] = "GDIDPISCALING DPIUNAWARE"
si=SI(); si.cb=ctypes.sizeof(si); pi=PI()
cmd='"'+EDITOR+'"'
ok=k.CreateProcessW(ctypes.c_wchar_p(EDITOR),ctypes.c_wchar_p(cmd),None,None,False,
    CREATE_SUSPENDED,None,ctypes.c_wchar_p(WORKDIR),ctypes.byref(si),ctypes.byref(pi))
if not ok:
    print("CreateProcessW 失败", k.get_last_error()); sys.exit(1)
print(f"[+] pid={pi.pid}  ({'不打补丁' if nopatch else '打补丁'})")

if not nopatch:
    pbi=PBI(); rl=ctypes.c_ulong(0)
    nt.NtQueryInformationProcess(pi.hP,0,ctypes.byref(pbi),ctypes.sizeof(pbi),ctypes.byref(rl))
    base=ctypes.c_ulonglong(0); nr=ctypes.c_size_t(0)
    k.ReadProcessMemory(pi.hP,ctypes.c_void_p(pbi.peb+0x10),ctypes.byref(base),8,ctypes.byref(nr))
    print(f"[+] base={base.value:#x}")
    for rva,old,new in PATCHES:
        addr=base.value+rva; op=wintypes.DWORD(0)
        k.VirtualProtectEx(pi.hP,ctypes.c_void_p(addr),2,PAGE_EXECUTE_READWRITE,ctypes.byref(op))
        buf=(ctypes.c_ubyte*2).from_buffer_copy(new); w=ctypes.c_size_t(0)
        k.WriteProcessMemory(pi.hP,ctypes.c_void_p(addr),buf,2,ctypes.byref(w))
        k.VirtualProtectEx(pi.hP,ctypes.c_void_p(addr),2,op,ctypes.byref(op))
        print(f"    patched {addr:#x}")

k.ResumeThread(pi.hT)
print("[+] resumed, 探活 8 秒...")
code=wintypes.DWORD(0)
for i in range(16):
    time.sleep(0.5)
    k.GetExitCodeProcess(pi.hP,ctypes.byref(code))
    if code.value!=STILL_ACTIVE:
        c=code.value
        sc = c-0x100000000 if c>0x7fffffff else c
        print(f"[!] 进程已退出, 退出码={c:#x} ({sc})  用时~{(i+1)*0.5}s")
        break
else:
    print("[+] 8 秒仍存活 → 编辑器应已打开(检查任务栏/屏幕)。诊断进程结束不影响它。")
    try:
        shcore = ctypes.WinDLL("Shcore.dll")
        val = ctypes.c_int(-1)
        hr = shcore.GetProcessDpiAwareness(pi.hP, ctypes.byref(val))
        names = {0: "UNAWARE(✓ GDI缩放前提OK)", 1: "SYSTEM", 2: "PER-MONITOR"}
        print(f"[i] GetProcessDpiAwareness hr={hr:#x} value={val.value} "
              f"({names.get(val.value,'?')})")
    except Exception as e:
        print("[i] 查询 DPI awareness 失败:", e)
k.CloseHandle(pi.hT); k.CloseHandle(pi.hP)
