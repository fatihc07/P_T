import os
import json
import threading
import time
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ÖNEMLİ: Kendi servisimizden import ediyoruz
try:
    from financial_service import (
        get_all_bist_stocks, 
        get_stock_data, 
        get_stock_details, 
        get_stock_financials
    )
except ImportError:
    # Railway'de bazen path karışabiliyor, fallback yapalım
    from backend.financial_service import (
        get_all_bist_stocks, 
        get_stock_data, 
        get_stock_details, 
        get_stock_financials
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
    all_stocks = get_all_bist_stocks()
    start = (page - 1) * limit
    end = start + limit
    
    current_page_stocks = all_stocks[start:end]
    
    # Her bir hisse için fiyat verilerini çek ve listeye ekle
    enriched_stocks = []
    for s in current_page_stocks:
        symbol = s["symbol"]
        data = get_stock_data(symbol)
        if data:
            # Mevcut bilgilerin üzerine fiyat, değişim vb. verileri birleştir
            enriched_item = {
                "symbol": symbol,
                "name": s.get("name", symbol),
                "price": data.get("price"),
                "change": data.get("change"),
                "changePercent": data.get("changePercent"),
                "open": data.get("open"),
                "volume": data.get("volume"),
                "sector_group": s.get("sector_group", "Diğer")
            }
            enriched_stocks.append(enriched_item)
        else:
            # Veri çekilemezse orijinal halini bırak
            enriched_stocks.append(s)

    return {
        "items": enriched_stocks,
        "has_more": end < len(all_stocks)
    }

@app.get("/stocks/{symbol}")
async def get_details(symbol: str):
    return {
        "symbol": symbol,
        "price_data": get_stock_data(symbol),
        "details": get_stock_details(symbol),
        "financials": get_stock_financials(symbol)
    }

@app.get("/search/suggestions")
async def suggestions(q: str):
    all_stocks = get_all_bist_stocks()
    q = q.upper()
    return [s for s in all_stocks if q in s["symbol"] or q in s["name"].upper()][:10]

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
