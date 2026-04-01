
import json
import os
import threading
import time
from datetime import datetime
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor
import yfinance as yf

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Supabase client
try:
    from supabase import create_client, Client
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")  # Service key for admin operations
    supabase: Client = None
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase client initialized")
    else:
        print("⚠️ Supabase credentials not found, using local JSON")
except ImportError:
    supabase = None
    print("⚠️ Supabase library not installed, using local JSON")

# --- Loglama Sistemi ---
def log_to_file(message):
    try:
        with open("backend_logs.txt", "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
    except: pass

log_to_file("🚀 Backend baslatildi.")

# ÖNEMLİ: Kendi servisimizden import ediyoruz
try:
    from financial_service import (
        get_all_bist_stocks, 
        get_stock_data, 
        get_stock_details, 
        get_stock_financials,
        get_stock_history,
        get_brokerage_data,
        get_sector_group
    )
except ImportError:
    from backend.financial_service import (
        get_all_bist_stocks, 
        get_stock_data, 
        get_stock_details, 
        get_stock_financials,
        get_stock_history,
        get_brokerage_data,
        get_sector_group
    )

app = FastAPI(title="Hisse PhD API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "https://meek-madeleine-0b2e8d.netlify.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Veri Yolu (Railway Volume için) ---
DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

USER_DB = os.path.join(DATA_DIR, "users.json")

def load_users():
    if os.path.exists(USER_DB):
        try:
            with open(USER_DB, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {"admin": {"password": "admin", "role": "admin"}}

users_db = load_users()

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/login")
async def login(req: LoginRequest):
    if req.username in users_db and users_db[req.username]["password"] == req.password:
        return {
            "status": "success",
            "token": f"token-{req.username}",
            "user": req.username
        }
    raise HTTPException(status_code=401, detail="Hatalı giriş")

@app.get("/stocks")
async def get_stocks(page: int = 1, limit: int = 20):
    log_to_file(f"📋 Hisse listesi istendi (Sayfa: {page}, Limit: {limit})")
    all_stocks = get_all_bist_stocks()
    start = (page - 1) * limit
    end = start + limit
    current_page_stocks = all_stocks[start:end]
    
    log_to_file(f"🔄 {len(current_page_stocks)} hisse zenginleştiriliyor...")
    
    # Hisse verilerini paralel olarak çekelim ki sayfa hızlı yüklensin
    def enrich(s):
        try:
            symbol = s["symbol"]
            data = get_stock_data(symbol)
            if data:
                return {
                    "symbol": symbol,
                    "name": s.get("name", symbol),
                    "price": data.get("price"),
                    "change": data.get("change"),
                    "changePercent": data.get("changePercent"),
                    "open": data.get("open"),
                    "volume": data.get("volume"),
                    "sector_group": get_sector_group(symbol)
                }
        except Exception as e:
            log_to_file(f"⚠️ {s['symbol']} zenginleştirme hatası: {e}")
        return s

    num_workers = max(1, min(len(current_page_stocks), 15))
    try:
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            enriched_stocks = list(executor.map(enrich, current_page_stocks))
    except Exception as e:
        log_to_file(f"🔥 ThreadPool hatası: {e}")
        enriched_stocks = current_page_stocks

    log_to_file(f"✅ {len(enriched_stocks)} hisse hazırlandı.")
    return {
        "items": enriched_stocks,
        "has_more": end < len(all_stocks)
    }

@app.get("/stocks/{symbol}/detail")
def get_details_only(symbol: str):
    log_to_file(f"🔍 {symbol} için detaylar istendi.")
    try:
        data = get_stock_details(symbol)
        if not data:
            log_to_file(f"❌ {symbol} detayları bulunamadı.")
            # Boş veri yerine varsayılan veri döndür
            data = {
                "symbol": symbol.replace(".IS", ""),
                "name": symbol.replace(".IS", ""),
                "price": 0,
                "change": 0,
                "changePercent": 0,
                "sector": "Bilinmiyor",
                "industry": "",
                "description": "",
                "website": "",
                "marketCap": None,
                "peRatio": "-",
                "pd_dd": "-",
                "fd_favok": "-",
                "netDebt": 0,
                "floatShares": None,
                "sharesOutstanding": None,
                "tv_symbol": f"BIST:{symbol.replace('.IS', '')}",
                "last_updated": datetime.now().isoformat(),
                "calculation_source": "Veri bulunamadı",
                "fiftyTwoWeekHigh": "-",
                "fiftyTwoWeekLow": "-",
                "enterpriseValue": None,
                "bookValue": "-",
                "ebitda": None
            }
        log_to_file(f"✅ {symbol} detayları gönderildi.")
        return data
    except Exception as e:
        log_to_file(f"🔥 {symbol} detay hatası: {str(e)}")
        # Hata durumunda da varsayılan veri döndür
        return {
            "symbol": symbol.replace(".IS", ""),
            "name": symbol.replace(".IS", ""),
            "price": 0,
            "change": 0,
            "changePercent": 0,
            "sector": "Bilinmiyor",
            "industry": "",
            "description": f"Veri çekilemedi: {str(e)}",
            "website": "",
            "marketCap": None,
            "peRatio": "-",
            "pd_dd": "-",
            "fd_favok": "-",
            "netDebt": 0,
            "floatShares": None,
            "sharesOutstanding": None,
            "tv_symbol": f"BIST:{symbol.replace('.IS', '')}",
            "last_updated": datetime.now().isoformat(),
            "calculation_source": "Hata oluştu",
            "fiftyTwoWeekHigh": "-",
            "fiftyTwoWeekLow": "-",
            "enterpriseValue": None,
            "bookValue": "-",
            "ebitda": None
        }

@app.get("/stocks/{symbol}/financials")
def get_financials_only(symbol: str):
    log_to_file(f"📊 {symbol} için mali tablolar istendi.")
    data = get_stock_financials(symbol)
    if not data:
        log_to_file(f"⚠️ {symbol} mali tabloları ÇEKİLEMEDİ.")
        # Frontend'in financials ? checkini geçmesi için null yerine boş ama geçerli yapı dönelim
        return {"data": [], "periods": [], "last_updated": None, "status": "error"}
    log_to_file(f"✅ {symbol} mali tabloları hazır.")
    return data

@app.get("/stocks/{symbol}/history")
def get_history_only(symbol: str, period: str = "1y"):
    print(f"📈 {symbol} için {period} sürelik geçmiş veri isteniyor...")
    hist = get_stock_history(symbol, period)
    print(f"✅ {symbol} geçmiş verisi ({len(hist)} kayıt) alındı.")
    return hist

@app.get("/stocks/{symbol}/brokerage")
def get_brokerage_only(symbol: str):
    print(f"🔄 {symbol} için takas verisi isteniyor...")
    return get_brokerage_data(symbol)

@app.get("/stocks/{symbol}")
def get_details(symbol: str):
    # Geriye uyumluluk için hepsini birden dönen endpoint
    print(f"📡 {symbol} için tüm veriler (paket) isteniyor...")
    return {
        "symbol": symbol,
        "price_data": get_stock_data(symbol),
        "details": get_stock_details(symbol),
        "financials": get_stock_financials(symbol)
    }

@app.get("/search/suggestions")
def suggestions(q: str):
    all_stocks = get_all_bist_stocks()
    q = q.upper()
    
    # Kendi listemizden ara
    local_results = [s for s in all_stocks if q in s["symbol"] or q in s["name"].upper()]
    
    # Eğer sonuç azsa veya yoksa Yahoo'dan ara
    if len(local_results) < 5:
        try:
            # Arama sonucunu daraltmak için '.IS' ekleyebiliriz veya genel arama yapıp temizleyebiliriz
            search_res = yf.Search(q, max_results=8).quotes
            for quote in search_res:
                symbol = quote.get('symbol', '').replace('.IS', '')
                # Mükerrer olmasın
                if not any(r['symbol'] == symbol for r in local_results):
                    local_results.append({
                        "symbol": symbol,
                        "name": quote.get('shortname', quote.get('longname', symbol))
                    })
        except: pass
        
    return local_results[:12]

@app.get("/heartbeat")
async def heartbeat():
    return {"status": "ok", "time": datetime.now().isoformat()}

# --- Admin Rotaları ---

@app.get("/admin/users")
async def get_admin_users():
    # Supabase varsa oradan çek
    if supabase:
        try:
            response = supabase.auth.admin.list_users()
            users = [user.email for user in response if user.email]
            print(f"✅ Supabase'den {len(users)} kullanıcı çekildi")
            return users
        except Exception as e:
            print(f"⚠️ Supabase'den kullanıcı çekilemedi: {e}")
    
    # Fallback: local JSON
    return list(users_db.keys())

@app.get("/admin/stats")
async def get_admin_stats():
    # financial_cache.json dosyasını sayalım
    cache_path = os.path.join(DATA_DIR, "financial_cache.json")
    cached_count = 0
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
                cached_count = len(cache_data)
        except: pass
    
    # Kullanıcı sayısını Supabase'den al
    user_count = len(users_db)
    if supabase:
        try:
            response = supabase.auth.admin.list_users()
            user_count = len([u for u in response if u.email])
        except: pass
    
    return {
        "cached_financials": cached_count,
        "total_users": user_count,
        "online_users": 1 # Şimdilik basitçe 1 dönelim
    }

@app.get("/admin/online-users")
async def get_online_users():
    # Basitlik için sadece admin'i dönelim şimdilik
    return ["admin"]

@app.get("/admin/cached-stocks")
async def get_cached_stocks():
    cache_path = os.path.join(DATA_DIR, "financial_cache.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
                return list(cache_data.keys())
        except: return []
    return []

# IPO Cache
IPO_CACHE_FILE = os.path.join(DATA_DIR, "ipo_cache.json")

def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

IPO_CACHE = load_json(IPO_CACHE_FILE)

def save_ipo_cache(cache):
    try:
        with open(IPO_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except: pass

@app.get("/ipo/list")
async def get_ipo_list(page: int = 1, limit: int = 10, search: str = ""):
    """Halka arz listesini döndürür - Yahoo Finance'den gerçek veri çeker"""
    try:
        # Cache kontrolü - 12 saat geçerli
        cache_key = "ipo_list"
        if cache_key in IPO_CACHE:
            cached = IPO_CACHE[cache_key]
            last_updated = datetime.fromisoformat(cached.get("last_updated", "2000-01-01"))
            if (datetime.now() - last_updated).total_seconds() / 3600 < 12:
                ipo_list = cached.get("items", [])
                # Arama filtresi
                if search:
                    ipo_list = [ipo for ipo in ipo_list if search.lower() in ipo["company"].lower() or search.lower() in ipo["symbol"].lower()]
                # Sayfalama
                start = (page - 1) * limit
                end = start + limit
                paginated_list = ipo_list[start:end]
                return {
                    "items": paginated_list,
                    "total": len(ipo_list),
                    "page": page,
                    "has_more": end < len(ipo_list)
                }
        
        # BIST hisselerini Yahoo Finance'den çek
        all_stocks = get_all_bist_stocks()
        
        # Halka arz olan şirketleri filtrele (son 3 yılda halka arz olanlar)
        ipo_list = []
        current_year = datetime.now().year
        
        # Daha fazla hisse kontrol et ve paralel işlem kullan
        def check_ipo(stock):
            try:
                symbol = stock["symbol"]
                yf_symbol = f"{symbol}.IS"
                ticker = yf.Ticker(yf_symbol)
                info = ticker.info
                
                # Halka arz tarihini kontrol et
                ipo_date = info.get("firstTradeDateMilliseconds")
                if ipo_date:
                    ipo_year = datetime.fromtimestamp(ipo_date / 1000).year
                    if ipo_year >= current_year - 3:  # Son 3 yıl
                        # Fiyat bilgisini al
                        hist = ticker.history(period="5d")
                        current_price = 0
                        if not hist.empty:
                            current_price = round(hist.iloc[-1]['Close'], 2)
                        
                        return {
                            "id": 0,  # Geçici, sonra güncellenecek
                            "company": info.get("longName", symbol),
                            "symbol": symbol,
                            "sector": info.get("sector", "Bilinmiyor"),
                            "date": datetime.fromtimestamp(ipo_date / 1000).strftime("%Y-%m-%d"),
                            "priceRange": f"{info.get('previousClose', current_price):.2f} ₺",
                            "currentPrice": current_price,
                            "volume": f"{info.get('volume', 0):,}",
                            "marketCap": info.get("marketCap"),
                            "status": "Tamamlandı",
                            "description": info.get("longBusinessSummary", "")[:150] + "..." if info.get("longBusinessSummary") else "Halka arz tamamlandı"
                        }
            except Exception as e:
                print(f"IPO check error for {stock.get('symbol', 'unknown')}: {e}")
            return None
        
        # Paralel olarak IPO kontrolü yap
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(check_ipo, stock): stock for stock in all_stocks[:200]}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    ipo_list.append(result)
        
        # Tarihe göre sırala (en yeni önce)
        ipo_list.sort(key=lambda x: x["date"], reverse=True)
        
        # ID'leri güncelle
        for i, ipo in enumerate(ipo_list):
            ipo["id"] = i + 1
        
        # Cache'e kaydet
        IPO_CACHE[cache_key] = {
            "items": ipo_list,
            "last_updated": datetime.now().isoformat()
        }
        save_ipo_cache(IPO_CACHE)
        
        # Arama filtresi
        if search:
            ipo_list = [ipo for ipo in ipo_list if search.lower() in ipo["company"].lower() or search.lower() in ipo["symbol"].lower()]
        
        # Sayfalama
        start = (page - 1) * limit
        end = start + limit
        paginated_list = ipo_list[start:end]
        
        return {
            "items": paginated_list,
            "total": len(ipo_list),
            "page": page,
            "has_more": end < len(ipo_list)
        }
    except Exception as e:
        print(f"IPO verisi çekilemedi: {e}")
        import traceback
        traceback.print_exc()
        # Fallback: boş liste döndür
        return {
            "items": [],
            "total": 0,
            "page": page,
            "has_more": False
        }

@app.post("/admin/create-user")
async def create_user(req: LoginRequest):
    # Supabase varsa orada oluştur
    if supabase:
        try:
            # Supabase'de kullanıcı oluştur
            response = supabase.auth.admin.create_user({
                "email": req.username,
                "password": req.password,
                "email_confirm": True  # Otomatik onayla
            })
            print(f"✅ Supabase'de kullanıcı oluşturuldu: {req.username}")
            return {"status": "success", "message": f"{req.username} kullanıcısı oluşturuldu"}
        except Exception as e:
            print(f"⚠️ Supabase'de kullanıcı oluşturulamadı: {e}")
            raise HTTPException(status_code=400, detail=f"Kullanıcı oluşturulamadı: {str(e)}")
    
    # Fallback: local JSON
    if req.username in users_db:
        raise HTTPException(status_code=400, detail="Kullanıcı zaten mevcut")
    
    users_db[req.username] = {"password": req.password, "role": "user"}
    
    # Veritabanına kaydet
    try:
        with open(USER_DB, "w", encoding="utf-8") as f:
            json.dump(users_db, f, ensure_ascii=False, indent=2)
    except: pass
    
    return {"status": "success"}

@app.delete("/admin/users/{username}")
async def delete_user(username: str):
    # Admin kullanıcısı silinemez
    if username == "admin":
        raise HTTPException(status_code=400, detail="Admin kullanıcısı silinemez")
    
    # Supabase varsa oradan sil
    if supabase:
        try:
            # Önce kullanıcıyı email ile bul
            users = supabase.auth.admin.list_users()
            user_to_delete = None
            for user in users:
                if user.email == username:
                    user_to_delete = user
                    break
            
            if user_to_delete:
                supabase.auth.admin.delete_user(user_to_delete.id)
                print(f"✅ Supabase'den kullanıcı silindi: {username}")
                return {"status": "success", "message": f"{username} kullanıcısı silindi"}
            else:
                raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
        except HTTPException:
            raise
        except Exception as e:
            print(f"⚠️ Supabase'den kullanıcı silinemedi: {e}")
            raise HTTPException(status_code=400, detail=f"Kullanıcı silinemedi: {str(e)}")
    
    # Fallback: local JSON
    if username not in users_db:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    
    # Kullanıcıyı sil
    del users_db[username]
    
    # Veritabanına kaydet
    try:
        with open(USER_DB, "w", encoding="utf-8") as f:
            json.dump(users_db, f, ensure_ascii=False, indent=2)
    except: pass
    
    return {"status": "success", "message": f"{username} kullanıcısı silindi"}

# --- Frontend Servis ---
# main.py ile aynı yerdeki 'dist' klasörüne bak (nixpacks oraya kopyalıyor)
current_dir = os.path.dirname(os.path.abspath(__file__))
frontend_path = os.path.join(current_dir, "dist")

if os.path.exists(frontend_path):
    # Statik assetler (js, css)
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_path, "assets")), name="assets")
    
    @app.get("/")
    async def index():
        return FileResponse(os.path.join(frontend_path, "index.html"))

    @app.get("/{full_path:path}")
    async def catch_all(full_path: str):
        # API yollarını hariç tut (Bu yollar SPA rotası değil, gerçek API endpointleridir)
        api_paths = ["stocks", "login", "search", "admin", "ipo", "heartbeat", "assets"]
        if any(full_path.startswith(p) for p in api_paths):
            raise HTTPException(status_code=404)
            
        # Dosya varsa onu ver
        local_file = os.path.join(frontend_path, full_path)
        if os.path.exists(local_file) and os.path.isfile(local_file):
            return FileResponse(local_file)
                
        # Yoksa SPA router için index.html ver
        return FileResponse(os.path.join(frontend_path, "index.html"))
else:
    print(f"⚠️ UYARI: Frontend built klasörü ({frontend_path}) bulunamadı!")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
