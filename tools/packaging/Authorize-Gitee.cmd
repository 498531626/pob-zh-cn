@echo off
cd /d "%~dp0..\.."
python tools\packaging\authorize_gitee.py
pause
