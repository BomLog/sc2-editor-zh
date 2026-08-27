#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SC2 银河编辑器 DPI 修复 —— WebView(HTML/CSS)高级动画版
=======================================================
UI: pywebview(WebView2)承载 HTML/CSS,动画走浏览器合成器,丝滑 60fps。
内核: dpifix_core.launch_patched —— 挂起启动 + 内存 NOP 两处 DPI 调用 + 恢复。
      不改文件 / 不注入环境变量(不污染测试游戏) / 单实例保护 / 自动定位编辑器。
"""
import json
import logging
import sys
import threading

# pywebview + pythonnet 在 Python 3.14 下会因内省 .NET 辅助功能对象在
# "构造错误日志" 时无限递归刷屏 -> 提高日志阈值, 让它不去格式化那条消息。
logging.disable(logging.ERROR)
for _n in ("pywebview", "webview", "pythonnet", "clr"):
    logging.getLogger(_n).setLevel(logging.CRITICAL)
sys.setrecursionlimit(10000)

import webview

import dpifix_core as core

HTML = r"""
<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<style>
  :root{
    --cyan:#22d3ee; --cyan-hi:#8bf6ff; --blue:#3b82f6;
    --ok:#34d399; --err:#fb7185; --text:#dbe7f7; --muted:#5c6f8c;
    --accent:var(--cyan);
  }
  *{margin:0;padding:0;box-sizing:border-box;user-select:none;-webkit-user-select:none;}
  html,body{width:100%;height:100%;overflow:hidden;font-family:"Microsoft YaHei UI","Segoe UI",sans-serif;}
  body{
    background:radial-gradient(120% 120% at 50% 0%, #0e1830 0%, #070b14 55%, #05070d 100%);
    color:var(--text);position:relative;
  }
  /* 极光旋转辉光 */
  .aurora{position:absolute;left:50%;top:42%;width:820px;height:820px;transform:translate(-50%,-50%);
    background:conic-gradient(from 0deg, transparent 0%, rgba(34,211,238,.20) 20%, transparent 42%,
      rgba(59,130,246,.18) 62%, transparent 84%);
    filter:blur(46px);opacity:.7;animation:spin 18s linear infinite;pointer-events:none;}
  body.ok{--accent:var(--ok);}  body.err{--accent:var(--err);}
  /* 关闭 */
  .close{position:absolute;top:14px;right:18px;font-size:17px;color:var(--muted);cursor:pointer;
    z-index:9;transition:color .2s, transform .2s;}
  .close:hover{color:var(--err);transform:rotate(90deg);}
  /* 卡片 */
  .wrap{position:relative;z-index:2;height:100%;display:flex;flex-direction:column;align-items:center;
    padding:34px 30px 22px;}
  .title{font-size:22px;font-weight:800;letter-spacing:2px;
    background:linear-gradient(90deg,var(--cyan-hi),var(--blue));-webkit-background-clip:text;
    background-clip:text;color:transparent;}
  .sub{font-size:12px;color:var(--muted);margin-top:7px;letter-spacing:.5px;}
  .tag{font-size:10px;margin-top:3px;letter-spacing:3px;
    font-family:Consolas,monospace;color:#39507a;}
  /* 反应堆 */
  .reactor{position:relative;width:180px;height:180px;margin:30px 0 24px;
    display:flex;align-items:center;justify-content:center;}
  .ring{position:absolute;border-radius:50%;}
  .r-outer{inset:0;
    background:conic-gradient(from 0deg, transparent 0deg, var(--accent) 40deg, transparent 130deg,
      var(--blue) 200deg, transparent 300deg, var(--accent) 360deg);
    -webkit-mask:radial-gradient(farthest-side, transparent calc(100% - 5px), #000 calc(100% - 5px));
            mask:radial-gradient(farthest-side, transparent calc(100% - 5px), #000 calc(100% - 5px));
    animation:spin 9s linear infinite;filter:drop-shadow(0 0 8px var(--accent));opacity:.95;}
  .r-mid{inset:22px;border:1.5px dashed rgba(122,180,255,.5);animation:spin 14s linear infinite reverse;}
  .r-ticks{inset:10px;
    background:repeating-conic-gradient(from 0deg, transparent 0 10deg, rgba(139,246,255,.35) 10deg 10.6deg);
    -webkit-mask:radial-gradient(farthest-side, transparent calc(100% - 9px), #000 calc(100% - 9px));
            mask:radial-gradient(farthest-side, transparent calc(100% - 9px), #000 calc(100% - 9px));
    animation:spin 26s linear infinite;opacity:.6;}
  .core{position:relative;width:96px;height:96px;border-radius:50%;
    background:radial-gradient(circle at 50% 40%, rgba(34,211,238,.28), rgba(10,18,36,.7) 70%);
    border:1px solid rgba(139,246,255,.35);
    box-shadow:0 0 24px rgba(34,211,238,.35), inset 0 0 22px rgba(34,211,238,.25);
    display:flex;align-items:center;justify-content:center;
    animation:breathe 2.6s ease-in-out infinite;transition:box-shadow .4s;}
  body.ok .core{box-shadow:0 0 28px rgba(52,211,153,.5), inset 0 0 22px rgba(52,211,153,.3);}
  body.err .core{box-shadow:0 0 28px rgba(251,113,133,.5), inset 0 0 22px rgba(251,113,133,.3);}
  .core b{font:800 24px Consolas,monospace;letter-spacing:1px;
    background:linear-gradient(90deg,var(--cyan-hi),#fff);-webkit-background-clip:text;background-clip:text;
    color:transparent;transition:.3s;}
  body.ok .core b, body.err .core b{background:none;color:var(--accent);-webkit-text-fill-color:var(--accent);}
  /* 忙时加速 */
  body.busy .r-outer{animation-duration:1.6s;}
  body.busy .r-mid{animation-duration:3s;}
  body.busy .core{animation-duration:1.1s;}
  /* 按钮 */
  .btn{position:relative;width:288px;height:52px;border-radius:14px;cursor:pointer;overflow:hidden;
    display:flex;align-items:center;justify-content:center;gap:8px;font-size:15px;font-weight:700;
    color:#04121a;letter-spacing:1px;border:1px solid rgba(139,246,255,.6);
    background:linear-gradient(100deg,var(--cyan),var(--blue));
    box-shadow:0 8px 22px rgba(34,211,238,.28), inset 0 1px 0 rgba(255,255,255,.35);
    transition:transform .18s cubic-bezier(.2,.8,.2,1), box-shadow .25s, filter .2s;}
  .btn:hover{transform:translateY(-2px);filter:brightness(1.08);
    box-shadow:0 12px 30px rgba(34,211,238,.5), 0 0 26px rgba(59,130,246,.4);}
  .btn:active{transform:translateY(0) scale(.985);}
  .btn::after{content:"";position:absolute;top:0;left:-60%;width:40%;height:100%;
    background:linear-gradient(100deg,transparent,rgba(255,255,255,.55),transparent);
    transform:skewX(-20deg);animation:sheen 3.4s ease-in-out infinite;}
  body.busy .btn{pointer-events:none;filter:grayscale(.4) brightness(.8);
    background:linear-gradient(100deg,#26506b,#243b66);color:#8fb3d6;}
  .btn .spinner{width:16px;height:16px;border-radius:50%;border:2px solid rgba(255,255,255,.3);
    border-top-color:#dff;display:none;animation:spin .8s linear infinite;}
  body.busy .btn .spinner{display:inline-block;}
  /* 状态 */
  .status{margin-top:20px;font-size:13px;min-height:18px;color:var(--muted);
    transition:opacity .35s, color .35s;opacity:1;}
  .status.flash{opacity:0;}
  /* 路径 */
  .path{margin-top:auto;font:11px Consolas,monospace;color:var(--muted);cursor:pointer;
    padding:7px 12px;border-radius:9px;border:1px solid rgba(90,120,160,.2);
    max-width:440px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;transition:.2s;}
  .path:hover{color:var(--cyan-hi);border-color:rgba(34,211,238,.4);background:rgba(34,211,238,.06);}
  @keyframes spin{to{transform:rotate(360deg);}}
  @keyframes breathe{0%,100%{transform:scale(1);}50%{transform:scale(1.06);}}
  @keyframes sheen{0%,60%{left:-60%;}100%{left:130%;}}
</style>
</head>
<body class="idle">
  <div class="aurora"></div>
  <div class="close" onclick="pywebview.api.close()">✕</div>
  <div class="wrap">
    <div class="title">SC2 · DPI FIX</div>
    <div class="sub">银河编辑器 高DPI 字体溢出修复 · 外置内存补丁</div>
    <div class="tag">/// MEMORY&nbsp;PATCH&nbsp;ENGINE ///</div>
    <div class="reactor">
      <div class="ring r-ticks"></div>
      <div class="ring r-outer"></div>
      <div class="ring r-mid"></div>
      <div class="core"><b id="core">DPI</b></div>
    </div>
    <div class="btn" id="btn" onclick="onLaunch()">
      <span class="spinner"></span><span id="btnlbl">▶ 启动修复版编辑器</span>
    </div>
    <div class="status" id="status">初始化…</div>
    <div class="path" id="path" onclick="onPick()">» 定位编辑器中…</div>
  </div>
<script>
  const $=s=>document.querySelector(s);
  function setState(s){document.body.className=s;}
  function setStatus(txt,cls){
    const el=$('#status');el.classList.add('flash');
    setTimeout(()=>{el.textContent=txt;el.style.color=cls||'var(--muted)';el.classList.remove('flash');},180);
  }
  function shortPath(p){return p&&p.length>56?p.slice(0,27)+'…'+p.slice(-27):p;}
  function setPath(p){$('#path').textContent = p ? ('» '+shortPath(p)+'  [更换]') : '» 点此选择 SC2Editor_x64.exe';}

  // Python -> JS 事件入口
  window.appEvent=function(kind,msg){
    if(kind==='status'){setStatus(msg,'var(--cyan)');}
    else if(kind==='done'){setState('ok');$('#core').textContent='✓';setStatus(msg,'var(--ok)');}
    else if(kind==='fail'){setState('err');$('#core').textContent='!';setStatus(msg,'var(--err)');}
  };
  function onLaunch(){
    if(document.body.classList.contains('busy'))return;
    setState('busy');$('#core').textContent='···';$('#btnlbl').textContent='PATCHING…';
    setStatus('初始化补丁引擎…','var(--cyan)');
    pywebview.api.launch();
  }
  async function onPick(){
    if(document.body.classList.contains('busy'))return;
    const p=await pywebview.api.pick();
    if(p){setPath(p);setStatus('已选择编辑器','var(--cyan)');}
  }
  window.addEventListener('pywebviewready',async()=>{
    const p=await pywebview.api.get_editor();
    setPath(p);
    setStatus(p?'已定位编辑器 · 准备就绪':'未自动找到,请点下方选择', p?'var(--cyan)':'var(--err)');
  });
</script>
</body>
</html>
"""


class Api:
    def __init__(self):
        self.window = None
        self.editor = core.find_editor()

    def get_editor(self):
        return self.editor or ""

    def pick(self):
        try:
            res = self.window.create_file_dialog(
                webview.OPEN_DIALOG, allow_multiple=False,
                file_types=("SC2Editor (SC2Editor_x64.exe)", "可执行文件 (*.exe)"))
            if res:
                self.editor = res[0]
                return self.editor
        except Exception:
            pass
        return ""

    def launch(self):
        threading.Thread(target=self._work, daemon=True).start()

    def _work(self):
        try:
            core.launch_patched(self.editor, lambda m: self._push("status", m))
            self._push("done", "已启动 · 官方依赖汉化已加载 ✓")
        except core.PatchError as e:
            self._push("fail", str(e))
        except Exception as e:  # noqa
            self._push("fail", f"错误: {e}")

    def close(self):
        if self.window:
            self.window.destroy()

    def _push(self, kind, msg):
        if self.window:
            try:
                self.window.evaluate_js(
                    f"window.appEvent && appEvent({json.dumps(kind)}, {json.dumps(msg)})")
            except Exception:
                pass


def main():
    api = Api()
    win = webview.create_window(
        "SC2 银河编辑器 DPI 修复", html=HTML, js_api=api,
        width=520, height=480, frameless=True, easy_drag=True,
        resizable=False, background_color="#05070d")
    api.window = win
    webview.start()


if __name__ == "__main__":
    main()
