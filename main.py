import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BIRDEYE_API_KEY")

if not API_KEY:
    raise RuntimeError("BIRDEYE_API_KEY belum diatur")

WALLETS = [
    {
        "name": "CORE_CANDIDATE",
        "address": "9xn3JjPreFAaAEBZL3VVvcou33jrfRWhsuiNbD4sJcEe",
    },
    {
        "name": "CONTROL",
        "address": "F6Fh9BjBXb1GyacHto4cwqcKF4K4xK8SwEyDv9Ayp8j9",
    },
]

BASE_URL = "https://public-api.birdeye.so"

HEADERS = {
    "X-API-KEY": API_KEY,
    "x-chain": "solana",
}


def get_pnl(wallet):

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

    if response.status_code != 200:
        print(
            f"PNL ERROR {wallet}: "
            f"{response.status_code}"
        )
        return None

    return response.json()


def get_details(wallet):

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

    if response.status_code != 200:
        print(
            f"DETAIL ERROR {wallet}: "
            f"{response.status_code}"
        )
        return None

    return response.json()


def safe_number(value):

    if value is None:
        return 0

    try:
        return float(value)
    except:
        return 0


def calculate_score(summary, tokens):

    counts = summary.get("counts", {})
    pnl = summary.get("pnl", {})

    total_trade = safe_number(
        counts.get("total_trade")
    )

    win_rate = safe_number(
        counts.get("win_rate")
    )

    realized = safe_number(
        pnl.get("realized_profit_usd")
    )

    unrealized = safe_number(
        pnl.get("unrealized_usd")
    )

    total_pnl = safe_number(
        pnl.get("total_usd")
    )

    # -----------------------------
    # 1. WIN RATE — 25 POINTS
    # -----------------------------

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

    # -----------------------------
    # 2. REALIZED PNL — 25 POINTS
    # -----------------------------

    if realized > 50000:
        realized_score = 25
    elif realized > 25000:
        realized_score = 22
    elif realized > 10000:
        realized_score = 18
    elif realized > 0:
        realized_score = 12
    else:
        realized_score = 0

    # -----------------------------
    # 3. TRADE EXPERIENCE — 15
    # -----------------------------

    if total_trade >= 500:
        trade_score = 15
    elif total_trade >= 200:
        trade_score = 13
    elif total_trade >= 100:
        trade_score = 11
    elif total_trade >= 50:
        trade_score = 8
    else:
        trade_score = 4

    # -----------------------------
    # 4. PROFIT DIVERSIFICATION
    # -----------------------------

    profitable_tokens = []

    for token in tokens:

        token_pnl = safe_number(
            token.get("pnl", {}).get(
                "realized_profit_usd"
            )
        )

        if token_pnl > 0:
            profitable_tokens.append(
                token_pnl
            )

    if len(profitable_tokens) >= 5:
        diversity_score = 15
    elif len(profitable_tokens) >= 3:
        diversity_score = 12
    elif len(profitable_tokens) >= 2:
        diversity_score = 9
    elif len(profitable_tokens) >= 1:
        diversity_score = 5
    else:
        diversity_score = 0

    # -----------------------------
    # 5. UNREALIZED RISK — 20
    # -----------------------------

    if total_pnl > 0:

        unrealized_ratio = (
            max(unrealized, 0)
            / total_pnl
        )

    else:
        unrealized_ratio = 1

    if unrealized_ratio < 0.30:
        risk_score = 20
    elif unrealized_ratio < 0.50:
        risk_score = 16
    elif unrealized_ratio < 0.70:
        risk_score = 12
    elif unrealized_ratio < 0.85:
        risk_score = 7
    else:
        risk_score = 3

    score = (
        win_score
        + realized_score
        + trade_score
        + diversity_score
        + risk_score
    )

    return {
        "score": score,
        "win_score": win_score,
        "realized_score": realized_score,
        "trade_score": trade_score,
        "diversity_score": diversity_score,
        "risk_score": risk_score,
        "unrealized_ratio": unrealized_ratio,
    }


def analyze_wallet(wallet_info):

    wallet = wallet_info["address"]
    name = wallet_info["name"]

    print()
    print("=" * 70)
    print(name)
    print(wallet)
    print("=" * 70)

    pnl_data = get_pnl(wallet)

    if not pnl_data:
        return

    detail_data = get_details(wallet)

    if not detail_data:
        return

    summary = (
        detail_data
        .get("
