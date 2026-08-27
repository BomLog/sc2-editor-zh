#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SC2 银河编辑器 DPI 修复 —— QtWebEngine(Chromium)高级动画版
============================================================
UI:  PySide6 QWebEngineView 承载 HTML/CSS,动画走 Chromium 合成器(丝滑 60fps),
     桥接走 QWebChannel(稳定,无 pythonnet)。
内核: dpifix_core.launch_patched —— 挂起启动 + 内存 NOP 两处 DPI 调用 + 恢复。
     不改文件 / 不注入环境变量(不污染测试游戏) / 单实例保护 / 自动定位编辑器。
"""
import threading

from PySide6.QtCore import QFile, QIODevice, QObject, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QColor
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QFileDialog, QVBoxLayout, QWidget

import dpifix_core as core

HTML = r"""
<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<style>
  :root{--cyan:#22d3ee;--cyan-hi:#a8f6ff;--blue:#4f7dff;--vio:#8b5cf6;
        --ok:#34d399;--err:#fb7185;--text:#e6f0ff;--muted:#63769a;--accent:var(--cyan);}
  *{margin:0;padding:0;box-sizing:border-box;user-select:none;}
  html,body{width:100%;height:100%;overflow:hidden;background:transparent;
    font-family:"Microsoft YaHei UI","Segoe UI",sans-serif;}
  .app{position:absolute;inset:12px;border-radius:22px;overflow:hidden;
    background:
      radial-gradient(130% 100% at 50% -10%, rgba(79,125,255,.18), transparent 60%),
      linear-gradient(160deg,#0c1428 0%,#070b16 60%,#05060f 100%);
    border:1px solid rgba(120,170,255,.16);
    box-shadow:0 24px 70px rgba(0,0,0,.6), inset 0 1px 0 rgba(255,255,255,.06);}
  /* 极光光斑 */
  .aurora{position:absolute;left:50%;top:40%;width:760px;height:760px;
    transform:translate(-50%,-50%);pointer-events:none;
    background:conic-gradient(from 0deg,transparent,rgba(34,211,238,.22) 18%,transparent 38%,
      rgba(139,92,246,.20) 58%,transparent 76%,rgba(79,125,255,.18) 92%,transparent);
    filter:blur(50px);opacity:.75;animation:spin 20s linear infinite;}
  .grain{position:absolute;inset:0;pointer-events:none;opacity:.5;
    background:radial-gradient(circle at 50% 120%, rgba(79,125,255,.10), transparent 55%);}
  .drag{position:absolute;top:0;left:0;right:0;height:120px;}
  .close{position:absolute;top:16px;right:20px;width:26px;height:26px;border-radius:8px;
    display:flex;align-items:center;justify-content:center;font-size:15px;color:var(--muted);
    cursor:pointer;z-index:9;transition:.2s;}
  .close:hover{color:#fff;background:rgba(251,113,133,.22);transform:rotate(90deg);}
  .wrap{position:absolute;inset:0;z-index:3;display:flex;flex-direction:column;
    align-items:center;padding:40px 30px 24px;}
  .title{font-size:23px;font-weight:800;letter-spacing:3px;
    background:linear-gradient(90deg,#fff,var(--cyan-hi) 40%,var(--blue));
    -webkit-background-clip:text;background-clip:text;color:transparent;
    filter:drop-shadow(0 2px 10px rgba(34,211,238,.35));}
  .sub{font-size:12px;color:#8ea3c8;margin-top:9px;letter-spacing:.6px;}
  .tag{font-size:9.5px;color:#41577f;margin-top:5px;letter-spacing:4px;font-family:Consolas,monospace;}
  /* 反应堆 */
  .reactor{position:relative;width:186px;height:186px;margin:34px 0 26px;
    display:flex;align-items:center;justify-content:center;}
  .ring{position:absolute;border-radius:50%;}
  .halo{inset:-14px;background:radial-gradient(circle,var(--accent),transparent 62%);
    opacity:.22;filter:blur(14px);transition:.5s;}
  .r-outer{inset:0;
    background:conic-gradient(from 0deg,transparent 0deg,var(--accent) 55deg,transparent 150deg,
      var(--vio) 210deg,transparent 250deg,var(--blue) 320deg,transparent 360deg);
    -webkit-mask:radial-gradient(farthest-side,transparent calc(100% - 4px),#000 calc(100% - 4px));
            mask:radial-gradient(farthest-side,transparent calc(100% - 4px),#000 calc(100% - 4px));
    animation:spin 8s linear infinite;filter:drop-shadow(0 0 6px var(--accent));}
  .r-mid{inset:20px;border:1.5px dashed rgba(122,180,255,.45);animation:spin 15s linear infinite reverse;}
  .r-ticks{inset:9px;
    background:repeating-conic-gradient(from 0deg,transparent 0 11deg,rgba(168,246,255,.32) 11deg 11.5deg);
    -webkit-mask:radial-gradient(farthest-side,transparent calc(100% - 8px),#000 calc(100% - 8px));
            mask:radial-gradient(farthest-side,transparent calc(100% - 8px),#000 calc(100% - 8px));
    animation:spin 30s linear infinite;opacity:.55;}
  .core{position:relative;width:98px;height:98px;border-radius:50%;
    background:radial-gradient(circle at 50% 38%,rgba(34,211,238,.30),rgba(9,16,32,.85) 72%);
    border:1px solid rgba(168,246,255,.4);backdrop-filter:blur(4px);
    box-shadow:0 0 30px rgba(34,211,238,.4),inset 0 0 26px rgba(34,211,238,.28);
    display:flex;align-items:center;justify-content:center;
    animation:breathe 2.8s ease-in-out infinite;transition:box-shadow .45s;}
  .core b{font:800 25px Consolas,monospace;letter-spacing:1px;color:#eafcff;
    text-shadow:0 0 12px var(--accent);transition:.3s;}
  body.ok .core b,body.err .core b{color:var(--accent);}
  body.busy .r-outer{animation-duration:1.5s;}
  body.busy .r-mid{animation-duration:2.6s;}
  body.busy .core{animation-duration:1s;}
  /* 按钮 */
  .btn{position:relative;width:300px;height:54px;border-radius:15px;cursor:pointer;overflow:hidden;
    display:flex;align-items:center;justify-content:center;gap:9px;font-size:15px;font-weight:800;
    color:#04121e;letter-spacing:1px;border:1px solid rgba(168,246,255,.55);
    background:linear-gradient(100deg,var(--cyan),var(--blue) 70%,var(--vio));
    box-shadow:0 10px 26px rgba(34,211,238,.30),inset 0 1px 0 rgba(255,255,255,.4);
    transition:transform .2s cubic-bezier(.2,.9,.2,1),box-shadow .28s,filter .2s;}
  .btn:hover{transform:translateY(-3px);filter:brightness(1.1) saturate(1.1);
    box-shadow:0 16px 40px rgba(34,211,238,.5),0 0 34px rgba(139,92,246,.45);}
  .btn:active{transform:translateY(-1px) scale(.98);}
  .btn::after{content:"";position:absolute;top:-30%;left:-70%;width:45%;height:160%;
    background:linear-gradient(100deg,transparent,rgba(255,255,255,.6),transparent);
    transform:skewX(-18deg);animation:sheen 3.6s ease-in-out infinite;}
  body.busy .btn{pointer-events:none;color:#9fc0e0;
    background:linear-gradient(100deg,#274a66,#233a63);box-shadow:none;filter:none;}
  body.busy .btn::after{display:none;}
  .spinner{width:17px;height:17px;border-radius:50%;border:2px solid rgba(255,255,255,.25);
    border-top-color:#dffcff;display:none;animation:spin .8s linear infinite;}
  body.busy .spinner{display:inline-block;}
  .status{margin-top:22px;font-size:13px;min-height:18px;color:var(--muted);
    transition:opacity .3s,color .3s;}
  .status.flash{opacity:0;}
  .path{margin-top:auto;font:11px Consolas,monospace;color:#5a6d90;cursor:pointer;
    padding:8px 14px;border-radius:10px;border:1px solid rgba(90,120,160,.18);
    max-width:452px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;transition:.2s;}
  .path:hover{color:var(--cyan-hi);border-color:rgba(34,211,238,.42);background:rgba(34,211,238,.07);}
  @keyframes spin{to{transform:rotate(360deg);}}
  @keyframes breathe{0%,100%{transform:scale(1);}50%{transform:scale(1.055);}}
  @keyframes sheen{0%,55%{left:-70%;}100%{left:140%;}}
  body.ok{--accent:var(--ok);}body.err{--accent:var(--err);}
</style></head>
<body class="idle">
  <div class="app">
    <div class="aurora"></div><div class="grain"></div>
    <div class="drag" id="drag"></div>
    <div class="close" onclick="B&&B.close()">✕</div>
    <div class="wrap">
      <div class="title">SC2 · DPI FIX</div>
      <div class="sub">银河编辑器 高DPI 字体溢出修复 · 外置内存补丁</div>
      <div class="tag">/// MEMORY&nbsp;PATCH&nbsp;ENGINE ///</div>
      <div class="reactor">
        <div class="ring halo"></div><div class="ring r-ticks"></div>
        <div class="ring r-outer"></div><div class="ring r-mid"></div>
        <div class="core"><b id="core">DPI</b></div>
      </div>
      <div class="btn" id="btn" onclick="onLaunch()">
        <span class="spinner"></span><span id="btnlbl">▶ 启动修复版编辑器</span>
      </div>
      <div class="status" id="status">初始化…</div>
      <div class="path" id="path" onclick="onPick()">» 定位编辑器中…</div>
    </div>
  </div>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
  let B=null;
  const $=s=>document.querySelector(s);
  const setState=s=>document.body.className=s;
  function setStatus(t,c){const e=$('#status');e.classList.add('flash');
    setTimeout(()=>{e.textContent=t;e.style.color=c||'var(--muted)';e.classList.remove('flash');},170);}
  const short=p=>p&&p.length>58?p.slice(0,28)+'…'+p.slice(-28):p;
  const setPath=p=>$('#path').textContent=p?('» '+short(p)+'  [更换]'):'» 点此选择 SC2Editor_x64.exe';
  function onLaunch(){if(document.body.classList.contains('busy')||!B)return;
    setState('busy');$('#core').textContent='···';$('#btnlbl').textContent='PATCHING…';
    setStatus('初始化补丁引擎…','var(--cyan)');B.launch();}
  function onPick(){if(document.body.classList.contains('busy')||!B)return;
    B.pick(p=>{if(p){setPath(p);setStatus('已选择编辑器','var(--cyan)');}});}
  function onEvent(kind,msg){
    if(kind==='status')setStatus(msg,'var(--cyan)');
    else if(kind==='done'){setState('ok');$('#core').textContent='✓';setStatus(msg,'var(--ok)');}
    else if(kind==='fail'){setState('err');$('#core').textContent='!';setStatus(msg,'var(--err)');}}
  new QWebChannel(qt.webChannelTransport,function(ch){
    B=ch.objects.backend;
    B.statusEvent.connect(onEvent);
    B.get_editor(function(p){setPath(p);
      setStatus(p?'已定位编辑器 · 准备就绪':'未自动找到,请点下方选择',p?'var(--cyan)':'var(--err)');});
    $('#drag').addEventListener('mousedown',()=>B.start_drag());
  });
</script></body></html>
"""


class Backend(QObject):
    statusEvent = Signal(str, str)

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.editor = core.find_editor()

    @Slot(result=str)
    def get_editor(self):
        return self.editor or ""

    @Slot(result=str)
    def pick(self):
        p, _ = QFileDialog.getOpenFileName(
            self.window, "选择 SC2Editor_x64.exe", "",
            "SC2Editor (SC2Editor_x64.exe);;可执行文件 (*.exe)")
        if p:
            self.editor = p
        return p or ""

    @Slot()
    def launch(self):
        threading.Thread(target=self._work, daemon=True).start()

    def _work(self):
        try:
            core.launch_patched(self.editor, lambda m: self.statusEvent.emit("status", m))
            self.statusEvent.emit("done", "已启动 · 官方依赖汉化已加载 ✓")
        except core.PatchError as e:
            self.statusEvent.emit("fail", str(e))
        except Exception as e:  # noqa
            self.statusEvent.emit("fail", f"错误: {e}")

    @Slot()
    def start_drag(self):
        h = self.window.windowHandle()
        if h:
            h.startSystemMove()

    @Slot()
    def close(self):
        self.window.close()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SC2 银河编辑器 DPI 修复")
        self.setFixedSize(540, 500)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.view = QWebEngineView(self)
        self.view.page().setBackgroundColor(QColor(0, 0, 0, 0))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.view)

        self.backend = Backend(self)
        self.channel = QWebChannel()
        self.channel.registerObject("backend", self.backend)
        self.view.page().setWebChannel(self.channel)
        self.view.setHtml(HTML, QUrl("about:blank"))


def main():
    app = QApplication([])
    w = MainWindow()
    # 居中偏上
    scr = app.primaryScreen().geometry()
    w.move((scr.width() - 540) // 2, scr.height() // 3 - 40)
    w.show()
    app.exec()


if __name__ == "__main__":
    main()
