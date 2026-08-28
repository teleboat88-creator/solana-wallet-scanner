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
    """
    Mencari key secara rekursif di seluruh JSON.
    """
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

    print()
    print("=" * 70)
    print("WALLET")
    print(wallet)
    print("=" * 70)

    response = requests.get(
        URL,
        headers=HEADERS,
        params=params,
        timeout=30,
    )

    print("HTTP:", response.status_code)

    if response.status_code != 200:

        print("ERROR:")
        print(response.text)

        return None

    data = response.json()

    total_trade = get_value(data, "total_trade")
    total_win = get_value(data, "total_win")
    total_loss = get_value(data, "total_loss")
    win_rate = get_value(data, "win_rate")

    realized = get_value(data, "realized_profit_usd")
    unrealized = get_value(data, "unrealized_usd")
    total_pnl = get_value(data, "total_usd")

    print()
    print("------ WALLET PERFORMANCE ------")

    print("Total Trade :", total_trade)
    print("Win         :", total_win)
    print("Loss        :", total_loss)
    print("Win Rate    :", win_rate)

    print("Realized PnL:", realized)
    print("Unrealized   :", unrealized)
    print("Total PnL    :", total_pnl)

    return {
        "wallet": wallet,
        "total_trade": total_trade,
        "total_win": total_win,
        "total_loss": total_loss,
        "win_rate": win_rate,
        "realized_pnl": realized,
        "unrealized_pnl": unrealized,
        "total_pnl": total_pnl,
    }


def main():

    print("=" * 70)
    print("SOLANA WALLET ANALYZER")
    print("=" * 70)

    results = []

    for i, wallet in enumerate(WALLETS):

        result = analyze_wallet(wallet)

        if result:
            results.append(result)

        # Jangan langsung request wallet kedua
        if i < len(WALLETS) - 1:

            print()
            print("Menunggu 8 detik untuk rate limit...")
            time.sleep(8)

    print()
    print("=" * 70)
    print("ANALISIS SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    main()
