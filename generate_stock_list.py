import yfinance as yf
from yfinance import screen, EquityQuery
import json
import os

def fetch_all_bist():
    all_quotes = []
    print("Collecting BIST stocks from Yahoo Finance...")
    
    try:
        q = EquityQuery('eq', ['exchange', 'IST'])
        # Iterate in batches to get all (Yahoo usually limits size to 250 per call)
        batch_size = 250
        offset = 0
        while True:
            res = screen(q, offset=offset, size=batch_size)
            quotes = res.get('quotes', [])
            if not quotes:
                break
            all_quotes.extend(quotes)
            print(f"Collected {len(all_quotes)} stocks so far...")
            if len(quotes) < batch_size:
                break
            offset += batch_size
            
        # Transform data
        sectors_data = {}
        for quote in all_quotes:
            symbol = quote.get('symbol', '')
            # Clean symbol (THYAO.IS -> THYAO)
            clean_symbol = symbol.replace('.IS', '')
            name = quote.get('shortname', quote.get('longname', clean_symbol))
            sectors_data[symbol] = {
                "name": name,
                "sector": quote.get('sector', 'Diğer'),
                "industry": quote.get('industry', ''),
                "market_cap": quote.get('marketCap', 0)
            }
        
        # Save to file
        target_file = r"c:\Users\efcak\Desktop\Myapps\PHD_T-main\backend\sectors.json"
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(sectors_data, f, ensure_ascii=False, indent=2)
            
        print(f"Successfully saved {len(sectors_data)} stocks to sectors.json")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    fetch_all_bist()
