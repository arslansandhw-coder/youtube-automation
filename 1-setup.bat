@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Umrah Asaan - Setup

echo ============================================
echo   Umrah Asaan - pehli dafa ka setup
echo ============================================
echo.

rem Make freshly installed tools visible in this window too
set "PATH=%PATH%;%LocalAppData%\Programs\Python\Launcher;%LocalAppData%\Programs\Python\Python312;%LocalAppData%\Programs\Python\Python312\Scripts;%LocalAppData%\Microsoft\WinGet\Links"

where winget >nul 2>&1
if errorlevel 1 (
  echo [X] winget nahi mila. Microsoft Store se "App Installer" update/install karein, phir yeh file dobara chalayein.
  goto :end
)

rem ---------- 1. Python ----------
call :findpy
if not defined PY (
  echo [1/4] Python install ho raha hai...
  winget install -e --id Python.Python.3.12 --scope user --accept-source-agreements --accept-package-agreements
  call :findpy
)
if not defined PY (
  echo [X] Python install nahi hua. Is window ko band kar ke yeh file dobara chalayein.
  goto :end
)
echo [1/4] Python theek hai: %PY%

rem ---------- 2. FFmpeg ----------
where ffmpeg >nul 2>&1
if errorlevel 1 (
  echo [2/4] FFmpeg install ho raha hai...
  winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
)
where ffmpeg >nul 2>&1
if errorlevel 1 (
  echo [X] FFmpeg abhi nazar nahi aa raha. Is window ko band kar ke yeh file dobara chalayein.
  goto :end
)
echo [2/4] FFmpeg theek hai.

rem ---------- 3. Python packages ----------
echo [3/4] Zaroori packages install ho rahe hain...
%PY% -m pip install --upgrade pip >nul
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
  echo [X] Packages install nahi hue. Upar wala error Claude ko bhejein.
  goto :end
)
echo [3/4] Packages theek hain.

rem ---------- 4. Checks ----------
if exist "client_secret.json" (
  echo [4/4] client_secret.json mil gayi.
) else (
  echo [!] client_secret.json is folder mein nahi mili. Upload se pehle yahan rakhein.
)
dir /b "assets\common\*.jpg" "assets\common\*.jpeg" "assets\common\*.png" >nul 2>&1
if errorlevel 1 (
  echo [!] assets\common mein koi tasveer nahi. Video saade rang ke background par banegi.
)

echo.
echo ============================================
echo   Setup mukammal. Ab "2-test-video.bat" chalayein.
echo ============================================
goto :end

:findpy
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3" && goto :eof
python --version >nul 2>&1 && set "PY=python" && goto :eof
goto :eof

:end
echo.
pause
endlocal
