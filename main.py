import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BIRDEYE_API_KEY")

if not API_KEY:
    raise RuntimeError("BIRDEYE_API_KEY belum diatur")

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

    print("Mengambil PnL Details...")
    print("Wallet:", WALLET)

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

    # Jangan print JSON besar.
    # Kita ambil data untuk mengetahui struktur response.
    print(
        "DETAIL_SUCCESS="
        + json.dumps(
            {
                "wallet": WALLET,
                "http": response.status_code,
                "top_level_keys": list(data.keys()),
                "data_type": type(
                    data.get("data")
                ).__name__,
            },
            separators=(",", ":")
        )
    )

    # Simpan response mentah secara lokal
    with open(
        "wallet_details.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2
        )

    print("DETAIL_SAVED=wallet_details.json")


if __name__ == "__main__":
    main()
