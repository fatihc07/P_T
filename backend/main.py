import os
import json
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

app = FastAPI(title="PhD Terminal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    data = get_stock_details(symbol)
    if not data:
        log_to_file(f"❌ {symbol} detayları bulunamadı.")
        raise HTTPException(status_code=404, detail="Hisse bulunamadı")
    log_to_file(f"✅ {symbol} detayları gönderildi.")
    return data

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
    
    return {
        "cached_financials": cached_count,
        "total_users": len(users_db),
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

@app.post("/admin/create-user")
async def create_user(req: LoginRequest):
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
        # API ise 404 dön ki FastAPI yakalasın
        if full_path.startswith("stocks") or full_path.startswith("login"):
            raise HTTPException(status_code=404)
        
        # Dosya varsa onu ver
        local_file = os.path.join(frontend_path, full_path)
        if os.path.exists(local_file) and os.path.isfile(local_file):
            return FileResponse(local_file)
            
        # Yoksa SPA router için index.html ver
        return FileResponse(os.path.join(frontend_path, "index.html"))
else:
    print(f"⚠️ UYARI: Frontend built klasörü ({frontend_path}) bulunamadı!")
