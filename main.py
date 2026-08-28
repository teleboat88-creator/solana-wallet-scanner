import os
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

    # Urutkan berdasarkan total PnL
    tokens = sorted(
        tokens,
        key=lambda x: x.get("pnl", {}).get(
            "total_usd", 0
        ),
        reverse=True
    )

    print(
        "TOKEN_COUNT="
        + str(len(tokens))
    )

    print(
        "TOKEN_RESULTS_START"
    )

    for i, token in enumerate(tokens, start=1):

        pnl = token.get("pnl", {})
        counts = token.get("counts", {})
        pricing = token.get("pricing", {})

        result = (
            f"{i}|"
            f"{token.get('symbol')}|"
            f"{token.get('address')}|"
            f"BUY={counts.get('total_buy')}|"
            f"SELL={counts.get('total_sell')}|"
            f"TRADE={counts.get('total_trade')}|"
            f"REALIZED=${pnl.get('realized_profit_usd')}|"
            f"UNREALIZED=${pnl.get('unrealized_usd')}|"
            f"TOTAL=${pnl.get('total_usd')}|"
            f"ROI={pnl.get('total_percent')}%|"
            f"AVG_BUY=${pricing.get('avg_buy_cost')}"
        )

        print(result)

    print(
        "TOKEN_RESULTS_END"
    )


if __name__ == "__main__":
    main()
