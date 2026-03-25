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
        
        # Fiyat ve değişim verilerini de ekleyelim (tek seferde çekilmesi için)
        hist = ticker.history(period="2d")
        price = 0
        change = 0
        change_percent = 0
        if not hist.empty:
            latest = hist.iloc[-1]
            price = round(latest['Close'], 2)
            if len(hist) > 1:
                prev = hist.iloc[-2]['Close']
                change = price - prev
                change_percent = (change / prev) * 100

        return {
            "symbol": symbol.replace(".IS", ""),
            "name": info.get("longName", symbol),
            "price": price,
            "change": round(change, 2),
            "changePercent": round(change_percent, 2),
            "sector": info.get("sector", SECTORS_DATA.get(symbol, "Bilinmiyor")),
            "industry": info.get("industry", ""),
            "description": info.get("longBusinessSummary", ""),
            "website": info.get("website", ""),
            "marketCap": info.get("marketCap"),
            "peRatio": info.get("trailingPE") or "-",
            "pd_dd": info.get("priceToBook") or "-",
            "fd_favok": info.get("enterpriseToEbitda") or "-",
            "netDebt": info.get("totalDebt", 0) - info.get("totalCash", 0),
            "floatShares": info.get("floatShares"),
            "sharesOutstanding": info.get("sharesOutstanding"),
            "tv_symbol": f"BIST:{symbol.replace('.IS', '')}",
            "last_updated": datetime.now().isoformat(),
            "calculation_source": "Yahoo Finance üzerinden hesaplanmıştır."
        }
    except Exception as e:
        print(f"Details error ({symbol}): {e}")
        return {
            "symbol": symbol,
            "sector": SECTORS_DATA.get(symbol, "Bilinmiyor"),
            "peRatio": "-",
            "pd_dd": "-"
        }

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

def get_stock_history(symbol, period="1y"):
    """
    yfinance kullanarak geçmiş fiyat verilerini çeker.
    """
    try:
        yf_symbol = symbol if symbol.endswith(".IS") else f"{symbol}.IS"
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period=period)
        
        if hist.empty:
            return []
            
        data = []
        # MA'ları hesapla
        hist['MA20'] = hist['Close'].rolling(window=20).mean()
        hist['MA50'] = hist['Close'].rolling(window=50).mean()
        hist['MA200'] = hist['Close'].rolling(window=200).mean()
        
        # RSI hesapla (Basit)
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        hist['RSI'] = 100 - (100 / (1 + rs))

        for date, row in hist.iterrows():
            data.append({
                "Date": date.strftime("%Y-%m-%d"),
                "Open": round(row['Open'], 2) if not pd.isna(row['Open']) else None,
                "High": round(row['High'], 2) if not pd.isna(row['High']) else None,
                "Low": round(row['Low'], 2) if not pd.isna(row['Low']) else None,
                "Close": round(row['Close'], 2) if not pd.isna(row['Close']) else None,
                "Volume": int(row['Volume']) if not pd.isna(row['Volume']) else 0,
                "MA20": round(row['MA20'], 2) if not pd.isna(row['MA20']) else None,
                "MA50": round(row['MA50'], 2) if not pd.isna(row['MA50']) else None,
                "MA200": round(row['MA200'], 2) if not pd.isna(row['MA200']) else None,
                "RSI": round(row['RSI'], 2) if not pd.isna(row['RSI']) else None
            })
        return data
    except Exception as e:
        print(f"History error ({symbol}): {e}")
        return []

def get_brokerage_data(symbol):
    """
    Simüle edilmiş takas verisi döner (BIST gerçek takas verisi ücretlidir).
    """
    symbol = symbol.upper().replace(".IS", "")
    return {
        "top_buyers": [
            {"broker": "Ziraat Yatırım", "quantity": 1250430, "percentage": 25.4},
            {"broker": "İş Yatırım", "quantity": 980200, "percentage": 19.8},
            {"broker": "Garanti BBVA", "quantity": 750000, "percentage": 15.2},
            {"broker": "QNB Finans", "quantity": 420000, "percentage": 8.5},
            {"broker": "Yatırım Finansman", "quantity": 310000, "percentage": 6.3}
        ],
        "top_sellers": [
            {"broker": "Ak Yatırım", "quantity": -1150000, "percentage": 23.3},
            {"broker": "Vakıf Yatırım", "quantity": -890000, "percentage": 18.0},
            {"broker": "Yapı Kredi", "quantity": -650000, "percentage": 13.2},
            {"broker": "Deniz Yatırım", "quantity": -520000, "percentage": 10.5},
            {"broker": "Diğer", "quantity": -1720630, "percentage": 35.0}
        ],
        "note": "Takas verileri 2 gün gecikmelidir. Veriler simüle edilmiştir."
    }

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
