@echo off
TITLE PhD Terminal - Canliya Gonderiliyor
echo.
echo  =========================================
echo    DEGISIKLIKLER CANLIYA GONDERILIYOR...
echo  =========================================
echo.

:: Değişiklikleri ekle
git add .

:: Commit mesajı sor (veya otomatik at)
set /p msg="Ne degistirdin? (Opsiyonel): "
if "%msg%"=="" set msg="Hizli guncelleme (%date% %time%)"

:: Commit ve Push
git commit -m "%msg%"
git push origin main

echo.
echo  =========================================
echo  ✅ Islem tamam! GitHub degisikligi aldi. 
echo  Netlify ve Railway simdi derlemeye basladi.
echo  -----------------------------------------
echo.
pause
