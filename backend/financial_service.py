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

# --- BIST Sektör Eşleşmeleri ---
SECTOR_MAPPING = {
    # Bankacılık & Finans
    "AKBNK": "Bankacılık", "GARAN": "Bankacılık", "ISCTR": "Bankacılık", "YKBNK": "Bankacılık", 
    "VAKBN": "Bankacılık", "HALKB": "Bankacılık", "TSKB": "Bankacılık", "SKBNK": "Bankacılık",
    "ALARK": "Holding", "KCHOL": "Holding", "SAHOL": "Holding", "SISE": "Sanayi",
    
    # Teknoloji & Savunma
    "ASELS": "Savunma & Teknoloji", "SDTTR": "Savunma & Teknoloji", "MIATK": "Teknoloji", 
    "SMRTG": "Enerji", "YEOTK": "Enerji", "KONTROL": "Teknoloji", "REEDR": "Teknoloji",
    
    # Ulaşım & Gıda
    "THYAO": "Ulaşım", "PGSUS": "Ulaşım", "TAVHL": "Ulaşım",
    "BIMAS": "Gıda Perakende", "SOKM": "Gıda Perakende", "MGROS": "Gıda Perakende",
    "ULKER": "Gıda & İçecek", "CCOLA": "Gıda & İçecek", "AEFES": "Gıda & İçecek",
    
    # Demir Çelik & Enerji
    "EREGL": "Demir Çelik", "KRDMD": "Demir Çelik", "TUPRS": "Rafineri & Enerji",
    "PETKM": "Petrokimya", "SASA": "Tekstil & Kimya", "HEKTS": "Tarım & Kimya",
    "ENJSA": "Enerji", "AKSEN": "Enerji", "ZOREN": "Enerji", "ODAS": "Enerji"
}

def get_sector_group(symbol):
    clean_symbol = symbol.replace(".IS", "").upper()
    
    # 1. Hardcoded mapping önceliği
    if clean_symbol in SECTOR_MAPPING:
        return SECTOR_MAPPING[clean_symbol]
    
    # 2. sectors.json'dan bak
    if clean_symbol + ".IS" in SECTORS_DATA:
        sec = SECTORS_DATA[clean_symbol + ".IS"].get("sector", "Diğer")
        # İngilizce gelirse çevir
        mapping = {
            "Financial Services": "Finansal Hizmetler",
            "Energy": "Enerji", "Technology": "Teknoloji", 
            "Industrials": "Sanayi", "Consumer Defensive": "Tüketim", 
            "Basic Materials": "Temel Maddeler", "Communication Services": "İletişim"
        }
        return mapping.get(sec, sec)
        
    return "Diğer"

FINANCIAL_CACHE = load_json(FINANCIAL_CACHE_FILE)
SECTORS_DATA = load_json(SECTORS_FILE)

# Hisse detay ve geçmiş veriler için cache
STOCK_CACHE_FILE = os.path.join(DATA_DIR, "stock_cache.json")
STOCK_CACHE = load_json(STOCK_CACHE_FILE)

