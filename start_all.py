import subprocess
import time
import os
import webbrowser
import sys

def start_app():
    print("\n" + "="*45)
    print("      🚀 PhD TERMINAL ZEKI YÖNETICI 🚀")
    print("="*45 + "\n")
    
    processes = []

    try:
        # 1. Backend'i Başlat
        print("[1/3] Backend (Python/FastAPI) ayağa kaldırılıyor...")
        
        # Sanal ortam kontrolü
        venv_python = os.path.join(".venv", "Scripts", "python.exe")
        python_exe = venv_python if os.path.exists(venv_python) else "python"
        
        # Backend sürecini başlat
        # Python script'ini doğrudan çalıştırmak yerine, root dizindeki main.py'yi çalıştırıyoruz.
        backend_proc = subprocess.Popen([python_exe, "main.py"], shell=False)
        processes.append(backend_proc)

        # 2. Frontend'i Başlat
        print("[2/3] Frontend (React/Vite) hazırlanıyor...")
        frontend_dir = os.path.join(os.getcwd(), "frontend")
        
        # Windows'ta npm komutu için shell=True gerekir
        # npm run dev genellikle log basar, bu logları aynı pencerede göreceğiz.
        frontend_proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir,
            shell=True
        )
        processes.append(frontend_proc)

        # 3. Hazır Olmasını Bekle ve Tarayıcıyı Aç
        print("[3/3] Servisler ayağa kalkıyor, bekleniyor (5sn)...")
        time.sleep(5) 
        
        print("\n" + "-"*45)
        print("✅ BAŞARILI! PhD Terminal şu an çalışıyor.")
        print("🔗 Frontend:  http://localhost:5173")
        print("🔗 API:       http://localhost:8000")
        print("-" * 45 + "\n")
        
        # Tarayıcıyı otomatik aç
        webbrowser.open("http://localhost:5173")

        print("💡 İpucu: Kapatmak için bu pencerede CTRL+C tuşlarına bas.")
        print("Loglar aşağıda akacaktır:\n" + "-"*30)

        # Ana süreci ayakta tutmak için bekliyoruz
        while True:
            time.sleep(1)
            # Süreçlerden biri çökerse uyar
            if backend_proc.poll() is not None:
                print("\n❌ Backend beklenmedik şekilde durdu!")
                break
            if frontend_proc.poll() is not None:
                print("\n❌ Frontend beklenmedik şekilde durdu!")
                break

    except KeyboardInterrupt:
        print("\n🛑 Program kapatılıyor, süreçler sonlandırılıyor...")
    except Exception as e:
        print(f"\n❌ Bir hata oluştu: {e}")
    finally:
        # Tüm süreçleri temizce kapat
        for p in processes:
            try:
                if os.name == 'nt': # Windows için ağaç yapısındaki tüm alt süreçleri (taskkill) kapat
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(p.pid)], 
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    p.terminate()
            except:
                pass
        print("👋 Güle güle!")

if __name__ == "__main__":
    start_app()
