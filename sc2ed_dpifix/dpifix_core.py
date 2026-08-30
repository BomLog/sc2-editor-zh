#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SC2 编辑器 DPI 修复 —— 补丁内核 (被 GUI 复用)。
挂起启动 SC2Editor_x64.exe -> 读 PEB 真实基址(ASLR) ->
两处运行时 DPI-aware 调用 (call rax = FF D0) NOP 成 90 90 -> 恢复运行。
清晰模式: 启动前给"编辑器 exe 完整路径"写注册表 AppCompatFlags\\Layers
= GDIDPISCALING(系统增强/矢量缩放,清晰),启动后随即删除(热切换);
按路径生效 -> 游戏 exe 路径不同,绝不受影响(不同于环境变量会被子进程继承)。
不修改编辑器程序文件；汉化资源会先备份再同步到 Editor 目录。
"""
import ctypes
import hashlib
import json
import lzma
import os
import shutil
import string
import sys
import tempfile
import threading
import time
import winreg
from ctypes import wintypes

PATCHES = [
    (0x138880, b"\xff\xd0", b"\x90\x90"),   # SetProcessDpiAwareness(2)  (旧版, 仅作兜底)
    (0x3245792, b"\xff\xd0", b"\x90\x90"),  # SetProcessDPIAware()       (旧版, 仅作兜底)
]
# 版本无关定位: 运行时按字符串锚定两处 DPI call rax(见 _find_dpi_sites), 不依赖固定 RVA。
DPI_STRINGS = [b"SetProcessDpiAwareness\x00", b"SetProcessDPIAware\x00"]
# 兜底: 已见过的各版本 RVA(扫描失败时按此尝试, 且仅当该处字节为 FF D0 才补)。
KNOWN_DPI_RVAS = [0x138880, 0x138760, 0x3245792, 0x32331b2]
REL = os.path.join("Support64", "SC2Editor_x64.exe")

# 注册表兼容层: "系统增强" DPI 缩放(GDI 矢量缩放, 比纯位图清晰)
LAYERS_KEY = r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"
COMPAT_VALUE = "~ GDIDPISCALING DPIUNAWARE"

CREATE_SUSPENDED = 0x00000004
PAGE_EXECUTE_READWRITE = 0x40
TH32CS_SNAPPROCESS = 0x00000002
MAX_PATH = 260
MEM_COMMIT_RESERVE = 0x3000               # MEM_COMMIT | MEM_RESERVE
MEM_RELEASE = 0x8000
WAIT_OBJECT_0 = 0
# PMv2 "两全" 模式: 强制 Per-Monitor-V2 awareness, 让系统自动缩放对话框/通用控件字体
# (PMv1=SetProcessDpiAwareness(2) 不自动缩放对话框 -> 溢出; PMv2 会 -> 目标既清晰又不溢出)。
DPI_PER_MONITOR_AWARE_V2 = (1 << 64) - 4   # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 == (HANDLE)-4
DPI_UNAWARE_GDISCALED = (1 << 64) - 5       # DPI_AWARENESS_CONTEXT_UNAWARE_GDISCALED == (HANDLE)-5 ("系统增强" GDI 矢量缩放, 需 Win10 1809+)

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
ntdll = ctypes.WinDLL("ntdll")
user32 = ctypes.WinDLL("user32", use_last_error=True)

# 64 位指针不能让 ctypes 默认按 int(截断成 32 位)返回/传参, 显式声明类型。
kernel32.VirtualAllocEx.restype = wintypes.LPVOID
kernel32.VirtualAllocEx.argtypes = [wintypes.HANDLE, wintypes.LPVOID, ctypes.c_size_t,
                                    wintypes.DWORD, wintypes.DWORD]
kernel32.VirtualFreeEx.restype = wintypes.BOOL
kernel32.VirtualFreeEx.argtypes = [wintypes.HANDLE, wintypes.LPVOID, ctypes.c_size_t,
                                   wintypes.DWORD]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetProcAddress.restype = ctypes.c_void_p
kernel32.GetProcAddress.argtypes = [wintypes.HMODULE, ctypes.c_char_p]
kernel32.CreateRemoteThread.restype = wintypes.HANDLE
kernel32.CreateRemoteThread.argtypes = [
    wintypes.HANDLE, wintypes.LPVOID, ctypes.c_size_t, ctypes.c_void_p,
    wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
]
kernel32.WriteProcessMemory.restype = wintypes.BOOL
kernel32.WriteProcessMemory.argtypes = [
    wintypes.HANDLE, wintypes.LPVOID, wintypes.LPCVOID, ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
kernel32.WaitForSingleObject.restype = wintypes.DWORD
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.GetExitCodeThread.restype = wintypes.BOOL
kernel32.GetExitCodeThread.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]

L10N_DLL = "SC2EditorDependencyL10n.dll"
L10N_TABLE = "OfficialDependencyNames.tsv"
L10N_RESOURCE_TABLE = "OfficialResourceNames.tsv"
L10N_LOG = "SC2EditorDependencyL10n.log"
L10N_BUNDLE_DIR = "bundle"
L10N_BUNDLE_MANIFEST = "manifest.json"
L10N_STASH_DIR = ".sc2ed_dpifix_localization_disabled"
L10N_STASH_MANIFEST = "manifest.json"
L10N_FILES = (
    "EditorCatalogStrings.txt",
    "EditorCategoryStrings.txt",
    "EditorStrings.txt",
    os.path.join("LocalizedData", "GameStrings.txt"),
    os.path.join("LocalizedData", "ObjectStrings.txt"),
    os.path.join("LocalizedData", "TriggerStrings.txt"),
    os.path.join("LocalizedData", "GameStringsProduct.txt"),
    os.path.join("LocalizedData", "ObjectStringsProduct.txt"),
)
L10N_RESOURCES = (L10N_DLL, L10N_TABLE, L10N_RESOURCE_TABLE) + L10N_FILES


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.c_void_p), ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]


class PROCESS_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [("Reserved1", ctypes.c_void_p), ("PebBaseAddress", ctypes.c_void_p),
                ("Reserved2", ctypes.c_void_p * 2), ("UniqueProcessId", ctypes.c_void_p),
                ("Reserved3", ctypes.c_void_p)]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_void_p),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * MAX_PATH)]


class PatchError(Exception):
    pass


def find_editor():
    """自动定位银河编辑器 SC2Editor_x64.exe: 注册表 -> 常见路径 -> 全盘符扫描。"""
    seen = []

    def add(base):
        if not base:
            return None
        p = base if base.lower().endswith("sc2editor_x64.exe") else os.path.join(base, REL)
        if os.path.isfile(p) and p not in seen:
            seen.append(p)
            return p
        return None

    try:
        import winreg
        reg_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\StarCraft II", "InstallLocation"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\StarCraft II", "InstallLocation"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Blizzard Entertainment\StarCraft II", "InstallPath"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Blizzard Entertainment\StarCraft II", "InstallPath"),
        ]
        for hk, sub, val in reg_keys:
            try:
                with winreg.OpenKey(hk, sub) as k:
                    loc, _ = winreg.QueryValueEx(k, val)
                    r = add(loc)
                    if r:
                        return r
            except OSError:
                pass
    except Exception:
        pass

    for c in [r"C:\Program Files (x86)\StarCraft II", r"C:\Program Files\StarCraft II",
              r"D:\StarCraft II", r"E:\StarCraft II", r"F:\StarCraft II", r"G:\StarCraft II",
              r"D:\Program Files (x86)\StarCraft II", r"E:\Program Files (x86)\StarCraft II"]:
        r = add(c)
        if r:
            return r

    for d in string.ascii_uppercase:
        root = f"{d}:\\"
        if not os.path.isdir(root):
            continue
        for sub in ("StarCraft II", r"Program Files\StarCraft II",
                    r"Program Files (x86)\StarCraft II", r"Games\StarCraft II"):
            r = add(os.path.join(root, sub))
            if r:
                return r
    return None


def is_editor_running():
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap in (-1, 0xFFFFFFFFFFFFFFFF):
        return False
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        ok = kernel32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            if entry.szExeFile.lower() == "sc2editor_x64.exe":
                return True
            ok = kernel32.Process32NextW(snap, ctypes.byref(entry))
        return False
    finally:
        kernel32.CloseHandle(snap)


def _image_base(hproc):
    pbi = PROCESS_BASIC_INFORMATION()
    rl = ctypes.c_ulong(0)
    if ntdll.NtQueryInformationProcess(hproc, 0, ctypes.byref(pbi),
                                       ctypes.sizeof(pbi), ctypes.byref(rl)) != 0:
        raise PatchError("读取进程信息失败 (NtQueryInformationProcess)")
    base = ctypes.c_ulonglong(0)
    if not kernel32.ReadProcessMemory(hproc, ctypes.c_void_p(pbi.PebBaseAddress + 0x10),
                                      ctypes.byref(base), 8, ctypes.byref(ctypes.c_size_t(0))):
        raise PatchError("读取镜像基址失败 (PEB)")
    return base.value


def _rpm(hproc, addr, size):
    buf = (ctypes.c_ubyte * size)()
    if not kernel32.ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, size,
                                      ctypes.byref(ctypes.c_size_t(0))):
        raise PatchError(f"读内存失败 @ {addr:#x}")
    return bytes(buf)


def _wpm(hproc, addr, data):
    old = wintypes.DWORD(0)
    if not kernel32.VirtualProtectEx(hproc, ctypes.c_void_p(addr), len(data),
                                     PAGE_EXECUTE_READWRITE, ctypes.byref(old)):
        raise PatchError(f"改内存保护失败 @ {addr:#x}")
    buf = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    ok = kernel32.WriteProcessMemory(hproc, ctypes.c_void_p(addr), buf, len(data),
                                     ctypes.byref(ctypes.c_size_t(0)))
    kernel32.VirtualProtectEx(hproc, ctypes.c_void_p(addr), len(data), old, ctypes.byref(old))
    if not ok:
        raise PatchError(f"写内存失败 @ {addr:#x}")


def _read_range(hproc, addr, size, chunk=0x100000):
    """分块 ReadProcessMemory 一段区间, 返回读到的字节(读失败即止)。"""
    out = bytearray()
    off = 0
    while off < size:
        n = min(chunk, size - off)
        buf = (ctypes.c_ubyte * n)()
        got = ctypes.c_size_t(0)
        if not kernel32.ReadProcessMemory(hproc, ctypes.c_void_p(addr + off), buf, n,
                                          ctypes.byref(got)):
            break
        out += bytes(buf[:got.value])
        if got.value < n:
            break
        off += n
    return bytes(out)


def _pe_sections(hproc, base):
    """解析已映射镜像的节表, 返回 {name: (va, size)}。"""
    hdr = _read_range(hproc, base, 0x2000)
    if hdr[:2] != b"MZ":
        return {}
    e_lfanew = int.from_bytes(hdr[0x3c:0x40], "little")
    nt = e_lfanew
    if hdr[nt:nt + 4] != b"PE\x00\x00":
        return {}
    num_sec = int.from_bytes(hdr[nt + 6:nt + 8], "little")
    size_opt = int.from_bytes(hdr[nt + 20:nt + 22], "little")
    sec_off = nt + 24 + size_opt
    secs = {}
    for i in range(num_sec):
        s = hdr[sec_off + i * 40: sec_off + i * 40 + 40]
        if len(s) < 40:
            break
        name = s[:8].rstrip(b"\x00").decode("latin1", "ignore")
        vsize = int.from_bytes(s[8:12], "little")
        vaddr = int.from_bytes(s[12:16], "little")
        rawsize = int.from_bytes(s[16:20], "little")
        secs[name] = (base + vaddr, max(vsize, rawsize))
    return secs


def _entry_point(hproc, base):
    """返回主模块入口点绝对 VA (base + OptionalHeader.AddressOfEntryPoint)。"""
    hdr = _read_range(hproc, base, 0x400)
    if hdr[:2] != b"MZ":
        raise PatchError("PE 头无效, 无法定位入口点")
    nt = int.from_bytes(hdr[0x3c:0x40], "little")
    if hdr[nt:nt + 4] != b"PE\x00\x00":
        raise PatchError("PE 签名无效, 无法定位入口点")
    aoep = int.from_bytes(hdr[nt + 40:nt + 44], "little")  # OptionalHeader+16
    return base + aoep


def _inject_dpi_context(hproc, base, ctx_val, ctx_name, log=lambda m: None):
    """入口点注入 SetProcessDpiAwarenessContext(ctx_val) —— 不改磁盘、纯内存。

    ctx_val: DPI_PER_MONITOR_AWARE_V2(-4, 物理像素清晰) 或
             DPI_UNAWARE_GDISCALED(-5, "系统增强" GDI 矢量缩放)。
    做法(挂起态, 主线程未跑):
      1. 取 user32!SetProcessDpiAwarenessContext 的 VA。已知系统 DLL 每次开机 ASLR
         基址【全系统统一】, 故本进程里解析到的 VA == 目标进程里的 VA。
      2. 在目标入口点前挂一段 stub: 入口点前 12 字节改成 `mov rax,stub; jmp rax`,
         stub 里 `SetProcessDpiAwarenessContext(ctx_val)` -> 还原入口点原字节 -> 跳回。
         入口点由 ntdll 加载器在【静态导入(含 user32)全部加载完】之后才执行,
         故 stub 运行时 user32 必已就位, 且早于编辑器自己声明 DPI 的代码
         (awareness set-once: 先注入者胜, 编辑器随后的 SetProcessDpiAware* 无效)。
    失败(如老系统无此 API)抛 PatchError, 由上层回退到位图模式。
    """
    fn = getattr(user32, "SetProcessDpiAwarenessContext", None)
    if fn is None:
        raise PatchError("本系统 user32 无 SetProcessDpiAwarenessContext (需 Win10 1703+)")
    if ctypes.sizeof(ctypes.c_void_p) != 8:
        # 依赖"系统 DLL 每次开机全系统同一 ASLR 基址": 仅当本进程也是 64 位, 解析到的
        # user32 VA 才与 64 位目标一致。32 位 Python 下此假设不成立, 拒绝以免注入到错地址。
        raise PatchError("入口点 DPI 注入需 64 位 Python(共享 user32 基址假设)")
    fn_addr = ctypes.cast(fn, ctypes.c_void_p).value

    entry = _entry_point(hproc, base)
    orig12 = _rpm(hproc, entry, 12)

    stub_addr = kernel32.VirtualAllocEx(hproc, None, 256, MEM_COMMIT_RESERVE,
                                        PAGE_EXECUTE_READWRITE)
    if not stub_addr:
        raise PatchError(f"VirtualAllocEx 失败 err={ctypes.get_last_error()}")

    ctx = ctx_val & ((1 << 64) - 1)
    stub = (
        b"\x48\x83\xEC\x28"                              # sub  rsp, 0x28  (对齐+影子空间)
        b"\x48\xB9" + ctx.to_bytes(8, "little") +        # mov  rcx, ctx_val(-4 PMv2 / -5 GDIScaled)
        b"\x48\xB8" + fn_addr.to_bytes(8, "little") +    # mov  rax, SetProcessDpiAwarenessContext
        b"\xFF\xD0"                                      # call rax
        b"\x48\x83\xC4\x28"                              # add  rsp, 0x28
        b"\x48\xB8" + entry.to_bytes(8, "little") +      # mov  rax, entry
        b"\x48\xB9" + orig12[0:8] +                      # mov  rcx, orig[0:8]
        b"\x48\x89\x08"                                  # mov  [rax], rcx
        b"\xB9" + orig12[8:12] +                         # mov  ecx, orig[8:12]
        b"\x89\x48\x08"                                  # mov  [rax+8], ecx
        b"\xFF\xE0"                                      # jmp  rax  (回到入口点原码)
    )
    _wpm(hproc, stub_addr, stub)

    # 入口点前 12 字节 -> mov rax,stub; jmp rax。入口点所在页需可写(stub 稍后要还原它),
    # 故常驻 RWX 不再恢复原保护。
    old = wintypes.DWORD(0)
    if not kernel32.VirtualProtectEx(hproc, ctypes.c_void_p(entry), 16,
                                     PAGE_EXECUTE_READWRITE, ctypes.byref(old)):
        raise PatchError(f"入口点改保护失败 @ {entry:#x}")
    patch = b"\x48\xB8" + stub_addr.to_bytes(8, "little") + b"\xFF\xE0"
    buf = (ctypes.c_ubyte * len(patch)).from_buffer_copy(patch)
    if not kernel32.WriteProcessMemory(hproc, ctypes.c_void_p(entry), buf, len(patch),
                                       ctypes.byref(ctypes.c_size_t(0))):
        raise PatchError(f"入口点补丁写入失败 @ {entry:#x}")
    log(f"  · {ctx_name} stub @ {stub_addr:#x} · 入口点 {entry:#x} 已挂钩")


def _force_pmv2(hproc, base, log=lambda m: None):
    """强制 Per-Monitor-V2 awareness(入口点注入 -4, 物理像素清晰)。"""
    _inject_dpi_context(hproc, base, DPI_PER_MONITOR_AWARE_V2, "PMv2", log)


def _find_dpi_sites(hproc, base, log=lambda m: None):
    """版本无关: 按字符串锚定两处 DPI `call rax`, 返回待 NOP 的绝对地址列表。
    思路: 定位 "SetProcessDpiAwareness"/"SetProcessDPIAware" 字符串 VA ->
    在 .text 里找引用它的 `lea rdx,[rip+disp]`(48 8D 15) -> 其后 0x80 内首个 FF D0。"""
    secs = _pe_sections(hproc, base)
    text = secs.get(".text")
    if not text:
        return []
    text_va, text_sz = text
    text_buf = _read_range(hproc, text_va, text_sz)

    # 1) 找字符串 VA: 优先 .rdata, 未命中再扫其余非代码节
    str_va = {}
    order = [n for n in (".rdata", ".rodata", ".data") if n in secs]
    order += [n for n in secs if n not in order and n != ".text"]
    for sname in order:
        if all(t in str_va for t in DPI_STRINGS):
            break
        sva, ssz = secs[sname]
        blob = _read_range(hproc, sva, ssz)
        for t in DPI_STRINGS:
            if t not in str_va:
                idx = blob.find(t)
                if idx >= 0:
                    str_va[t] = sva + idx

    # 2) 每个字符串 -> lea rdx,[rip+disp] 引用点 -> 向后首个 FF D0
    sites = []
    for t in DPI_STRINGS:
        target = str_va.get(t)
        if target is None:
            log(f"  · 未找到字符串 {t.rstrip(bytes([0])).decode()}")
            continue
        pos = 0
        hit = None
        while True:
            i = text_buf.find(b"\x48\x8d\x15", pos)
            if i < 0:
                break
            disp = int.from_bytes(text_buf[i + 3:i + 7], "little", signed=True)
            if text_va + i + 7 + disp == target:            # rip 相对目标 == 字符串
                j = text_buf.find(b"\xff\xd0", i, i + 0x80)  # 其后 call rax
                if j >= 0:
                    hit = text_va + j
                break
            pos = i + 1
        if hit:
            sites.append(hit)
            log(f"  · {t.rstrip(bytes([0])).decode()} -> call rax @ {hit:#x} (RVA {hit-base:#x})")
        else:
            log(f"  · {t.rstrip(bytes([0])).decode()} 调用点未定位")
    return sites


# ---- 清晰适配: 字体工厂分母补丁(版本无关) ----------------------------------
# 编辑器全 UI 字体都过一个字体工厂 sub_141D36230, 核心:
#   lfHeight = -MulDiv(点数, GetDeviceCaps(DC, LOGPIXELSY=90), 72)
# 那个 72(=0x48)是全 UI 字号的唯一总闸门。IDA 全盘只 2 处这种"点->像素"换算
# (字体工厂 + 点->像素辅助 sub_141D3B780), 定式均为:
#   41 B8 48 00 00 00   mov r8d, 48h      ; nDenominator = 72
#   8B D0               mov edx, eax      ; nNumerator   = GetDeviceCaps 返回的 DPI
#   FF 15 ..            call cs:MulDiv
# 改分母 -> 一刀统一缩放所有字体, 进程仍原生 DPI-aware => D3D9 按物理像素清晰渲染。
FONT_DENOM_PATTERN = b"\x41\xb8\x48\x00\x00\x00\x8b\xd0\xff\x15"
FONT_DENOM_OFF = 2                         # 立即数(0x48)在定式中的字节偏移


def font_scale_to_denom(pct):
    """字体缩放百分比 -> MulDiv 分母。pct=100 即原生真实 DPI(=72);
    pct 越小字越小(分母越大), 用来把字缩到贴合欠缩放的控件框。"""
    try:
        pct = int(round(float(pct)))
    except (TypeError, ValueError):
        pct = 85
    pct = max(30, min(200, pct))
    denom = int(round(72.0 / (pct / 100.0)))
    return max(1, min(255, denom))


def _patch_font_denom(hproc, base, denom, log=lambda m: None):
    """把字体工厂里 MulDiv(点数, DPI, 72) 的分母 72 改成 denom, 统一缩放全 UI 字体。
    版本无关: 在 .text 扫上面的定式。只改确为 0x48 的那一字节。返回改动处数。"""
    secs = _pe_sections(hproc, base)
    text = secs.get(".text")
    if not text:
        return 0
    text_va, text_sz = text
    buf = _read_range(hproc, text_va, text_sz)
    n = 0
    pos = 0
    while True:
        i = buf.find(FONT_DENOM_PATTERN, pos)
        if i < 0:
            break
        addr = text_va + i + FONT_DENOM_OFF
        if _rpm(hproc, addr, 1) == b"\x48":     # 安全: 只改立即数确为 72 的
            _wpm(hproc, addr, bytes([denom]))
            n += 1
            log(f"  · 字体分母 72->{denom} @ {addr:#x} (RVA {addr-base:#x})")
        pos = i + 1
    return n


def _set_compat_layer(path):
    """给 exe 完整路径写"系统增强 DPI 缩放"兼容层。按路径生效, 游戏不受影响。"""
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, LAYERS_KEY, 0,
                                winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, path, 0, winreg.REG_SZ, COMPAT_VALUE)
        return True
    except OSError:
        return False


def _del_compat_layer(path):
    """删除该 exe 的兼容层键 -> 普通快捷方式启动回到原样(热切换)。"""
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, LAYERS_KEY, 0,
                                winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, path)
    except OSError:
        pass


def _resource_base():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def app_version():
    try:
        with open(os.path.join(_resource_base(), "VERSION"), encoding="ascii") as handle:
            return handle.read().strip() or "dev"
    except OSError:
        return "dev"


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.digest()


def _sha256_hex(path):
    return _sha256(path).hex()


def _next_backup_path(target):
    version = app_version().replace("/", "_").replace("\\", "_")
    base = f"{target}.bak.sc2ed_dpifix_{version}"
    candidate = base
    suffix = 1
    while os.path.exists(candidate):
        candidate = f"{base}.{suffix}"
        suffix += 1
    return candidate


def _hook_version_marker(version=None):
    version = version or app_version()
    return f"SC2ED_DPIFIX_L10N_HOOK_VERSION={version}".encode("ascii")


def _valid_hook_dll(path, version=None):
    try:
        with open(path, "rb") as handle:
            blob = handle.read()
    except OSError:
        return False
    markers = (
        b"SC2L10nGetNameCount",
        b"SC2L10nGetResourceNameCount",
        b"SC2L10nGetHookVersion",
        _hook_version_marker(version),
        "OfficialDependencyNames.tsv".encode("utf-16le"),
        "OfficialResourceNames.tsv".encode("utf-16le"),
        b"loaded official dependency names",
        b"loaded official resource names",
    )
    return blob.startswith(b"MZ") and all(marker in blob for marker in markers)


def _external_resource_matches(source, target):
    if os.path.basename(target).lower() == L10N_DLL.lower():
        return _valid_hook_dll(source) and _valid_hook_dll(target)
    try:
        return os.path.getsize(source) == os.path.getsize(target) and _sha256(source) == _sha256(target)
    except OSError:
        return False


def _resource_target_matches(record, target):
    if os.path.basename(target).lower() == L10N_DLL.lower():
        return _valid_hook_dll(target)
    try:
        return (
            os.path.getsize(target) == record["size"]
            and _sha256_hex(target) == record["sha256"]
        )
    except OSError:
        return False


def _load_localization_bundle(bundle_dir=None):
    bundle_dir = bundle_dir or os.path.join(_resource_base(), "l10n", L10N_BUNDLE_DIR)
    manifest_path = os.path.join(bundle_dir, L10N_BUNDLE_MANIFEST)
    try:
        with open(manifest_path, encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError) as exc:
        raise PatchError(f"无法读取汉化压缩包清单: {exc}") from exc
    if manifest.get("format") != 1 or manifest.get("version") != app_version():
        raise PatchError("汉化压缩包版本与启动器不一致，请重新构建或下载完整程序。")
    records = {}
    for raw in manifest.get("resources", []):
        relative = str(raw.get("path", "")).replace("/", os.sep)
        blob = str(raw.get("blob", ""))
        digest = str(raw.get("sha256", "")).lower()
        size = raw.get("size")
        if (
            relative not in L10N_RESOURCES
            or relative in records
            or not isinstance(size, int)
            or size < 0
            or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
            or blob != f"{digest}.xz"
            or os.path.basename(blob) != blob
        ):
            raise PatchError("汉化压缩包清单包含无效资源记录。")
        records[relative] = {
            "path": relative,
            "blob": blob,
            "sha256": digest,
            "size": size,
        }
    if set(records) != set(L10N_RESOURCES):
        raise PatchError("汉化压缩包资源不完整，请重新构建或下载完整程序。")
    return bundle_dir, records


def _extract_bundle_resource(bundle_dir, record, output_dir):
    source = os.path.join(bundle_dir, record["blob"])
    target = os.path.join(output_dir, record["sha256"])
    digest = hashlib.sha256()
    size = 0
    try:
        with lzma.open(source, "rb") as packed, open(target, "wb") as unpacked:
            while True:
                block = packed.read(1024 * 1024)
                if not block:
                    break
                unpacked.write(block)
                digest.update(block)
                size += len(block)
    except (OSError, lzma.LZMAError) as exc:
        raise PatchError(f"汉化资源解压失败: {record['path']}: {exc}") from exc
    if size != record["size"] or digest.hexdigest() != record["sha256"]:
        try:
            os.remove(target)
        except OSError:
            pass
        raise PatchError(f"汉化资源解压校验失败: {record['path']}")
    return target


def _release_localization_file(source, target):
    """Validate an external resource and atomically release the bundle if needed."""
    if not os.path.isfile(source):
        raise PatchError(f"汉化资源缺失: {source}")
    if os.path.isfile(target):
        if _external_resource_matches(source, target):
            temporary = target + ".sc2ed_dpifix.tmp"
            try:
                os.remove(temporary)
            except FileNotFoundError:
                pass
            except OSError:
                pass
            return "valid"
        shutil.copy2(target, _next_backup_path(target))
        status = "replaced"
    elif os.path.exists(target):
        raise PatchError(f"汉化目标不是普通文件: {target}")
    else:
        status = "released"
    os.makedirs(os.path.dirname(target), exist_ok=True)
    temporary = target + ".sc2ed_dpifix.tmp"
    shutil.copy2(source, temporary)
    os.replace(temporary, target)
    if not _external_resource_matches(source, target):
        raise PatchError(f"汉化资源释放后校验失败: {target}")
    return status


def _prepare_localization(editor_path, log=lambda m: None):
    editor_dir = os.path.join(os.path.dirname(os.path.dirname(editor_path)), "Editor")
    if localization_is_uninstalled(editor_path):
        raise PatchError("汉化当前处于暂时卸载状态，请先点击“恢复汉化”。")
    statuses = {"valid": 0, "released": 0, "replaced": 0}
    bundle_path = os.path.join(_resource_base(), "l10n", L10N_BUNDLE_DIR)
    if os.path.isfile(os.path.join(bundle_path, L10N_BUNDLE_MANIFEST)):
        bundle_dir, records = _load_localization_bundle(bundle_path)
        with tempfile.TemporaryDirectory(prefix="sc2ed_dpifix_l10n_") as extracted:
            for relative in L10N_RESOURCES:
                target = os.path.join(editor_dir, relative)
                record = records[relative]
                if _resource_target_matches(record, target):
                    status = "valid"
                else:
                    source = _extract_bundle_resource(bundle_dir, record, extracted)
                    status = _release_localization_file(source, target)
                statuses[status] += 1
    else:
        source = os.path.join(_resource_base(), "l10n")
        for relative in L10N_RESOURCES:
            source_path = (
                os.path.join(source, relative)
                if relative in (L10N_DLL, L10N_TABLE, L10N_RESOURCE_TABLE)
                else os.path.join(source, "Editor", relative)
            )
            status = _release_localization_file(
                source_path, os.path.join(editor_dir, relative)
            )
            statuses[status] += 1
    log(
        "汉化外置文件校验完成: "
        f"{statuses['valid']} 个一致 · {statuses['released']} 个缺失已释放 · "
        f"{statuses['replaced']} 个异常已备份并修复"
    )
    log_path = os.path.join(editor_dir, L10N_LOG)
    try:
        os.remove(log_path)
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise PatchError(f"无法重置汉化 Hook 日志: {exc}") from exc
    return os.path.join(editor_dir, L10N_DLL), log_path


def _localization_editor_dir(editor_path):
    return os.path.join(os.path.dirname(os.path.dirname(editor_path)), "Editor")


def _localization_stash_path(editor_path):
    return os.path.join(_localization_editor_dir(editor_path), L10N_STASH_DIR)


def localization_is_uninstalled(editor_path):
    if not editor_path:
        return False
    return os.path.isfile(
        os.path.join(_localization_stash_path(editor_path), L10N_STASH_MANIFEST)
    )


def _write_json_atomic(path, value):
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


def _temporarily_uninstall_editor_dir(editor_dir):
    stash = os.path.join(editor_dir, L10N_STASH_DIR)
    temporary = stash + ".tmp"
    if os.path.exists(stash):
        raise PatchError("汉化已经处于暂时卸载状态。")
    if os.path.exists(temporary):
        raise PatchError(f"发现未完成的汉化暂存目录，请先人工检查: {temporary}")
    moved = []
    try:
        os.makedirs(temporary)
        records = []
        for relative in L10N_RESOURCES:
            target = os.path.join(editor_dir, relative)
            if not os.path.exists(target):
                continue
            if not os.path.isfile(target):
                raise PatchError(f"汉化目标不是普通文件: {target}")
            stored = os.path.join(temporary, "files", relative)
            os.makedirs(os.path.dirname(stored), exist_ok=True)
            record = {
                "path": relative.replace(os.sep, "/"),
                "size": os.path.getsize(target),
                "sha256": _sha256_hex(target),
            }
            os.replace(target, stored)
            moved.append((stored, target))
            records.append(record)
        if not records:
            raise PatchError("未发现可暂时卸载的汉化外置文件。")
        _write_json_atomic(
            os.path.join(temporary, L10N_STASH_MANIFEST),
            {
                "format": 1,
                "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "files": records,
            },
        )
        os.replace(temporary, stash)
        return len(records)
    except Exception:
        for stored, target in reversed(moved):
            if os.path.isfile(stored) and not os.path.exists(target):
                os.makedirs(os.path.dirname(target), exist_ok=True)
                os.replace(stored, target)
        try:
            shutil.rmtree(temporary)
        except OSError:
            pass
        raise


def _load_stash_manifest(editor_dir):
    stash = os.path.join(editor_dir, L10N_STASH_DIR)
    manifest_path = os.path.join(stash, L10N_STASH_MANIFEST)
    try:
        with open(manifest_path, encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError) as exc:
        raise PatchError(f"无法读取汉化恢复清单: {exc}") from exc
    if manifest.get("format") != 1:
        raise PatchError("汉化恢复清单版本无效。")
    records = []
    seen = set()
    for raw in manifest.get("files", []):
        relative = str(raw.get("path", "")).replace("/", os.sep)
        digest = str(raw.get("sha256", "")).lower()
        size = raw.get("size")
        if (
            relative not in L10N_RESOURCES
            or relative in seen
            or not isinstance(size, int)
            or size < 0
            or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
        ):
            raise PatchError("汉化恢复清单包含无效资源记录。")
        seen.add(relative)
        records.append({"path": relative, "size": size, "sha256": digest})
    if not records:
        raise PatchError("汉化恢复清单中没有文件。")
    return stash, records


def _restore_localization_editor_dir(editor_dir):
    stash, records = _load_stash_manifest(editor_dir)
    for record in records:
        stored = os.path.join(stash, "files", record["path"])
        if (
            not os.path.isfile(stored)
            or os.path.getsize(stored) != record["size"]
            or _sha256_hex(stored) != record["sha256"]
        ):
            raise PatchError(f"暂存的汉化文件损坏，未执行恢复: {record['path']}")
    conflicts = 0
    for record in records:
        stored = os.path.join(stash, "files", record["path"])
        target = os.path.join(editor_dir, record["path"])
        matches = (
            os.path.isfile(target)
            and os.path.getsize(target) == record["size"]
            and _sha256_hex(target) == record["sha256"]
        )
        if not matches:
            if os.path.exists(target):
                if not os.path.isfile(target):
                    raise PatchError(f"恢复目标不是普通文件: {target}")
                shutil.copy2(target, _next_backup_path(target))
                conflicts += 1
            os.makedirs(os.path.dirname(target), exist_ok=True)
            temporary = target + ".sc2ed_dpifix.restore.tmp"
            shutil.copy2(stored, temporary)
            os.replace(temporary, target)
        if os.path.getsize(target) != record["size"] or _sha256_hex(target) != record["sha256"]:
            raise PatchError(f"汉化文件恢复后校验失败: {target}")
    shutil.rmtree(stash)
    return len(records), conflicts


def temporarily_uninstall_localization(editor_path, log=lambda m: None):
    if is_editor_running():
        raise PatchError("编辑器正在运行，请完全关闭后再暂时卸载汉化。")
    if not editor_path or not os.path.isfile(editor_path):
        raise PatchError("未找到编辑器 exe，请先选择 SC2Editor_x64.exe。")
    count = _temporarily_uninstall_editor_dir(_localization_editor_dir(editor_path))
    log(f"已暂时卸载 {count} 个汉化外置文件，可随时恢复。")
    return count


def restore_localization(editor_path, log=lambda m: None):
    if is_editor_running():
        raise PatchError("编辑器正在运行，请完全关闭后再恢复汉化。")
    if not editor_path or not os.path.isfile(editor_path):
        raise PatchError("未找到编辑器 exe，请先选择 SC2Editor_x64.exe。")
    count, conflicts = _restore_localization_editor_dir(
        _localization_editor_dir(editor_path)
    )
    log(f"已恢复 {count} 个汉化外置文件，冲突备份 {conflicts} 个。")
    return count, conflicts


def _inject_localization(hproc, dll_path, hook_log, log=lambda m: None):
    payload = ctypes.create_unicode_buffer(os.path.abspath(dll_path))
    payload_size = ctypes.sizeof(payload)
    remote = kernel32.VirtualAllocEx(
        hproc, None, payload_size, MEM_COMMIT_RESERVE, 0x04  # PAGE_READWRITE
    )
    if not remote:
        raise PatchError(f"汉化 DLL 路径内存分配失败 err={ctypes.get_last_error()}")
    thread = None
    try:
        written = ctypes.c_size_t(0)
        if not kernel32.WriteProcessMemory(
            hproc, ctypes.c_void_p(remote), payload, payload_size, ctypes.byref(written)
        ) or written.value != payload_size:
            raise PatchError(f"汉化 DLL 路径写入失败 err={ctypes.get_last_error()}")
        module = kernel32.GetModuleHandleW("kernel32.dll")
        load_library = kernel32.GetProcAddress(module, b"LoadLibraryW") if module else None
        if not load_library:
            raise PatchError("无法定位 LoadLibraryW")
        thread_id = wintypes.DWORD(0)
        thread = kernel32.CreateRemoteThread(
            hproc, None, 0, ctypes.c_void_p(load_library), ctypes.c_void_p(remote),
            0, ctypes.byref(thread_id),
        )
        if not thread:
            raise PatchError(f"汉化 DLL 注入线程创建失败 err={ctypes.get_last_error()}")
        if kernel32.WaitForSingleObject(thread, 15000) != WAIT_OBJECT_0:
            raise PatchError("汉化 DLL 注入超时")
        exit_code = wintypes.DWORD(0)
        if not kernel32.GetExitCodeThread(thread, ctypes.byref(exit_code)):
            raise PatchError(f"无法读取汉化 DLL 注入结果 err={ctypes.get_last_error()}")
    finally:
        if thread:
            kernel32.CloseHandle(thread)
        kernel32.VirtualFreeEx(hproc, ctypes.c_void_p(remote), 0, MEM_RELEASE)

    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        try:
            with open(hook_log, "r", encoding="utf-8", errors="replace") as handle:
                status = handle.read()
        except FileNotFoundError:
            status = ""
        if "hook installed" in status:
            log("官方依赖汉化 Hook 已安装 · 运行时名称表加载成功")
            return
        if any(marker in status for marker in (
            "signature mismatch", "hook refused", "cannot ",
            "unexpectedly small", "invalid mapping",
        )):
            raise PatchError("汉化 Hook 拒绝安装: " + status.strip().splitlines()[-1])
        time.sleep(0.05)
    raise PatchError(f"汉化 Hook 未报告安装成功，请检查 {hook_log}")


def launch_patched(
    editor_path,
    log=lambda m: None,
    mode=None,
    enhanced=None,
    font_pct=85,
    localization=True,
):
    """挂起启动编辑器并按 mode 施加高 DPI 修复。

    mode:
      "crisp_fit" —— 清晰适配。不改 awareness(保留编辑器原生 DPI-aware => D3D9 按
                    物理像素清晰渲染), 只把字体工厂分母从 72 改成 font_pct 对应值,
                    把字体统一缩到贴合欠缩放的控件框。最小侵入, 治"文字对不上"。
      "pmv2"     —— 强制 Per-Monitor-V2 awareness(物理像素渲染 + 系统缩放对话框)。
      "enhanced" —— DPI-unaware + GDIDPISCALING("系统增强"矢量缩放, 不溢出但偏软)。
      "bitmap"   —— DPI-unaware 纯位图缩放(最稳、最糊)。
    font_pct: 仅 crisp_fit 用。字体缩放百分比(100=原生真实 DPI 字号, 越小越紧)。
    localization: 是否释放缺失的外置汉化文件并注入官方依赖名称 Hook。
    (旧参数 enhanced=True/False 仍兼容: 映射到 enhanced/bitmap。)
    """
    if mode is None:
        mode = "enhanced" if enhanced else ("bitmap" if enhanced is False else "pmv2")
    mode = str(mode).lower()
    if mode not in ("crisp_fit", "pmv2", "enhanced", "bitmap"):
        mode = "pmv2"

    if is_editor_running():
        raise PatchError("编辑器已在运行 — 单实例程序,请先完全关闭再启动。")
    if not editor_path or not os.path.isfile(editor_path):
        raise PatchError("未找到编辑器 exe,请手动选择 SC2Editor_x64.exe。")

    l10n_dll = None
    l10n_log = None
    if localization:
        l10n_dll, l10n_log = _prepare_localization(editor_path, log)
    else:
        log("官方依赖汉化已关闭 · 不释放文件、不注入 Hook")

    workdir = os.path.dirname(editor_path)
    cmdline = '"' + editor_path + '"'
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()

    # 增强模式: 优先入口点注入 UNAWARE_GDISCALED(-5) 硬激活 GDI 矢量缩放(不写注册表);
    # 仅在老系统(user32 无该 API)或 32 位 Python 时回退注册表兼容层(需在 CreateProcess 前写)。
    layer_set = False
    enh_inject = False
    if mode == "enhanced":
        if (getattr(user32, "SetProcessDpiAwarenessContext", None) is not None
                and ctypes.sizeof(ctypes.c_void_p) == 8):
            enh_inject = True
            log("系统增强: 入口点注入 UNAWARE_GDISCALED(-5) 硬激活 GDI 矢量缩放 "
                "· 不写注册表 · 游戏零影响…")
        else:
            layer_set = _set_compat_layer(editor_path)
            log("系统增强: 注册表兼容层回退(仅编辑器路径)…"
                if layer_set else "系统增强不可用, 回退位图模式…")

    log(f"[{mode}] 挂起启动编辑器…")
    if not kernel32.CreateProcessW(ctypes.c_wchar_p(editor_path), ctypes.c_wchar_p(cmdline),
                                   None, None, False, CREATE_SUSPENDED, None,
                                   ctypes.c_wchar_p(workdir), ctypes.byref(si), ctypes.byref(pi)):
        if layer_set:
            _del_compat_layer(editor_path)
        raise PatchError(f"启动失败 err={ctypes.get_last_error()}")
    try:
        log(f"pid={pi.dwProcessId} · 读取镜像基址…")
        base = _image_base(pi.hProcess)

        # 清晰适配: 不碰 awareness(保留编辑器原生 DPI-aware => 清晰), 只缩字体贴合框。
        if mode == "crisp_fit":
            denom = font_scale_to_denom(font_pct)
            log(f"基址 {base:#x} · [清晰适配] 字体 {font_pct}%(分母 72->{denom}) · "
                f"保留原生 DPI-aware(清晰)…")
            nf = _patch_font_denom(pi.hProcess, base, denom, log)
            if nf == 0:
                kernel32.TerminateProcess(pi.hProcess, 1)
                raise PatchError("未定位到字体分母换算点,已安全中止。"
                                 "编辑器可能已更新,请重新在 IDA 核对特征码。")
            if localization:
                _inject_localization(pi.hProcess, l10n_dll, l10n_log, log)
            log(f"已改 {nf} 处字体分母 · 恢复运行(物理像素清晰 · 字体已缩放贴合)…")
            kernel32.ResumeThread(pi.hThread)
            return

        log(f"基址 {base:#x} · 定位 DPI 调用点(按字符串锚定 · 版本无关)…")

        sites = _find_dpi_sites(pi.hProcess, base, log)

        # 兜底: 扫描没命中时, 试已知各版本 RVA(仅当该处确为 FF D0)
        if not sites:
            log("扫描未命中, 尝试已知 RVA 兜底…")
            for rva in KNOWN_DPI_RVAS:
                addr = base + rva
                try:
                    if _rpm(pi.hProcess, addr, 2) == b"\xff\xd0":
                        sites.append(addr)
                except PatchError:
                    pass

        # 三种模式都先 NOP 掉编辑器自声明 DPI 的调用:
        #  · enhanced/bitmap: 否则它会改回 aware 顶掉缩放;
        #  · pmv2: 否则它会把 PMv2 覆盖成 PMv1(不自动缩放对话框->溢出)。
        patched = 0
        for addr in sites:
            cur = _rpm(pi.hProcess, addr, 2)
            if cur == b"\x90\x90":
                continue
            if cur != b"\xff\xd0":       # 安全: 只改 call rax
                continue
            _wpm(pi.hProcess, addr, b"\x90\x90")
            patched += 1
        log(f"已 NOP {patched} 处编辑器自声明 DPI 调用。")

        pmv2_ok = False
        if mode == "pmv2":
            log("强制 Per-Monitor-V2 awareness(入口点注入)…")
            try:
                _force_pmv2(pi.hProcess, base, log)
                pmv2_ok = True
            except PatchError as e:
                log(f"PMv2 强制失败({e}) · 回退纯位图缩放…")

        enh_ok = False
        if mode == "enhanced" and enh_inject:
            log("入口点注入 UNAWARE_GDISCALED(-5) 硬激活系统增强矢量缩放…")
            try:
                _inject_dpi_context(pi.hProcess, base, DPI_UNAWARE_GDISCALED,
                                    "系统增强", log)
                enh_ok = True
            except PatchError as e:
                log(f"系统增强注入失败({e}) · 回退纯位图缩放…")

        # 成败判定: 每种模式至少要达成其核心手段, 否则安全中止不放行
        if mode == "pmv2":
            if not pmv2_ok and patched == 0:
                kernel32.TerminateProcess(pi.hProcess, 1)
                raise PatchError("PMv2 注入与 DPI 调用点均未成功,已安全中止。")
            log("PMv2 已就绪 · 恢复运行(物理像素渲染 · 系统自动缩放控件)…"
                if pmv2_ok else "已回退位图 · 恢复运行…")
        elif mode == "enhanced":
            if not enh_ok and not layer_set and patched == 0:
                kernel32.TerminateProcess(pi.hProcess, 1)
                raise PatchError("系统增强注入/兼容层/DPI 调用点均未成功,已安全中止。")
            log("系统增强(GDI 矢量缩放)已就绪 · 恢复运行…"
                if enh_ok or layer_set else "已回退位图 · 恢复运行…")
        else:  # bitmap
            if patched == 0:
                kernel32.TerminateProcess(pi.hProcess, 1)
                raise PatchError("未能定位任何 DPI 调用点,已安全中止。")
            log("位图缩放已就绪 · 恢复运行…")

        if localization:
            _inject_localization(pi.hProcess, l10n_dll, l10n_log, log)
        kernel32.ResumeThread(pi.hThread)
        # 进程已完成创建(兼容层已生效), 延时删除注册表键 -> 恢复热切换,
        # 且编辑器"测试文档"稍后拉起的游戏路径不同、届时键已删, 双重保险。
        if layer_set:
            threading.Timer(6.0, _del_compat_layer, args=(editor_path,)).start()
    except Exception:
        kernel32.TerminateProcess(pi.hProcess, 1)
        if layer_set:
            _del_compat_layer(editor_path)
        raise
    finally:
        kernel32.CloseHandle(pi.hThread)
        kernel32.CloseHandle(pi.hProcess)
