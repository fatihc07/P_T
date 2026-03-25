import yfinance as yf
from yfinance import screen, EquityQuery
import json

try:
    # Borsa Istanbul için EquityQuery
    q = EquityQuery('eq', ['exchange', 'IST'])
    results = screen(q, size=20)
    
    if 'quotes' in results:
        stocks = []
        for quote in results['quotes']:
            stocks.append({
                "symbol": quote.get('symbol', '').replace('.IS', ''),
                "name": quote.get('shortname', quote.get('longname', quote.get('symbol', '')))
            })
        print(json.dumps(stocks, indent=2, ensure_ascii=False))
    else:
        print("No quotes found in results.")
        print(results.keys())
except Exception as e:
    print(f"Error: {e}")
