from datetime import datetime
import json
import os
import urllib3
import pandas as pd
import ssl
import requests
import yfinance as yf

# SSL sertifika hatasını atlamak için
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# requests kütüphanesini verify=False yapacak şekilde yamalayalım
old_request = requests.Session.request
def new_request(self, method, url, **kwargs):
    kwargs['verify'] = False
    return old_request(self, method, url, **kwargs)
requests.Session.request = new_request

try:
    from isyatirimhisse import fetch_financials as isy_fetch
except ImportError:
    isy_fetch = None

DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

FINANCIAL_CACHE_FILE = os.path.join(DATA_DIR, "financial_cache.json")
SECTORS_FILE = os.path.join(os.path.dirname(__file__), "sectors.json")

def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

FINANCIAL_CACHE = load_json(FINANCIAL_CACHE_FILE)
SECTORS_DATA = load_json(SECTORS_FILE)

# --- Varsayılan Hisse Listesi ---
# sectors.json'dan çekelim veya yedek listeyi kullanalım
if SECTORS_DATA:
    ALL_BIST_STOCKS = [
        {"symbol": s.replace(".IS", ""), "name": s.replace(".IS", "")} 
        for s in SECTORS_DATA.keys() if not s.endswith(".IS")
    ]
else:
    ALL_BIST_STOCKS = [
        {"symbol": "THYAO", "name": "Türk Hava Yolları"},
        {"symbol": "KCHOL", "name": "Koç Holding"},
        {"symbol": "GARAN", "name": "Garanti Bankası"},
        {"symbol": "EREGL", "name": "Erdemir"},
        {"symbol": "SISE", "name": "Şişecam"}
    ]

def get_all_bist_stocks():
    return ALL_BIST_STOCKS

def get_stock_data(symbol):
    """
    yfinance kullanarak 5 günlük fiyat verisi çeker.
    """
    try:
        yf_symbol = symbol if symbol.endswith(".IS") else f"{symbol}.IS"
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period="5d")
        
        if hist.empty:
            return None
            
        latest = hist.iloc[-1]
        prev_close = hist.iloc[-2]['Close'] if len(hist) > 1 else latest['Open']
        
        change = latest['Close'] - prev_close
        change_percent = (change / prev_close) * 100
        
        return {
            "price": round(latest['Close'], 2),
            "open": round(latest['Open'], 2),
            "high": round(latest['High'], 2),
            "low": round(latest['Low'], 2),
            "change": round(change, 2),
            "changePercent": round(change_percent, 2),
            "volume": int(latest['Volume']),
            "history": [
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "close": round(c, 2)
                } for d, c in hist['Close'].items()
            ]
        }
    except Exception as e:
        print(f"yfinance hatası ({symbol}): {e}")
        return None

def get_stock_details(symbol):
    """
    Hisse rasyolarını (F/K, PD/DD vb.) ve temel bilgilerini döner.
    """
    try:
        yf_symbol = symbol if symbol.endswith(".IS") else f"{symbol}.IS"
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info
        
        return {
            "name": info.get("longName", symbol),
            "sector": info.get("sector", SECTORS_DATA.get(symbol, "Bilinmiyor")),
            "description": info.get("longBusinessSummary", ""),
            "ratios": {
                "pe": info.get("trailingPE"),
                "pb": info.get("priceToBook"),
                "ebitda": info.get("enterpriseToEbitda"),
                "marketCap": info.get("marketCap"),
                "dividendYield": info.get("dividendYield", 0) * 100 if info.get("dividendYield") else None
            }
        }
    except:
        return {"sector": SECTORS_DATA.get(symbol, "Bilinmiyor")}

def fetch_financials(symbol):
    if not isy_fetch:
        return None
    symbol = symbol.upper().replace(".IS", "")
    try:
        curr_year = datetime.now().year
        df = isy_fetch(symbols=symbol, start_year=str(curr_year-3), end_year=str(curr_year), exchange='TRY')
        if df is None or df.empty: return None
        
        period_cols = [c for c in df.columns if '/' in c]
        all_data = []
        for _, row in df.iterrows():
            item = {"code": row.get("FINANCIAL_ITEM_CODE"), "label": row.get("FINANCIAL_ITEM_NAME_TR"), "values": {}}
            for p in period_cols: item["values"][p] = row.get(p)
            all_data.append(item)
            
        res = {"last_updated": datetime.now().isoformat(), "data": all_data, "periods": period_cols}
        FINANCIAL_CACHE[symbol] = res
        save_financial_cache(FINANCIAL_CACHE)
        return res
    except:
        return None

def save_financial_cache(cache):
    try:
        with open(FINANCIAL_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except: pass

def get_stock_financials(symbol):
    symbol = symbol.upper().replace(".IS", "")
    cached = FINANCIAL_CACHE.get(symbol)
    if cached:
        last_updated = datetime.fromisoformat(cached["last_updated"])
        if (datetime.now() - last_updated).days < 7:
            return cached
    return fetch_financials(symbol)
