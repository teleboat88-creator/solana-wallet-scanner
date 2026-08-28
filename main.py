import os
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

BASE_URL = "https://public-api.birdeye.so"

HEADERS = {
    "X-API-KEY": API_KEY,
    "x-chain": "solana",
}


def get_wallet_pnl(wallet):
    url = f"{BASE_URL}/wallet/v2/pnl/summary"

    params = {
        "wallet": wallet,
        "duration": "90d",
        "position_scope": "duration_only",
        "pnl_method": "net_cash",
    }

    response = requests.get(
        url,
        headers=HEADERS,
        params=params,
        timeout=30,
    )

    print("PNL HTTP:", response.status_code)

    if response.status_code != 200:
        print(response.text)
        return None

    return response.json()


def get_wallet_pnl_details(wallet):
    url = f"{BASE_URL}/wallet/v2/pnl/details"

    payload = {
        "wallet": wallet,
        "duration": "90d",
        "position_scope": "duration_only",
        "pnl_method": "net_cash",
        "sort_by": "last_trade",
        "sort_type": "desc",
        "limit": 100,
        "offset": 0,
    }

    response = requests.post(
        url,
        headers=HEADERS,
        json=payload,
        timeout=30,
    )

    print("DETAIL HTTP:", response.status_code)

    if response.status_code != 200:
        print(response.text)
        return None

    return response.json()


def main():

    print("=" * 70)
    print("SOLANA WALLET ANALYZER")
    print("=" * 70)
    print(f"Analyzing {len(WALLETS)} wallets...\n")

    for wallet in WALLETS:

        print("\n" + "=" * 70)
        print("WALLET:")
        print(wallet)
        print("=" * 70)

        pnl = get_wallet_pnl(wallet)

        if pnl:
            print("\n--- PNL SUMMARY ---")
            print(pnl)

        details = get_wallet_pnl_details(wallet)

        if details:
            print("\n--- PNL DETAILS ---")
            print(details)


if __name__ == "__main__":
    main()
