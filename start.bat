@echo off
setlocal EnableDelayedExpansion
title E-Voting System — Launcher
color 0A

echo.
echo  ============================================
echo    E-Voting System — Auto Launcher
echo  ============================================
echo.

:: ── Step 0: Backend folder mein jao ─────────────────────────────────────────
cd /d "%~dp0Backend"
if errorlevel 1 (
    echo  [ERROR] Backend folder nahi mila.
    pause & exit /b 1
)

:: ── Step 1: Python check ─────────────────────────────────────────────────────
echo  [1/5] Python check kar raha hoon...
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python nahi mila. Python 3.10+ install karein.
    echo          https://www.python.org/downloads/
    pause & exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo         Python %PY_VER% mila. OK
echo.

:: ── Step 2: venv check / create ──────────────────────────────────────────────
echo  [2/5] Virtual environment check kar raha hoon...
if exist "venv\Scripts\activate.bat" (
    echo         venv pehle se maujood hai. Skip.
) else (
    echo         venv nahi mila — bana raha hoon...
    python -m venv venv
    if errorlevel 1 (
        echo  [ERROR] venv banana fail hua.
        pause & exit /b 1
    )
    echo         venv ban gaya. OK
)
echo.

:: ── Activate venv ────────────────────────────────────────────────────────────
call venv\Scripts\activate.bat

:: ── Step 3: Dependencies install ─────────────────────────────────────────────
echo  [3/5] Dependencies check kar raha hoon...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo         Packages install ho rahe hain...
    pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo  [ERROR] pip install fail hua.
        pause & exit /b 1
    )
    echo         Packages install ho gaye. OK
) else (
    echo         Packages pehle se installed hain. Skip.
)
echo.

:: ── Step 4: MongoDB check ─────────────────────────────────────────────────────
echo  [4/5] MongoDB check kar raha hoon...

:: MongoDB service check karo
sc query MongoDB >nul 2>&1
if errorlevel 1 (
    :: Service nahi mila — mongod directly check karo
    tasklist /FI "IMAGENAME eq mongod.exe" 2>nul | find /I "mongod.exe" >nul
    if errorlevel 1 (
        echo         MongoDB chal nahi raha — start karne ki koshish kar raha hoon...
        :: Common install paths try karo
        set MONGO_FOUND=0
        for %%P in (
            "C:\Program Files\MongoDB\Server\7.0\bin\mongod.exe"
            "C:\Program Files\MongoDB\Server\6.0\bin\mongod.exe"
            "C:\Program Files\MongoDB\Server\5.0\bin\mongod.exe"
        ) do (
            if exist %%P (
                start "" /B %%P --dbpath "C:\data\db" >nul 2>&1
                set MONGO_FOUND=1
            )
        )
        if !MONGO_FOUND!==0 (
            echo.
            echo  [WARN] MongoDB automatically start nahi ho saka.
            echo         Please manually start karein:
            echo           - MongoDB Compass open karein, ya
            echo           - Services mein MongoDB start karein, ya
            echo           - mongod.exe manually run karein
            echo.
            echo         Phir bhi continue karta hoon...
        ) else (
            echo         MongoDB start ho raha hai — 3 second wait...
            timeout /t 3 /nobreak >nul
            echo         OK
        )
    ) else (
        echo         MongoDB pehle se chal raha hai. OK
    )
) else (
    :: Service mili — running hai?
    sc query MongoDB | find "RUNNING" >nul
    if errorlevel 1 (
        echo         MongoDB service start kar raha hoon...
        net start MongoDB >nul 2>&1
        timeout /t 2 /nobreak >nul
        echo         OK
    ) else (
        echo         MongoDB service chal rahi hai. OK
    )
)
echo.

:: ── Step 5: Backend start karo ───────────────────────────────────────────────
echo  [5/5] Backend server start kar raha hoon...
echo         URL: http://localhost:5000
echo.

:: Backend ko alag window mein chalao
start "E-Voting Backend" cmd /k "cd /d "%~dp0Backend" && call venv\Scripts\activate.bat && echo. && echo  Backend chal raha hai — http://localhost:5000 && echo  Band karne ke liye Ctrl+C dabao && echo. && python app.py"

:: Server ko thoda waqt do start hone ke liye
echo         Server start ho raha hai — 3 second wait...
timeout /t 3 /nobreak >nul

:: Health check karo
echo         Health check...
curl -s http://localhost:5000/api/ping >nul 2>&1
if errorlevel 1 (
    echo         [WARN] Server abhi ready nahi — 3 second aur wait...
    timeout /t 3 /nobreak >nul
)

:: ── Frontend open karo ───────────────────────────────────────────────────────
echo.
echo  ============================================
echo    Frontend browser mein khul raha hai...
echo  ============================================
echo.

:: Frontend index.html Flask ke zariye serve hoti hai
start "" "http://localhost:5000"

echo  Sab kuch tayyar hai!
echo.
echo  Links:
echo    Main Site  :  http://localhost:5000
echo    Admin Panel:  http://localhost:5000/admin/index.html
echo    API Ping   :  http://localhost:5000/api/ping
echo.
echo  Backend band karne ke liye us window mein Ctrl+C dabao.
echo.
pause
endlocal