import subprocess
import time
import os
import sys
import webbrowser

def start_services():
    print("\n" + "="*45)
    print("      PhD TERMİNAL - AKILLI BAŞLATICI")
    print("="*45 + "\n")

    try:
        # 1. Backend'i Başlat (Port 8000)
        print("[1/3] Backend (FastAPI) başlatılıyor...")
        backend_proc = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=os.getcwd()
        )
        
        # Backend'in açılması için kısa bir bekleme
        time.sleep(2)

        # 2. Frontend'i Başlat (Port 3000)
        print("[2/3] Frontend (React/Vite) hazırlanıyor...")
        frontend_dir = os.path.join(os.getcwd(), "frontend")
        
        # Windows'ta npm komutu için shell=True gerekir
        frontend_proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir,
            shell=True
        )

        # 3. Tarayıcıyı Aç
        print("[3/3] Tarayıcı açılıyor...")
        time.sleep(3)
        webbrowser.open("http://localhost:3000")

        print("\n" + "-"*45)
        print("✅ BAŞARILI! PhD Terminal şu an çalışıyor.")
        print("🔗 Frontend:  http://localhost:3000")
        print("🔗 API:       http://localhost:8000")
        print("-"*45 + "\n")
        print("💡 İpucu: Kapatmak için bu pencerede CTRL+C tuşlarına bas.\n")

        # İşlemleri açık tut
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Kapatılıyor...")
            backend_proc.terminate()
            # Frontend proc shell üzerinden çalıştığı için taskkill gerekebilir ama terminate deneyelim
            frontend_proc.terminate()
            
    except Exception as e:
        print(f"\n❌ BİR HATA OLUŞTU: {e}")
        input("Çıkmak için bir tuşa basın...")

if __name__ == "__main__":
    start_services()
