import os
import json
import time
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

    print("Mengambil detail wallet...")

    response = requests.post(
        URL,
        headers=HEADERS,
        json=payload,
        timeout=30,
    )

    print("HTTP:", response.status_code)

    if response.status_code != 200:
        print("ERROR:", response.text)
        return

    data = response.json()

    # Hanya tampilkan struktur utama
    result = data.get("data", {})

    print(
        "DATA_KEYS="
        + json.dumps(
            list(result.keys()),
            separators=(",", ":")
        )
    )

    for key, value in result.items():

        if isinstance(value, list):
            info = {
                "key": key,
                "type": "list",
                "length": len(value)
            }

        elif isinstance(value, dict):
            info = {
                "key": key,
                "type": "dict",
                "keys": list(value.keys())
            }

        else:
            info = {
                "key": key,
                "type": type(value).__name__,
                "value": value
            }

        print(
            "FIELD="
            + json.dumps(
                info,
                separators=(",", ":")
            )
        )


if __name__ == "__main__":
    main()
