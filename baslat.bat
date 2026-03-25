@echo off
TITLE PhD Terminal Launcher
echo Python akilli yonetici baslatiliyor...

:: Oncelikle sistemde python yuklu mu kontrol et
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Python bulunamadi! Lutfen Python'in yuklu ve PATH'e ekli oldugundan emin olun.
    pause
    exit /b
)

:: start_all.py calistir
python start_all.py
pause
