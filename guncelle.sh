#!/bin/bash

# Renkler
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}♻️  PhD Terminal Otomatik Güncelleme Aracı Başlatılıyor...${NC}"
echo "------------------------------------------------"

# Scriptin olduğu dizine git
cd "$(dirname "$0")"

# Değişiklik kontrolü
if [ -z "$(git status --porcelain)" ]; then 
  echo -e "${RED}⚠️  Herhangi bir değişiklik bulunamadı.${NC}"
  # exit 0 # Değişiklik yoksa bile push denemek isteyebilir (commit edilmemiş olabilir)
fi

# 1. Tüm değişiklikleri ekle
echo -e "${BLUE}📦 Dosyalar ekleniyor...${NC}"
git add .

# 2. Mesaj oluştur
TARIH=$(date "+%d.%m.%Y %H:%M:%S")
if [ -z "$1" ]; then
    MESAJ="Güncelleme: $TARIH"
else
    MESAJ="$1 ($TARIH)"
fi

echo -e "${BLUE}💾 Commit oluşturuluyor: '${MESAJ}'${NC}"
git commit -m "$MESAJ"

# 3. GitHub'a gönder
echo -e "${BLUE}🚀 GitHub'a gönderiliyor...${NC}"
git push origin main

# Sonuç kontrolü
if [ $? -eq 0 ]; then
  echo "------------------------------------------------"
  echo -e "${GREEN}✅ İŞLEM BAŞARILI!${NC}"
  echo -e "${GREEN}🌐 Değişiklikler GitHub'a gönderildi. Railway otomatik olarak güncellenecek.${NC}"
else
  echo "------------------------------------------------"
  echo -e "${RED}❌ HATA OLUŞTU!${NC}"
  echo "Lütfen uzak depo (remote) bağlantınızı kontrol edin."
  echo "Not: 'git remote add origin <URL>' komutunu çalıştırdığınızdan emin olun."
fi
