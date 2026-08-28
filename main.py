import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BIRDEYE_API_KEY")

if not API_KEY:
    raise RuntimeError("BIRDEYE_API_KEY belum diatur")

WALLETS = [
    ("CORE_CANDIDATE", "9xn3JjPreFAaAEBZL3VVvcou33jrfRWhsuiNbD4sJcEe"),
    ("CONTROL", "F6Fh9BjBXb1GyacHto4cwqcKF4K4xK8SwEyDv9Ayp8j9"),
]

BASE_URL = "https://public-api.birdeye.so"

HEADERS = {
    "X-API-KEY": API_KEY,
    "x-chain": "solana"
}


def num(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def get_summary(wallet):

    r = requests.get(
        f"{BASE_URL}/wallet/v2/pnl/summary",
        headers=HEADERS,
        params={
            "wallet": wallet,
            "duration": "90d",
            "position_scope": "duration_only",
            "pnl_method": "net_cash"
        },
        timeout=30
    )

    if r.status_code != 200:
        print(
            f"SUMMARY ERROR {r.status_code}: "
            f"{r.text[:300]}"
        )
        return None

    return r.json()


def get_details(wallet):

    r = requests.post(
        f"{BASE_URL}/wallet/v2/pnl/details",
        headers=HEADERS,
        json={
            "wallet": wallet,
            "duration": "90d",
            "position_scope": "duration_only",
            "pnl_method": "net_cash",
            "sort_by": "last_trade",
            "sort_type": "desc",
            "limit": 100,
            "offset": 0
        },
        timeout=30
    )

    if r.status_code != 200:
        print(
            f"DETAIL ERROR {r.status_code}: "
            f"{r.text[:300]}"
        )
        return None

    return r.json()


def score_wallet(summary, tokens):

    counts = summary.get("counts", {})
    pnl = summary.get("pnl", {})

    trades = num(
        counts.get("total_trade")
    )

    win_rate = num(
        counts.get("win_rate")
    )

    realized = num(
        pnl.get("realized_profit_usd")
    )

    unrealized = num(
        pnl.get("unrealized_usd")
    )

    total = num(
        pnl.get("total_usd")
    )

    # WIN RATE

    if win_rate >= 0.70:
        win_score = 25
    elif win_rate >= 0.60:
        win_score = 22
    elif win_rate >= 0.50:
        win_score = 18
    elif win_rate >= 0.40:
        win_score = 12
    else:
        win_score = 5

    # REALIZED PNL

    if realized >= 50000:
        realized_score = 25
    elif realized >= 25000:
        realized_score = 22
    elif realized >= 10000:
        realized_score = 18
    elif realized > 0:
        realized_score = 12
    else:
        realized_score = 0

    # EXPERIENCE

    if trades >= 500:
        trade_score = 15
    elif trades >= 200:
        trade_score = 13
    elif trades >= 100:
        trade_score = 11
    elif trades >= 50:
        trade_score = 8
    else:
        trade_score = 4

    # PROFITABLE TOKENS

    profitable = sum(
        1
        for token in tokens
        if num(
            token.get("pnl", {}).get(
                "realized_profit_usd"
            )
        ) > 0
    )

    if profitable >= 5:
        diversity_score = 15
    elif profitable >= 3:
        diversity_score = 12
    elif profitable >= 2:
        diversity_score = 9
    elif profitable >= 1:
        diversity_score = 5
    else:
        diversity_score = 0

    # UNREALIZED RISK

    if total > 0:
        ratio = max(unrealized, 0) / total
    else:
        ratio = 1.0

    if ratio < 0.30:
        risk_score = 20
    elif ratio < 0.50:
        risk_score = 16
    elif ratio < 0.70:
        risk_score = 12
    elif ratio < 0.85:
        risk_score = 7
    else:
        risk_score = 3

    total_score = (
        win_score
        + realized_score
        + trade_score
        + diversity_score
        + risk_score
    )

    return (
        total_score,
        win_score,
        realized_score,
        trade_score,
        diversity_score,
        risk_score
    )


def analyze(name, wallet):

    print()
    print("=" * 60)
    print(name)
    print(wallet)
    print("=" * 60)

    summary_data = get_summary(wallet)

    details_data = get_details(wallet)

    if not summary_data or not details_data:
        return

    summary = (
        details_data
        .get("data", {})
        .get("summary", {})
    )

    tokens = (
        details_data
        .get("data", {})
        .get("tokens", [])
    )

    counts = summary.get(
        "counts",
        {}
    )

    pnl = summary.get(
        "pnl",
        {}
    )

    score = score_wallet(
        summary,
        tokens
    )

    print(
        f"Total Trade : "
        f"{counts.get('total_trade')}"
    )

    print(
        f"Win Rate    : "
        f"{num(counts.get('win_rate')) * 100:.2f}%"
    )

    print(
        f"Realized    : "
        f"${num(pnl.get('realized_profit_usd')):,.2f}"
    )

    print(
        f"Unrealized  : "
        f"${num(pnl.get('unrealized_usd')):,.2f}"
    )

    print(
        f"Total PnL   : "
        f"${num(pnl.get('total_usd')):,.2f}"
    )

    print(
        f"Tokens      : "
        f"{len(tokens)}"
    )

    print()
    print("SMART SCORE")
    print("-----------")

    print(
        f"Total            : "
        f"{score[0]}/100"
    )

    print(
        f"Win Rate         : "
        f"{score[1]}/25"
    )

    print(
        f"Realized PnL     : "
        f"{score[2]}/25"
    )

    print(
        f"Experience       : "
        f"{score[3]}/15"
    )

    print(
        f"Diversification  : "
        f"{score[4]}/15"
    )

    print(
        f"Risk             : "
        f"{score[5]}/20"
    )

    if score[0] >= 80:
        status = "CORE"
    elif score[0] >= 65:
        status = "WATCH"
    else:
        status = "REJECT"

    print(
        f"STATUS           : "
        f"{status}"
    )

    print()
    print("TOP 5 TOKENS")
    print("------------")

    ranked = sorted(
        tokens,
        key=lambda t: num(
            t.get("pnl", {}).get(
                "total_usd"
            )
        ),
        reverse=True
    )

    for i, token in enumerate(
        ranked[:5],
        1
    ):

        p = token.get(
            "pnl",
            {}
        )

        print(
            f"{i}. "
            f"{token.get('symbol', 'UNKNOWN')} | "
            f"PnL=${num(p.get('total_usd')):,.2f} | "
            f"ROI={num(p.get('total_percent')):.2f}%"
        )


def main():

    print(
        "SMART MONEY WALLET ANALYZER V7"
    )

    for i, (name, wallet) in enumerate(
        WALLETS
    ):

        analyze(
            name,
            wallet
        )

        if i < len(WALLETS) - 1:

            print()
            print(
                "Waiting 10 seconds..."
            )

            time.sleep(10)

    print()
    print(
        "ANALYSIS COMPLETE"
    )


if __name__ == "__main__":
    main()
