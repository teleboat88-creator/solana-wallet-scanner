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
    url = f"{BASE_URL}/wallet/v2/pnl"

    params = {
        "wallet": wallet,
        "duration": "90d",
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

    params = {
        "wallet": wallet,
        "duration": "90d",
        "position_scope": "duration_only",
        "limit": 100,
        "offset": 0,
    }

    response = requests.post(
        url,
        headers=HEADERS,
        json=params,
        timeout=30,
    )

    print("DETAIL HTTP:", response.status_code)

    if response.status_code != 200:
        print(response.text)
        return None

    return response.json()


def print_result(wallet, pnl, details):

    print("\n" + "=" * 70)
    print("WALLET")
    print(wallet)
    print("=" * 70)

    print("\n--- PNL SUMMARY ---")

    if pnl:
        print(pnl)

    print("\n--- PNL DETAILS ---")

    if details:
        print(details)


def main():

    print("SOLANA WALLET ANALYZER")
    print("Analyzing", len(WALLETS), "wallets...\n")

    for wallet in WALLETS:

        print("\nAnalyzing wallet:")
        print(wallet)

        pnl = get_wallet_pnl(wallet)

        details = get_wallet_pnl_details(wallet)

        print_result(
            wallet,
            pnl,
            details,
        )


if __name__ == "__main__":
    main()
