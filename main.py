import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BIRDEYE_API_KEY")

if not API_KEY:
    raise RuntimeError("BIRDEYE_API_KEY belum diatur")

url = "https://public-api.birdeye.so/defi/price"

params = {
    "address": "So11111111111111111111111111111111111111112"
}

headers = {
    "X-API-KEY": API_KEY,
    "x-chain": "solana"
}

response = requests.get(
    url,
    params=params,
    headers=headers,
    timeout=20
)

print("HTTP:", response.status_code)
print(response.text)
