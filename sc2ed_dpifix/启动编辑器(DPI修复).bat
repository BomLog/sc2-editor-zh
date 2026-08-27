@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem 优先用 py 启动器, 没有则回退 python
where py >nul 2>nul && (py -3 sc2ed_dpifix.py %*) || (python sc2ed_dpifix.py %*)
if errorlevel 1 (
  echo.
  echo [出错] 请查看上方信息。
  pause
)
