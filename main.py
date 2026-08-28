import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BIRDEYE_API_KEY")

if not API_KEY:
    raise RuntimeError("BIRDEYE_API_KEY belum diatur")

WALLETS = [
    "F6Fh9BjBXb1GyacHto4cwqcKF4K4xK8SwEyDv9Ayp8j9",
    "9xn3JjPreFAaAEBZL3VVvcou33jrfRWhsuiNbD4sJcEe",
]

URL = "https://public-api.birdeye.so/wallet/v2/pnl/summary"

HEADERS = {
    "X-API-KEY": API_KEY,
    "x-chain": "solana",
}


def get_value(obj, key):

    if isinstance(obj, dict):

        if key in obj:
            return obj[key]

        for value in obj.values():

            result = get_value(value, key)

            if result is not None:
                return result

    elif isinstance(obj, list):

        for item in obj:

            result = get_value(item, key)

            if result is not None:
                return result

    return None


def analyze_wallet(wallet):

    params = {
        "wallet": wallet,
        "duration": "90d",
        "position_scope": "duration_only",
        "pnl_method": "net_cash",
    }

    response = requests.get(
        URL,
        headers=HEADERS,
        params=params,
        timeout=30,
    )

    if response.status_code != 200:

        return {
            "wallet": wallet,
            "http": response.status_code,
            "error": response.text[:300],
        }

    data = response.json()

    result = {
        "wallet": wallet,
        "http": 200,
        "total_trade": get_value(data, "total_trade"),
        "total_win": get_value(data, "total_win"),
        "total_loss": get_value(data, "total_loss"),
        "win_rate": get_value(data, "win_rate"),
        "realized_pnl": get_value(
            data,
            "realized_profit_usd"
        ),
        "unrealized_pnl": get_value(
            data,
            "unrealized_usd"
        ),
        "total_pnl": get_value(
            data,
            "total_usd"
        ),
    }

    return result


def main():

    results = []

    for i, wallet in enumerate(WALLETS):

        result = analyze_wallet(wallet)

        results.append(result)

        # Delay agar tidak kena 429
        if i < len(WALLETS) - 1:
            time.sleep(8)

    # SATU LOG ENTRY
    print(
        "WALLET_ANALYSIS="
        + json.dumps(
            results,
            separators=(",", ":")
        )
    )


if __name__ == "__main__":
    main()
