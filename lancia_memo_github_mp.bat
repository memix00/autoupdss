@echo off
cd /d C:\Users\memixtv\Documents\IPTV_auto\autoupdss

taskkill /IM brave.exe /F >nul 2>&1

python aggiorna_memo_github_mp.py

pause