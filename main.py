import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BIRDEYE_API_KEY")

WALLET = "F6Fh9BjBXb1GyacHto4cwqcKF4K4xK8SwEyDv9Ayp8j9"

url = "https://public-api.birdeye.so/wallet/v2/pnl/summary"

headers = {
    "X-API-KEY": API_KEY,
    "x-chain": "solana"
}

params = {
    "wallet": WALLET,
    "duration": "90d",
    "position_scope": "duration_only",
    "pnl_method": "net_cash"
}

print("Mengambil PnL wallet...")
print(WALLET)

response = requests.get(
    url,
    headers=headers,
    params=params,
    timeout=30
)

print("\nHTTP:", response.status_code)

print("\n========== RESPONSE ==========")

try:
    data = response.json()
    print(json.dumps(data, indent=2))
except Exception:
    print(response.text)

print("==============================")
