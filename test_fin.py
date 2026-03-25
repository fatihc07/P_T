import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))
from financial_service import get_stock_financials
import json

symbol = "THYAO"
res = get_stock_financials(symbol)
print(json.dumps(res, indent=2, ensure_ascii=False) if res else "None")
