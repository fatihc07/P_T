@echo off
TITLE PhD Terminal - YEREL CALISTIRICI
echo.
echo  =========================================
echo    PHD TERMINAL YERELDE BASLATILIYOR...
echo  =========================================
echo.

:: Python yüklü mü kontrol et
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python bulunamadi! Lutfen Python yukleyin.
    pause
    exit /b
)

:: Script'i çalıştır
python start_all.py

pause
