@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Umrah Asaan - Test video (upload nahi hogi)
set "PYTHONUTF8=1"
set "PATH=%PATH%;%LocalAppData%\Programs\Python\Launcher;%LocalAppData%\Programs\Python\Python312;%LocalAppData%\Programs\Python\Python312\Scripts;%LocalAppData%\Microsoft\WinGet\Links"

set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY (
  echo [X] Python nahi mila. Pehle "1-setup.bat" chalayein.
  goto :end
)

echo Pehli script ki namoona video ban rahi hai. YouTube par upload NAHI hoga.
echo.
%PY% run.py --preview
echo.
echo Videos "output" folder mein hain. Har folder mein video.mp4 aur thumbnail.png dekhein.
if exist output start "" "output"

:end
echo.
pause
endlocal
