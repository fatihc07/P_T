kartındaimport sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from financial_service import get_stock_details
import json

print("Testing ZOREN stock details...")
try:
    result = get_stock_details('ZOREN')
    print("SUCCESS!")
    print(json.dumps(result, indent=2, default=str))
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()