import os
import sys

# Backend klasörünü kütüphane yolu olarak ekle
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

import uvicorn
from backend.main import app

if __name__ == "__main__":
    # Railway'in atadığı dinamik portu al
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 PhD Terminal {port} portunda havalanıyor...")
    
    # 0.0.0.0 her yerden erişim sağlar (Railway için zorunlu)
    uvicorn.run(app, host="0.0.0.0", port=port)
