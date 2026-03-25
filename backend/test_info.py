import yfinance as yf
import json

symbols = ["THYAO.IS", "KCHOL.IS", "GARAN.IS"]

for s in symbols:
    print(f"\n--- {s} ---")
    t = yf.Ticker(s)
    info = t.info
    data = {
        "marketCap": info.get("marketCap"),
        "trailingPE": info.get("trailingPE"),
        "priceToBook": info.get("priceToBook"),
        "enterpriseToEbitda": info.get("enterpriseToEbitda"),
        "totalDebt": info.get("totalDebt"),
        "totalCash": info.get("totalCash"),
        "floatShares": info.get("floatShares"),
        "sharesOutstanding": info.get("sharesOutstanding"),
        "bookValue": info.get("bookValue"),
        "enterpriseValue": info.get("enterpriseValue")
    }
    print(json.dumps(data, indent=2))
