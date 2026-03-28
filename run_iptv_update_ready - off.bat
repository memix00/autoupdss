@echo off
setlocal

title IPTV Auto Update + Brave CDP + Shutdown

set "WORKDIR=C:\Users\memixtv\Documents\IPTV_auto\autoupdss"
set "SCRIPT=aggiorna_memo_github_mp.py"
set "PYTHON=python"
set "BRAVE=C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
set "CDP_PORT=9222"
set "BRAVE_PROFILE=%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data IPTVCDP"

echo.
echo [INFO] Avvio procedura IPTV...

if not exist "%WORKDIR%" (
    echo [ERRORE] Cartella non trovata:
    echo %WORKDIR%
    pause
    exit /b 1
)

cd /d "%WORKDIR%"
if errorlevel 1 (
    echo [ERRORE] Impossibile entrare nella cartella di lavoro.
    pause
    exit /b 1
)

if not exist "%BRAVE%" (
    echo [ERRORE] Brave non trovato:
    echo %BRAVE%
    pause
    exit /b 1
)

echo [INFO] Avvio Brave con remote debugging sulla porta %CDP_PORT%...
start "Brave CDP" "%BRAVE%" --remote-debugging-port=%CDP_PORT% --user-data-dir="%BRAVE_PROFILE%"

echo [INFO] Attendo 8 secondi per inizializzare Brave...
timeout /t 8 /nobreak >nul

echo [INFO] Avvio script Python: %SCRIPT%
%PYTHON% "%SCRIPT%"
set "PY_EXIT=%ERRORLEVEL%"

if not "%PY_EXIT%"=="0" (
    echo.
    echo [ERRORE] Lo script Python e' terminato con codice %PY_EXIT%.
    echo [INFO] Nessuno spegnimento eseguito per sicurezza.
    pause
    exit /b %PY_EXIT%
)

echo.
echo [INFO] Script completato correttamente.
echo [INFO] Attendo 60 secondi per sicurezza ^(push GitHub ecc^)...
timeout /t 60 /nobreak >nul

echo [INFO] Spegnimento completo del PC...
shutdown /s /t 0

endlocal
exit /b 0
