# PhD Terminal - Akilli Baslatici (PowerShell)

Write-Host "`n  =========================================" -ForegroundColor Green
Write-Host "       PhD TERMINAL YONETICI (PS)        " -ForegroundColor Green
Write-Host "  =========================================`n" -ForegroundColor Green

# Python kontrolu
try {
    $pythonVersion = python --version
    Write-Host "[OK] Python bulundu." -ForegroundColor Gray
} catch {
    Write-Host "[HATA] Python bulunamadi! Lutfen Python'in yuklu oldugundan emin olun." -ForegroundColor Red
    Read-Host "Kapatmak icin Enter'a basin..."
    exit
}

# start_all.py dosyasini calistir
python start_all.py
