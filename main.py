import os
import json
import time
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BIRDEYE_API_KEY")

if not API_KEY:
    raise RuntimeError("BIRDEYE_API_KEY belum diatur")

WALLETS = [
    "F6Fh9BjBXb1GyacHto4cwqcKF4K4xK8SwEyDv9Ayp8j9",
    "9xn3JjPreFAaAEBZL3VVvcou33jrfRWhsuiNbD4sJcEe",
]

BASE_URL = "https://public-api.birdeye.so"

HEADERS = {
    "X-API-KEY": API_KEY,
    "x-chain": "solana",
}

CACHE_FILE = "wallet_cache.json"

# Minimal jeda antar request
REQUEST_DELAY = 5

# Maksimal retry ketika kena 429
MAX_RETRIES = 5


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def get_wallet_pnl(wallet):

    url = f"{BASE_URL}/wallet/v2/pnl/summary"

    params = {
        "wallet": wallet,
        "duration": "90d",
        "position_scope": "duration_only",
        "pnl_method": "net_cash",
    }

    for attempt in range(MAX_RETRIES):

        try:

            response = requests.get(
                url,
                headers=HEADERS,
                params=params,
                timeout=30,
            )

            print(
                f"[{wallet[:8]}] "
                f"HTTP {response.status_code}"
            )

            if response.status_code == 200:
                return response.json()

            if response.status_code == 429:

                wait_time = 10 * (attempt + 1)

                print(
                    f"Rate limit. "
                    f"Menunggu {wait_time} detik..."
                )

                time.sleep(wait_time)
                continue

            print(response.text)

            return None

        except requests.RequestException as e:

            print("Request error:", e)

            wait_time = 5 * (attempt + 1)

            time.sleep(wait_time)

    return None


def extract_summary(data):

    if not data:
        return {}

    result = data.get("data", {})

    counts = result.get("counts", {})
    pnl = result.get("pnl", {})
    cashflow = result.get("cashflow_usd", {})

    return {
        "total_buy": counts.get("total_buy"),
        "total_sell": counts.get("total_sell"),
        "total_trade": counts.get("total_trade"),
        "total_win": counts.get("total_win"),
        "total_loss": counts.get("total_loss"),
        "win_rate": counts.get("win_rate"),

        "total_invested": cashflow.get("total_invested"),
        "total_sold": cashflow.get("total_sold"),
        "current_value": cashflow.get("current_value"),

        "realized_profit_usd": pnl.get(
            "realized_profit_usd"
        ),

        "realized_profit_percent": pnl.get(
            "realized_profit_percent"
        ),

        "unrealized_usd": pnl.get(
            "unrealized_usd"
        ),

        "total_usd": pnl.get(
            "total_usd"
        ),

        "avg_profit_per_trade_usd": pnl.get(
            "avg_profit_per_trade_usd"
        ),
    }


def main():

    print("=" * 70)
    print("SOLANA WALLET ANALYZER V3")
    print("=" * 70)

    cache = load_cache()

    results = {}

    for index, wallet in enumerate(WALLETS, start=1):

        print()
        print("=" * 70)
        print(f"WALLET {index}/{len(WALLETS)}")
        print(wallet)
        print("=" * 70)

        # Kalau sudah ada cache, gunakan cache
        if wallet in cache:

            print("Menggunakan data cache.")

            results[wallet] = cache[wallet]

            continue

        data = get_wallet_pnl(wallet)

        if not data:

            print("Tidak mendapatkan data.")

            continue

        summary = extract_summary(data)

        results[wallet] = {
            "wallet": wallet,
            "checked_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "summary": summary,
        }

        cache[wallet] = results[wallet]

        save_cache(cache)

        print("\nHASIL:")

        for key, value in summary.items():
            print(f"{key}: {value}")

        # Jeda sebelum wallet berikutnya
        if index < len(WALLETS):

            print(
                f"\nMenunggu {REQUEST_DELAY} detik..."
            )

            time.sleep(REQUEST_DELAY)

    print()
    print("=" * 70)
    print("SELESAI")
    print("=" * 70)

    save_cache(cache)


if __name__ == "__main__":
    main()
