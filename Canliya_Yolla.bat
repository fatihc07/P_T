@echo off
TITLE Hisse PhD - Canliya Gonderiliyor (GITHUB)
echo.
echo  =========================================
echo    DEGISIKLIKLER CANLIYA GONDERILIYOR...
echo  =========================================
echo.

:: Değişiklikleri ekle
git add .

:: Kullanıcıdan commit mesajı sor
set /p msg="Ne degistirdin? (Opsiyonel): "
if "%msg%"=="" set msg="Hizli guncelleme (%date% %time%)"

:: Commit ve Push (Her şey GitHub'a oradan Canlıya)
git commit -m "%msg%"
git push origin main

echo.
echo  =========================================
echo  ✅ Islem tamam! GitHub degisikligi aldi. 
echo  Netlify ve Railway simdi derlemeye basladi.
echo  -----------------------------------------
echo.
pause
