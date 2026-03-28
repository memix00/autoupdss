@echo off
cd /d C:\Users\memixtv\Documents\IPTV_auto\autoupdss

taskkill /IM brave.exe /F >nul 2>&1

python aggiorna_memo_github_mp.py

echo [%date% %time%] Fine script, attendo 60 secondi >> iptv_task_log.txt
timeout /t 60 /nobreak

powercfg -hibernate off
powershell -command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState('Suspend', $false, $false)"

exit