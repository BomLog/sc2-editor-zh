#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SC2 编辑器 高DPI 字体溢出 修复器 —— 科技感动画 GUI
==================================================
内核: 挂起启动 SC2Editor_x64.exe -> 读 PEB 真实基址(ASLR) ->
      两处运行时 DPI-aware 调用 (call rax = FF D0) NOP 成 90 90 -> 恢复运行。
      进程退回 DPI-unaware, 系统整窗缩放, 字体不再撑破边框。
特点: 不改磁盘文件 / 不注入环境变量(不污染测试游戏) / 热切换 /
      不触发 Battle.net 完整性校验 / 自动定位编辑器。
"""

import ctypes
import math
import os
import queue
import string
import threading
import tkinter as tk
from ctypes import wintypes

import dpifix_core as core

# ============================================================
#  修复内核 (ctypes)
# ============================================================
PATCHES = [
    (0x138880, b"\xff\xd0", b"\x90\x90"),   # SetProcessDpiAwareness(2)
    (0x3245792, b"\xff\xd0", b"\x90\x90"),  # SetProcessDPIAware()
]
REL = os.path.join("Support64", "SC2Editor_x64.exe")

CREATE_SUSPENDED = 0x00000004
PAGE_EXECUTE_READWRITE = 0x40
TH32CS_SNAPPROCESS = 0x00000002
MAX_PATH = 260

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
ntdll = ctypes.WinDLL("ntdll")


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
    """自动定位 SC2Editor_x64.exe: 注册表 -> 常见路径 -> 全盘符扫描。"""
    seen = []

    def add(base):
        if not base:
            return None
        p = base if base.lower().endswith("sc2editor_x64.exe") else os.path.join(base, REL)
        if os.path.isfile(p) and p not in seen:
            seen.append(p)
            return p
        return None

    # 1) 注册表 (卸载项 InstallLocation / Blizzard 安装信息)
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

    # 2) 常见安装路径
    commons = [
        r"C:\Program Files (x86)\StarCraft II", r"C:\Program Files\StarCraft II",
        r"D:\StarCraft II", r"E:\StarCraft II", r"F:\StarCraft II", r"G:\StarCraft II",
        r"D:\Program Files (x86)\StarCraft II", r"E:\Program Files (x86)\StarCraft II",
    ]
    for c in commons:
        r = add(c)
        if r:
            return r

    # 3) 全盘符扫描盘根 + Program Files
    for d in string.ascii_uppercase:
        root = f"{d}:\\"
        if not os.path.isdir(root):
            continue
        for sub in ("StarCraft II", r"Program Files\StarCraft II",
                    r"Program Files (x86)\StarCraft II", r"Games\StarCraft II",
                    r"SC2\StarCraft II"):
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


def _get_image_base(hproc):
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


def launch_patched(editor_path, log):
    if is_editor_running():
        raise PatchError("编辑器已在运行 — 单实例程序,请先完全关闭再启动。")
    if not editor_path or not os.path.isfile(editor_path):
        raise PatchError("未找到编辑器 exe,请手动选择 SC2Editor_x64.exe。")

    workdir = os.path.dirname(editor_path)
    cmdline = '"' + editor_path + '"'
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()

    log("挂起启动编辑器…")
    if not kernel32.CreateProcessW(ctypes.c_wchar_p(editor_path), ctypes.c_wchar_p(cmdline),
                                   None, None, False, CREATE_SUSPENDED, None,
                                   ctypes.c_wchar_p(workdir), ctypes.byref(si), ctypes.byref(pi)):
        raise PatchError(f"启动失败 err={ctypes.get_last_error()}")
    try:
        log(f"pid={pi.dwProcessId} · 读取镜像基址…")
        base = _get_image_base(pi.hProcess)
        log(f"基址 {base:#x} · 写入补丁…")
        for rva, old, new in PATCHES:
            addr = base + rva
            cur = _rpm(pi.hProcess, addr, len(old))
            if cur == new:
                continue
            if cur != old:
                kernel32.TerminateProcess(pi.hProcess, 1)
                raise PatchError(f"字节不符 @ RVA {rva:#x} — 编辑器可能已更新,已安全中止。")
            _wpm(pi.hProcess, addr, new)
        log("补丁完成 · 恢复运行…")
        kernel32.ResumeThread(pi.hThread)
    except Exception:
        kernel32.TerminateProcess(pi.hProcess, 1)
        raise
    finally:
        kernel32.CloseHandle(pi.hThread)
        kernel32.CloseHandle(pi.hProcess)


# ============================================================
#  科技感动画 GUI
# ============================================================
W, H = 480, 420
C_BG = "#060910"
C_CARD = "#0b1220"
C_EDGE = "#15304a"
C_CYAN = "#22d3ee"
C_CYAN_HI = "#7ff3ff"
C_BLUE = "#3b82f6"
C_OK = "#34d399"
C_ERR = "#fb7185"
C_TEXT = "#d7e6f5"
C_MUTED = "#3f5570"
C_GRID = "#0e1a2b"


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def mix(c1, c2, t):
    a, b = _rgb(c1), _rgb(c2)
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class App:
    def __init__(self, root):
        self.root = root
        root.overrideredirect(True)
        root.geometry(f"{W}x{H}+{(root.winfo_screenwidth()-W)//2}+{(root.winfo_screenheight()-H)//3}")
        root.configure(bg=C_BG)
        try:
            root.attributes("-alpha", 0.0)
        except tk.TclError:
            pass
        root.attributes("-topmost", True)
        root.after(400, lambda: root.attributes("-topmost", False))

        self.cv = tk.Canvas(root, width=W, height=H, bg=C_BG, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)

        self.editor = find_editor()
        self.busy = False
        self.state = "idle"           # idle|busy|ok|err
        self.spin = 0.0
        self.t = 0.0                  # 全局时间
        self.btn_t = 0.0
        self.btn_hover = False
        self.btn_press = False
        self.win_alpha = 0.0
        self.intro = 0.0              # 开场动画 0..1
        self.status = "已定位编辑器 · 准备就绪" if self.editor else "未自动找到,点下方手动选择"
        self.status_color = C_CYAN if self.editor else C_ERR
        self.status_alpha = 0.0
        self.q = queue.Queue()

        # 数据流粒子
        self.particles = []
        s = 987654321
        for _ in range(34):
            s = (s * 1103515245 + 12345) & 0x7fffffff; x = s % W
            s = (s * 1103515245 + 12345) & 0x7fffffff; y = s % H
            s = (s * 1103515245 + 12345) & 0x7fffffff; r = 1 + s % 2
            s = (s * 1103515245 + 12345) & 0x7fffffff; sp = 0.2 + (s % 100) / 130.0
            self.particles.append([float(x), float(y), r, sp])

        self.cx, self.cy, self.cr = W // 2, 186, 52
        self.bx1, self.by1, self.bx2, self.by2 = 100, 300, W - 100, 350

        self._build_static()
        self._bind()
        self._animate()

    # ---------- 静态层 ----------
    def _build_static(self):
        cv = self.cv
        # 网格背景
        for gx in range(0, W, 26):
            cv.create_line(gx, 0, gx, H, fill=C_GRID, tags="grid")
        for gy in range(0, H, 26):
            cv.create_line(0, gy, W, gy, fill=C_GRID, tags="grid")
        # 卡片
        self._round_rect(10, 10, W - 10, H - 10, 16, fill=C_CARD, outline=C_EDGE)
        # 标题
        cv.create_text(W // 2, 58, text="SC2  EDITOR  DPI  FIX",
                       fill=C_CYAN, font=("Consolas", 18, "bold"))
        cv.create_text(W // 2, 84, text="高 DPI 字体溢出修复 · 外置内存补丁 · 不改文件",
                       fill=C_MUTED, font=("Microsoft YaHei UI", 9))
        cv.create_text(W // 2, 100, text="///  MEMORY  PATCH  ENGINE  ///",
                       fill=mix(C_CARD, C_BLUE, 0.7), font=("Consolas", 8))
        # 关闭
        self.close_id = cv.create_text(W - 30, 28, text="✕", fill=C_MUTED,
                                       font=("Segoe UI", 13), tags="close")
        # 状态 / 路径
        self.status_id = cv.create_text(W // 2, 372, text=self.status,
                                        fill=self.status_color, font=("Microsoft YaHei UI", 10))
        self.path_id = cv.create_text(W // 2, 398, text=self._path_label(),
                                      fill=C_MUTED, font=("Consolas", 8), tags="pick")

    def _path_label(self):
        if self.editor:
            p = self.editor
            if len(p) > 56:
                p = p[:27] + "…" + p[-27:]
            return "» " + p + "  [更换]"
        return "» 点此选择 SC2Editor_x64.exe"

    def _round_rect(self, x1, y1, x2, y2, r, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.cv.create_polygon(pts, smooth=True, **kw)

    # ---------- 交互 ----------
    def _bind(self):
        cv = self.cv
        cv.tag_bind("close", "<Button-1>", lambda e: self._fade_out())
        cv.tag_bind("close", "<Enter>", lambda e: cv.itemconfig(self.close_id, fill=C_ERR))
        cv.tag_bind("close", "<Leave>", lambda e: cv.itemconfig(self.close_id, fill=C_MUTED))
        cv.tag_bind("pick", "<Button-1>", lambda e: self._pick_editor())
        cv.bind("<Motion>", self._on_motion)
        cv.bind("<Button-1>", self._on_click)
        cv.bind("<ButtonRelease-1>", self._on_release)
        cv.bind("<B1-Motion>", self._drag_move, add="+")

    def _in_button(self, x, y):
        return self.bx1 <= x <= self.bx2 and self.by1 <= y <= self.by2 and not self.busy

    def _on_motion(self, e):
        self.btn_hover = self._in_button(e.x, e.y)
        self.cv.config(cursor="hand2" if (self.btn_hover or e.y > 388) else "")

    def _on_click(self, e):
        self._dx, self._dy = e.x, e.y
        if self._in_button(e.x, e.y):
            self.btn_press = True

    def _on_release(self, e):
        if self.btn_press:
            self.btn_press = False
            if self._in_button(e.x, e.y):
                self._launch()

    def _drag_move(self, e):
        if getattr(self, "_dy", None) is not None and self._dy < 110 and not self.busy:
            self.root.geometry(f"+{self.root.winfo_x()+e.x-self._dx}+{self.root.winfo_y()+e.y-self._dy}")

    def _pick_editor(self):
        if self.busy:
            return
        from tkinter import filedialog
        p = filedialog.askopenfilename(title="选择 SC2Editor_x64.exe",
                                       filetypes=[("SC2Editor", "SC2Editor_x64.exe"), ("exe", "*.exe")])
        if p:
            self.editor = p
            self.cv.itemconfig(self.path_id, text=self._path_label())
            self._set_status("已选择编辑器", C_CYAN)

    # ---------- 启动 ----------
    def _launch(self):
        if self.busy:
            return
        self.busy = True
        self.state = "busy"
        self._set_status("初始化补丁引擎…", C_CYAN)
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            core.launch_patched(self.editor, lambda m: self.q.put(("log", m)))
            self.q.put(("ok", "已启动 · 官方依赖汉化已加载 ✓"))
        except core.PatchError as ex:
            self.q.put(("err", str(ex)))
        except Exception as ex:  # noqa
            self.q.put(("err", f"错误: {ex}"))

    def _set_status(self, text, color):
        self.status = text
        self.status_color = color
        self.status_alpha = 0.0
        self.cv.itemconfig(self.status_id, text=text)

    def _drain(self):
        try:
            while True:
                kind, msg = self.q.get_nowait()
                if kind == "log":
                    self._set_status(msg, C_CYAN)
                elif kind == "ok":
                    self.busy = False; self.state = "ok"; self._set_status(msg, C_OK)
                elif kind == "err":
                    self.busy = False; self.state = "err"; self._set_status(msg, C_ERR)
        except queue.Empty:
            pass

    # ---------- 动画主循环 ----------
    def _animate(self):
        self._drain()
        self.t += 0.06
        if self.win_alpha < 1.0:
            self.win_alpha = min(1.0, self.win_alpha + 0.09)
            try:
                self.root.attributes("-alpha", self.win_alpha)
            except tk.TclError:
                pass
        if self.intro < 1.0:
            self.intro = min(1.0, self.intro + 0.05)

        # 按钮插值
        tgt = 1.0 if self.btn_hover and not self.busy else 0.0
        self.btn_t += (tgt - self.btn_t) * 0.22
        # 状态淡入
        if self.status_alpha < 1.0:
            self.status_alpha = min(1.0, self.status_alpha + 0.12)
            self.cv.itemconfig(self.status_id, fill=mix(C_CARD, self.status_color, self.status_alpha))

        self.spin = (self.spin + (14 if self.busy else 4)) % 360
        self._draw_reticle()
        self._draw_button()
        self._draw_corners()
        self._draw_scan()
        self._draw_particles()

        self.root.after(24, self._animate)

    def _accent(self):
        return {"ok": C_OK, "err": C_ERR}.get(self.state, C_CYAN)

    def _draw_reticle(self):
        cv, cx, cy = self.cv, self.cx, self.cy
        cv.delete("ring")
        col = self._accent()
        R = self.cr * (0.6 + 0.4 * self.intro)
        # 外环 + 刻度(随 spin 旋转)
        cv.create_oval(cx - R, cy - R, cx + R, cy + R, outline=mix(C_CARD, col, 0.35), width=1, tags="ring")
        for a in range(0, 360, 15):
            ang = math.radians(a + self.spin * 0.4)
            r2 = R
            r1 = R - (9 if a % 45 == 0 else 5)
            cv.create_line(cx + r1 * math.cos(ang), cy + r1 * math.sin(ang),
                           cx + r2 * math.cos(ang), cy + r2 * math.sin(ang),
                           fill=mix(C_CARD, col, 0.55), tags="ring")
        # 反向虚线弧段
        rm = R - 14
        for k in range(4):
            st = self.spin * -1.3 + k * 90
            cv.create_arc(cx - rm, cy - rm, cx + rm, cy + rm, start=st, extent=52,
                          style="arc", outline=mix(C_CARD, C_BLUE, 0.8), width=2, tags="ring")
        # 忙时高亮扫描弧
        if self.busy:
            cv.create_arc(cx - R, cy - R, cx + R, cy + R, start=self.spin, extent=80,
                          style="arc", outline=C_CYAN_HI, width=3, tags="ring")
        # 呼吸内环
        br = 22 + math.sin(self.t * 2) * 3
        cv.create_oval(cx - br, cy - br, cx + br, cy + br, outline=mix(C_CARD, col, 0.9), width=2, tags="ring")
        # 中心图标
        if self.state == "ok":
            cv.create_line(cx - 13, cy + 1, cx - 4, cy + 11, cx + 15, cy - 13,
                           fill=C_OK, width=4, capstyle="round", joinstyle="round", tags="ring")
        elif self.state == "err":
            cv.create_line(cx - 11, cy - 11, cx + 11, cy + 11, fill=C_ERR, width=4, capstyle="round", tags="ring")
            cv.create_line(cx + 11, cy - 11, cx - 11, cy + 11, fill=C_ERR, width=4, capstyle="round", tags="ring")
        else:
            cv.create_text(cx, cy, text="DPI", fill=mix(C_CARD, C_CYAN_HI, 0.95),
                           font=("Consolas", 16, "bold"), tags="ring")

    def _draw_button(self):
        cv = self.cv
        cv.delete("btn")
        t = self.btn_t
        col = mix(C_CYAN, C_CYAN_HI, t)
        if self.busy:
            col = mix(C_CYAN, C_CARD, 0.6)
        if self.btn_press:
            col = mix(col, "#000000", 0.2)
        g = int(2 * t)
        x1, y1, x2, y2 = self.bx1 - g, self.by1 - g, self.bx2 + g, self.by2 + g
        # 霓虹光晕
        if t > 0.02 and not self.busy:
            self._round_rect(x1 - 4, y1 - 4, x2 + 4, y2 + 4, 14, fill="",
                             outline=mix(C_CARD, C_CYAN, t * 0.7), width=2, tags="btn")
        # 描边 + 填充(半透明感: 深填充 + 亮边)
        self._round_rect(x1, y1, x2, y2, 12, fill=mix(C_CARD, col, 0.30 + 0.25 * t),
                         outline=col, width=2, tags="btn")
        label = "PATCHING…" if self.busy else "▶  启动修复版编辑器"
        cv.create_text((x1 + x2) // 2, (y1 + y2) // 2, text=label,
                       fill=C_CYAN_HI if not self.busy else C_MUTED,
                       font=("Microsoft YaHei UI", 12, "bold"), tags="btn")

    def _draw_corners(self):
        cv = self.cv
        cv.delete("corner")
        col = mix(C_CARD, self._accent(), 0.5 + 0.3 * math.sin(self.t * 1.5))
        L = 22 * self.intro
        m = 18
        for (ox, oy, sx, sy) in [(m, m, 1, 1), (W - m, m, -1, 1),
                                 (m, H - m, 1, -1), (W - m, H - m, -1, -1)]:
            cv.create_line(ox, oy, ox + sx * L, oy, fill=col, width=2, tags="corner")
            cv.create_line(ox, oy, ox, oy + sy * L, fill=col, width=2, tags="corner")

    def _draw_scan(self):
        cv = self.cv
        cv.delete("scan")
        y = 14 + ((self.t * 34) % (H - 28))
        cv.create_line(14, y, W - 14, y, fill=mix(C_CARD, C_CYAN, 0.18), tags="scan")

    def _draw_particles(self):
        cv = self.cv
        cv.delete("pt")
        for p in self.particles:
            p[1] -= p[3]
            if p[1] < 12:
                p[1] = H - 12
            cv.create_oval(p[0] - p[2], p[1] - p[2], p[0] + p[2], p[1] + p[2],
                           fill=mix(C_CARD, C_BLUE, 0.4), outline="", tags="pt")
        cv.tag_lower("pt")
        cv.tag_lower("grid")

    def _fade_out(self):
        if self.win_alpha <= 0.05:
            self.root.destroy(); return
        self.win_alpha -= 0.12
        try:
            self.root.attributes("-alpha", max(0.0, self.win_alpha))
        except tk.TclError:
            pass
        self.root.after(16, self._fade_out)


def main():
    root = tk.Tk()
    root.title("SC2 编辑器 DPI 修复")
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
