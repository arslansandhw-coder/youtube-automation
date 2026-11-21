@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Umrah Asaan - Videos banayein aur PRIVATE upload karein
set "PYTHONUTF8=1"
set "PATH=%PATH%;%LocalAppData%\Programs\Python\Launcher;%LocalAppData%\Programs\Python\Python312;%LocalAppData%\Programs\Python\Python312\Scripts;%LocalAppData%\Microsoft\WinGet\Links"

set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY (
  echo [X] Python nahi mila. Pehle "1-setup.bat" chalayein.
  goto :end
)
if not exist "client_secret.json" (
  echo [X] client_secret.json is folder mein nahi hai.
  goto :end
)

echo Har "approved: true" script ki video banegi aur YouTube par PRIVATE upload hogi.
echo publish_at ke waqt woh khud public ho jayegi.
echo Pehli dafa browser khulega: channel wale Gmail se login kar ke Allow dabayein.
echo.
%PY% run.py

:end
echo.
pause
endlocal
