import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BIRDEYE_API_KEY")

WALLET = "9xn3JjPreFAaAEBZL3VVvcou33jrfRWhsuiNbD4sJcEe"

URL = "https://public-api.birdeye.so/wallet/v2/pnl/details"

HEADERS = {
    "X-API-KEY": API_KEY,
    "x-chain": "solana",
}


def main():

    payload = {
        "wallet": WALLET,
        "duration": "90d",
        "position_scope": "duration_only",
        "pnl_method": "net_cash",
        "sort_by": "last_trade",
        "sort_type": "desc",
        "limit": 100,
        "offset": 0,
    }

    response = requests.post(
        URL,
        headers=HEADERS,
        json=payload,
        timeout=30,
    )

    print("HTTP:", response.status_code)

    if response.status_code != 200:
        print(response.text)
        return

    data = response.json()

    tokens = data["data"]["tokens"]

    print(
        "TOKEN_COUNT="
        + str(len(tokens))
    )

    # Tampilkan struktur token pertama
    if tokens:

        print(
            "FIRST_TOKEN="
            + json.dumps(
                tokens[0],
                separators=(",", ":")
            )
        )

        print(
            "TOKEN_KEYS="
            + json.dumps(
                list(tokens[0].keys()),
                separators=(",", ":")
            )
        )

    print("TOKEN_ANALYSIS_READY")


if __name__ == "__main__":
    main()
