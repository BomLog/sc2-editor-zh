#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SC2 编辑器 高DPI 字体溢出 外置修复启动器
------------------------------------------------
原理:
  SC2Editor_x64.exe 启动时用 GetProcAddress 动态调用
    SetProcessDpiAwareness(2)   (Shcore.dll)
    SetProcessDPIAware()        (User32.dll)
  向系统声明自己"支持高DPI",于是系统不再整窗缩放,而它的
  对话框控件尺寸写死 → 高缩放下字体撑破边框看不清。

本工具组合两招让编辑器在高DPI下清晰缩放且不溢出:
  ① 给子进程注入环境变量  __COMPAT_LAYER=GDIDPISCALING DPIUNAWARE
     → 启用 Windows "系统(增强)" GDI 矢量级缩放(比纯位图缩放清晰)。
  ② 以【挂起】方式启动, 在主线程运行前把编辑器运行时的两处
        call rax  (FF D0)  →  NOP NOP (90 90)
     NOP 掉它主动声明 DPI-aware 的调用(SetProcessDpiAwareness / SetProcessDPIAware),
     否则它会把自己改回 aware, 顶掉 GDI 缩放。

* 环境变量只对本工具启动的这个进程生效, 不写注册表、不改任何磁盘文件。
* 用本工具启动 = GDI增强缩放修复版;用原快捷方式启动 = 原样。热切换。
* 不触发 Battle.net 完整性校验(文件没动)。
"""

import ctypes
import os
import sys
from ctypes import wintypes

# ------- 配置:编辑器路径(按需修改) -------
EDITOR = r"D:\StarCraft II\Support64\SC2Editor_x64.exe"
WORKDIR = os.path.dirname(EDITOR)

# 相对镜像基址的 RVA(已在 IDA 中核对: 原始字节 = FF D0 = call rax)
# 镜像首选基址 0x140000000, 这两个 VA 为 0x140138880 / 0x143245792
PATCHES = [
    (0x138880, b"\xff\xd0", b"\x90\x90"),   # SetProcessDpiAwareness(2)
    (0x3245792, b"\xff\xd0", b"\x90\x90"),  # SetProcessDPIAware()
]

CREATE_SUSPENDED = 0x00000004
PAGE_EXECUTE_READWRITE = 0x40

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
ntdll = ctypes.WinDLL("ntdll")

# 让控制台正确显示中文(UTF-8)
try:
    kernel32.SetConsoleOutputCP(65001)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


class PROCESS_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("Reserved1", ctypes.c_void_p),
        ("PebBaseAddress", ctypes.c_void_p),
        ("Reserved2", ctypes.c_void_p * 2),
        ("UniqueProcessId", ctypes.c_void_p),
        ("Reserved3", ctypes.c_void_p),
    ]


def _err(msg):
    print("[!] " + msg, file=sys.stderr)
    sys.exit(1)


def get_image_base(hProcess):
    """通过 PEB 读取主模块实际加载基址(应对 ASLR)。"""
    pbi = PROCESS_BASIC_INFORMATION()
    ret_len = ctypes.c_ulong(0)
    status = ntdll.NtQueryInformationProcess(
        hProcess, 0, ctypes.byref(pbi), ctypes.sizeof(pbi), ctypes.byref(ret_len)
    )
    if status != 0:
        _err(f"NtQueryInformationProcess 失败 status={status:#x}")
    peb = pbi.PebBaseAddress
    # x64: PEB+0x10 = ImageBaseAddress
    base = ctypes.c_ulonglong(0)
    nread = ctypes.c_size_t(0)
    if not kernel32.ReadProcessMemory(
        hProcess, ctypes.c_void_p(peb + 0x10),
        ctypes.byref(base), 8, ctypes.byref(nread)
    ):
        _err(f"读取 PEB.ImageBaseAddress 失败 err={ctypes.get_last_error()}")
    return base.value


def read_mem(hProcess, addr, size):
    buf = (ctypes.c_ubyte * size)()
    nread = ctypes.c_size_t(0)
    if not kernel32.ReadProcessMemory(
        hProcess, ctypes.c_void_p(addr), buf, size, ctypes.byref(nread)
    ):
        _err(f"ReadProcessMemory@{addr:#x} 失败 err={ctypes.get_last_error()}")
    return bytes(buf)


def write_mem(hProcess, addr, data):
    old = wintypes.DWORD(0)
    if not kernel32.VirtualProtectEx(
        hProcess, ctypes.c_void_p(addr), len(data),
        PAGE_EXECUTE_READWRITE, ctypes.byref(old)
    ):
        _err(f"VirtualProtectEx@{addr:#x} 失败 err={ctypes.get_last_error()}")
    buf = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    nwrote = ctypes.c_size_t(0)
    ok = kernel32.WriteProcessMemory(
        hProcess, ctypes.c_void_p(addr), buf, len(data), ctypes.byref(nwrote)
    )
    kernel32.VirtualProtectEx(
        hProcess, ctypes.c_void_p(addr), len(data), old, ctypes.byref(old)
    )
    if not ok:
        _err(f"WriteProcessMemory@{addr:#x} 失败 err={ctypes.get_last_error()}")


def main():
    verify = "--verify" in sys.argv
    extra_args = [a for a in sys.argv[1:] if a != "--verify"]

    if not os.path.isfile(EDITOR):
        _err(f"找不到编辑器: {EDITOR}\n请修改脚本顶部 EDITOR 路径。")

    # 单实例保护: 编辑器已在运行时, 新实例会检测到已有实例并立刻自退
    # (表现为"一闪而过")。这里提前拦截并提示。
    import subprocess
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq SC2Editor_x64.exe", "/NH"],
            capture_output=True
        ).stdout
        if b"SC2Editor_x64.exe" in out:
            _err("编辑器已在运行 —— SC2 编辑器是单实例程序,\n"
                 "    直接再启动会被现有实例挤掉(一闪而过)。\n"
                 "    请先【完全关闭】正在运行的编辑器,再用本工具启动。")
    except FileNotFoundError:
        pass  # 没有 tasklist 就跳过检测

    # 命令行: "<exe路径>" [透传参数]  —— 复刻官方启动器行为
    cmdline = '"' + EDITOR + '"'
    if extra_args:
        cmdline += " " + " ".join(extra_args)

    # 【重要】不注入 __COMPAT_LAYER 环境变量:它会被子进程继承,
    # 编辑器"测试文档"启动的游戏(DPI-aware)会继承 DPIUNAWARE 导致
    # 界面错位/点不动。这里只做进程内存补丁,不碰环境,游戏零影响。
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()

    ok = kernel32.CreateProcessW(
        ctypes.c_wchar_p(EDITOR),           # lpApplicationName
        ctypes.c_wchar_p(cmdline),          # lpCommandLine (可写字符串)
        None, None, False,
        CREATE_SUSPENDED,
        None,
        ctypes.c_wchar_p(WORKDIR),          # 工作目录 = Support64
        ctypes.byref(si), ctypes.byref(pi),
    )
    if not ok:
        _err(f"CreateProcessW 失败 err={ctypes.get_last_error()}")

    print(f"[+] 已挂起启动编辑器 pid={pi.dwProcessId}")

    try:
        base = get_image_base(pi.hProcess)
        print(f"[+] 主模块基址 = {base:#x}")

        for rva, old, new in PATCHES:
            addr = base + rva
            cur = read_mem(pi.hProcess, addr, len(old))
            if cur == new:
                print(f"    {addr:#x} (RVA {rva:#x}): 已是 {new.hex()}")
                continue
            if cur != old:
                # 字节不符 → 版本可能已更新, 中止并结束进程避免半patch
                kernel32.TerminateProcess(pi.hProcess, 1)
                _err(f"{addr:#x} 字节为 {cur.hex()}, 期望 {old.hex()}\n"
                     f"编辑器版本可能已更新, RVA 需重新在 IDA 里核对。已终止进程未修改。")
            write_mem(pi.hProcess, addr, new)
            back = read_mem(pi.hProcess, addr, len(new))
            status = "OK" if back == new else f"FAIL(now {back.hex()})"
            print(f"    {addr:#x} (RVA {rva:#x}): {old.hex()} -> {back.hex()}  {status}")

        if verify:
            print("[i] --verify 模式: 已确认补丁写入, 不恢复运行, 结束进程。")
            kernel32.TerminateProcess(pi.hProcess, 0)
        else:
            kernel32.ResumeThread(pi.hThread)
            print("[+] 补丁完成, 编辑器已恢复运行(DPI-unaware, 由系统整窗缩放)。")
    finally:
        kernel32.CloseHandle(pi.hThread)
        kernel32.CloseHandle(pi.hProcess)


if __name__ == "__main__":
    main()
