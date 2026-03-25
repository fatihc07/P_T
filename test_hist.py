import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))
from financial_service import get_stock_history
import json

symbol = "THYAO"
res = get_stock_history(symbol, "1y")
print(f"Count: {len(res)}")
if res:
    print(json.dumps(res[0], indent=2))