def save_stock_cache(cache):
    try:
        with open(STOCK_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except: pass

# --- Varsayılan Hisse Listesi ---
# sectors.json'dan çekelim veya yedek listeyi kullanalım
if SECTORS_DATA:
    ALL_BIST_STOCKS = [
        {"symbol": s.replace(".IS", ""), "name": SECTORS_DATA[s].get("name", s.replace(".IS", ""))} 
        for s in SECTORS_DATA.keys() if s.endswith(".IS")
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
    Cache kontrolü yapar, 24 saat içindeki verileri döndürür.
    """
    clean_symbol = symbol.replace(".IS", "").upper()
    
    # Varsayılan sonuç şablonu
    default_result = {
        "symbol": clean_symbol,
        "name": clean_symbol,
        "price": 0,
        "change": 0,
        "changePercent": 0,
        "sector": SECTORS_DATA.get(symbol, "Bilinmiyor"),
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
        "tv_symbol": f"BIST:{clean_symbol}",
        "last_updated": datetime.now().isoformat(),
        "calculation_source": "Yahoo Finance üzerinden hesaplanmıştır.",
        "fiftyTwoWeekHigh": "-",
        "fiftyTwoWeekLow": "-",
        "enterpriseValue": None,
        "bookValue": "-",
        "ebitda": None,
        "open": 0,
        "high": 0,
        "low": 0,
        "volume": 0,
        "avgVolume": None,
        "dividendYield": "-",
        "beta": "-",
        "profitMargins": "-",
        "grossMargins": "-",
        "operatingMargins": "-",
        "returnOnEquity": "-",
        "returnOnAssets": "-",
        "revenueGrowth": "-",
        "earningsGrowth": "-",
        "currentRatio": "-",
        "debtToEquity": "-",
        "quickRatio": "-",
        "index_code": "-"
    }
    
    # Cache kontrolü - 24 saat geçerli
    cache_key = f"{clean_symbol}_details"
    if cache_key in STOCK_CACHE:
        cached = STOCK_CACHE[cache_key]
        try:
            last_updated = datetime.fromisoformat(cached.get("last_updated", "2000-01-01"))
            time_diff = datetime.now() - last_updated
            # Saat cinsinden farkı kontrol et
            if time_diff.total_seconds() / 3600 < 24:
                print(f"✅ {clean_symbol} detayları cache'den döndürüldü")
                # Eksik alanları varsayılan değerlerle doldur
                for key in default_result:
                    if key not in cached:
                        cached[key] = default_result[key]
                return cached
        except Exception as e:
            print(f"⚠️ Cache okuma hatası: {e}")
    
    try:
        yf_symbol = symbol if symbol.endswith(".IS") else f"{symbol}.IS"
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info
        
        # Fiyat ve değişim verilerini de ekleyelim (tek seferde çekilmesi için)
        hist = ticker.history(period="2d")
        price = 0
        change = 0
        change_percent = 0
        open_price = 0
        high_price = 0
        low_price = 0
        volume = 0
        
        if not hist.empty:
            latest = hist.iloc[-1]
            price = round(latest['Close'], 2)
            open_price = round(latest['Open'], 2) if not pd.isna(latest['Open']) else 0
            high_price = round(latest['High'], 2) if not pd.isna(latest['High']) else 0
            low_price = round(latest['Low'], 2) if not pd.isna(latest['Low']) else 0
            volume = int(latest['Volume']) if not pd.isna(latest['Volume']) else 0
            
            if len(hist) > 1:
                prev = hist.iloc[-2]['Close']
                change = price - prev
                change_percent = (change / prev) * 100

        # Yahoo Finance'den tüm mevcut veriler - alternatif alan adlarını dene
        pe = info.get("trailingPE") or info.get("forwardPE") or info.get("priceEpsCurrentYear")
        pb = info.get("priceToBook") or info.get("pbRatio")
        ev_ebitda = info.get("enterpriseToEbitda") or info.get("evEbitda")
        
        # Piyasa verileri - alternatif alan adlarını dene
        fifty_two_week_high = info.get("fiftyTwoWeekHigh") or info.get("52WeekHigh") or info.get("fiftyDayAverage")
        fifty_two_week_low = info.get("fiftyTwoWeekLow") or info.get("52WeekLow")
        enterprise_value = info.get("enterpriseValue") or info.get("enterpriseValue")
        book_value = info.get("bookValue") or info.get("bookValuePerShare")
        total_debt = info.get("totalDebt") or info.get("longTermDebt") or 0
        total_cash = info.get("totalCash") or info.get("freeCashflow") or 0
        ebitda_value = info.get("ebitda") or info.get("ebitdaMargins")
        
        # Eğer değerler None ise 0 yap
        if total_debt is None:
            total_debt = 0
        if total_cash is None:
            total_cash = 0
        
        # Ek finansal oranlar
        dividend_yield = info.get("dividendYield")
        beta = info.get("beta")
        profit_margins = info.get("profitMargins")
        gross_margins = info.get("grossMargins")
        operating_margins = info.get("operatingMargins")
        return_on_equity = info.get("returnOnEquity")
        return_on_assets = info.get("returnOnAssets")
        revenue_growth = info.get("revenueGrowth")
        earnings_growth = info.get("earningsGrowth")
        current_ratio = info.get("currentRatio")
        debt_to_equity = info.get("debtToEquity")
        quick_ratio = info.get("quickRatio")
        avg_volume = info.get("averageVolume")
        
        # Endeks kodu
        index_code = info.get("index") or "-"
        
        def safe_round(value, decimals=2):
            if value is None or pd.isna(value):
                return "-"
            try:
                return round(float(value), decimals)
            except:
                return "-"
        
        def safe_percent(value):
            if value is None or pd.isna(value):
                return "-"
            try:
                return round(float(value) * 100, 2)
            except:
                return "-"
        
        result = {
            "symbol": symbol.replace(".IS", ""),
            "name": info.get("longName") or info.get("shortName") or clean_symbol,
            "price": price,
            "change": round(change, 2),
            "changePercent": round(change_percent, 2),
            "sector": info.get("sector") or SECTORS_DATA.get(symbol, {}).get("sector", "Bilinmiyor"),
            "industry": info.get("industry", ""),
            "description": info.get("longBusinessSummary", ""),
            "website": info.get("website", ""),
            "marketCap": info.get("marketCap"),
            "peRatio": safe_round(pe),
            "pd_dd": safe_round(pb),
            "fd_favok": safe_round(ev_ebitda),
            "netDebt": total_debt - total_cash,
            "floatShares": info.get("floatShares"),
            "sharesOutstanding": info.get("sharesOutstanding"),
            "tv_symbol": f"BIST:{symbol.replace('.IS', '')}",
            "last_updated": datetime.now().isoformat(),
            "calculation_source": "Yahoo Finance üzerinden hesaplanmıştır.",
            # Piyasa verileri
            "fiftyTwoWeekHigh": safe_round(fifty_two_week_high),
            "fiftyTwoWeekLow": safe_round(fifty_two_week_low),
            "enterpriseValue": enterprise_value,
            "bookValue": safe_round(book_value),
            "ebitda": ebitda_value,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "volume": volume,
            "avgVolume": avg_volume,
            # Ek finansal oranlar
            "dividendYield": safe_percent(dividend_yield),
            "beta": safe_round(beta),
            "profitMargins": safe_percent(profit_margins),
            "grossMargins": safe_percent(gross_margins),
            "operatingMargins": safe_percent(operating_margins),
            "returnOnEquity": safe_percent(return_on_equity),
            "returnOnAssets": safe_percent(return_on_assets),
            "revenueGrowth": safe_percent(revenue_growth),
            "earningsGrowth": safe_percent(earnings_growth),
            "currentRatio": safe_round(current_ratio),
            "debtToEquity": safe_round(debt_to_equity),
            "quickRatio": safe_round(quick_ratio),
            "index_code": index_code
        }
        
        # Cache'e kaydet
        STOCK_CACHE[cache_key] = result
        save_stock_cache(STOCK_CACHE)
        print(f"✅ {clean_symbol} detayları çekildi ve cache'e kaydedildi")
        
        return result
    except Exception as e:
        print(f"Details error ({symbol}): {e}")
        import traceback
        traceback.print_exc()
        # Hata durumunda varsayılan sonuç döndür
        default_result["last_updated"] = datetime.now().isoformat()
        return default_result

def fetch_financials(symbol):
    if not isy_fetch:
        return None
    symbol = symbol.upper().replace(".IS", "")
    try:
        # 2026 henüz gelmemiş olabilir, en son 2025 verisi vardır.
        # Bu yüzden end_year'ı sabitleyelim veya kontrol edelim.
        target_end = min(2025, datetime.now().year)
        target_start = target_end - 4
        
        print(f"📥 {symbol} mali tabloları İş Yatırım'dan çekiliyor ({target_start}-{target_end})...")
        df = isy_fetch(symbols=symbol, start_year=str(target_start), end_year=str(target_end), exchange='TRY')
        
        if df is None or df.empty:
            print(f"⚠️ {symbol} için veri dönmedi (Boş DataFrame).")
            return None
        
        period_cols = [c for c in df.columns if '/' in c]
        period_cols.reverse() # En yeni dönemleri en başa al
        
        all_data = []
        for _, row in df.iterrows():
            code = row.get("FINANCIAL_ITEM_CODE")
            label = row.get("FINANCIAL_ITEM_NAME_TR")
            
            # Code ve label NaN gelirse temizleyelim
            item = {
                "code": code if not pd.isna(code) else "-",
                "label": label if not pd.isna(label) else "-",
                "values": {}
            }
            
            for p in period_cols: 
                val = row.get(p)
                # JSON serializasyonu için NaN değerlerini None (null) yapalım
                if pd.isna(val):
                    item["values"][p] = None
                else:
                    # Bazen sayılar string gelebiliyor, sayıya çevirmeyi deneyelim
                    # ama nan kontrolünden geçmiş olmalı
                    item["values"][p] = val
            all_data.append(item)
            
        print(f"✅ {symbol} için mali tablolar başarıyla çekildi. Dönemler: {period_cols[:4]}")
        res = {"last_updated": datetime.now().isoformat(), "data": all_data, "periods": period_cols}
        FINANCIAL_CACHE[symbol] = res
        save_financial_cache(FINANCIAL_CACHE)
        return res
    except:
        return None

def get_stock_history(symbol, period="1y"):
    """
    yfinance kullanarak geçmiş fiyat verilerini çeker.
    Cache kontrolü yapar, 6 saat içindeki verileri döndürür.
    """
    clean_symbol = symbol.replace(".IS", "").upper()
    
    # Cache kontrolü - 6 saat geçerli
    cache_key = f"{clean_symbol}_history_{period}"
    if cache_key in STOCK_CACHE:
        cached = STOCK_CACHE[cache_key]
        last_updated = datetime.fromisoformat(cached.get("last_updated", "2000-01-01"))
        if (datetime.now() - last_updated).hours < 6:
            print(f"✅ {clean_symbol} geçmişi cache'den döndürüldü")
            return cached.get("data", [])
    
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
            # Eksik verisi olan satırları atlayalım, grafiği bozmasın
            if pd.isna(row['Open']) or pd.isna(row['High']) or pd.isna(row['Low']) or pd.isna(row['Close']):
                continue
                
            data.append({
                "Date": date.strftime("%Y-%m-%d"),
                "Open": round(row['Open'], 2),
                "High": round(row['High'], 2),
                "Low": round(row['Low'], 2),
                "Close": round(row['Close'], 2),
                "Volume": int(row['Volume']) if not pd.isna(row['Volume']) else 0,
                "MA20": round(row['MA20'], 2) if not pd.isna(row['MA20']) else None,
                "MA50": round(row['MA50'], 2) if not pd.isna(row['MA50']) else None,
                "MA200": round(row['MA200'], 2) if not pd.isna(row['MA200']) else None,
                "RSI": round(row['RSI'], 2) if not pd.isna(row['RSI']) else None
            })
        
        # Cache'e kaydet
        STOCK_CACHE[cache_key] = {
            "data": data,
            "last_updated": datetime.now().isoformat()
        }
        save_stock_cache(STOCK_CACHE)
        print(f"✅ {clean_symbol} geçmişi çekildi ve cache'e kaydedildi")
        
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
