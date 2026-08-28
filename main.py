import os
import time
import requests
from dotenv import load_dotenv

# ============================================================
# SMART MONEY WALLET ANALYZER V8
# ============================================================

load_dotenv()

API_KEY = os.getenv("BIRDEYE_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "BIRDEYE_API_KEY belum diatur"
    )


# ============================================================
# CONFIG
# ============================================================

WALLETS = [
    (
        "CORE_CANDIDATE",
        "9xn3JjPreFAaAEBZL3VVvcou33jrfRWhsuiNbD4sJcEe"
    ),
    (
        "CONTROL",
        "F6Fh9BjBXb1GyacHto4cwqcKF4K4xK8SwEyDv9Ayp8j9"
    ),
]

BASE_URL = "https://public-api.birdeye.so"

HEADERS = {
    "X-API-KEY": API_KEY,
    "x-chain": "solana",
}

DURATION = "90d"

REQUEST_TIMEOUT = 30

DELAY_BETWEEN_WALLETS = 10


# ============================================================
# HELPERS
# ============================================================

def num(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def pct(value):
    """
    Birdeye win_rate biasanya berbentuk decimal.
    Contoh:
    0.65 = 65%
    """

    value = num(value)

    if value <= 1:
        return value * 100

    return value


def money(value):
    return f"${num(value):,.2f}"


def safe_text(value, default="UNKNOWN"):
    if value is None:
        return default

    value = str(value).strip()

    return value if value else default


# ============================================================
# BIRDEYE API
# ============================================================

def request_get(endpoint, params):
    try:

        response = requests.get(
            f"{BASE_URL}{endpoint}",
            headers=HEADERS,
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code != 200:

            print(
                f"API ERROR {response.status_code}: "
                f"{response.text[:500]}"
            )

            return None

        return response.json()

    except requests.RequestException as e:

        print(
            f"REQUEST ERROR: {e}"
        )

        return None

    except ValueError as e:

        print(
            f"JSON ERROR: {e}"
        )

        return None


def request_post(endpoint, payload):
    try:

        response = requests.post(
            f"{BASE_URL}{endpoint}",
            headers=HEADERS,
            json=payload,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code != 200:

            print(
                f"API ERROR {response.status_code}: "
                f"{response.text[:500]}"
            )

            return None

        return response.json()

    except requests.RequestException as e:

        print(
            f"REQUEST ERROR: {e}"
        )

        return None

    except ValueError as e:

        print(
            f"JSON ERROR: {e}"
        )

        return None


# ============================================================
# WALLET SUMMARY
# ============================================================

def get_summary(wallet):

    return request_get(
        "/wallet/v2/pnl/summary",
        {
            "wallet": wallet,
            "duration": DURATION,
            "position_scope": "duration_only",
            "pnl_method": "net_cash",
        }
    )


# ============================================================
# WALLET DETAILS
# ============================================================

def get_details(wallet):

    return request_post(
        "/wallet/v2/pnl/details",
        {
            "wallet": wallet,
            "duration": DURATION,
            "position_scope": "duration_only",
            "pnl_method": "net_cash",
            "sort_by": "last_trade",
            "sort_type": "desc",
            "limit": 100,
            "offset": 0,
        }
    )


# ============================================================
# EXTRACT DATA
# ============================================================

def extract_summary(summary_data, details_data):

    summary = {}

    if isinstance(summary_data, dict):

        summary = (
            summary_data
            .get("data", {})
        )

    if not summary:

        summary = (
            details_data
            .get("data", {})
            .get("summary", {})
        )

    if not isinstance(summary, dict):

        summary = {}

    return summary


def extract_tokens(details_data):

    if not isinstance(details_data, dict):

        return []

    data = details_data.get(
        "data",
        {}
    )

    tokens = data.get(
        "tokens",
        []
    )

    if not isinstance(tokens, list):

        return []

    return tokens


# ============================================================
# TOKEN ANALYSIS
# ============================================================

def analyze_tokens(tokens):

    result = {
        "total": 0,
        "profitable": 0,
        "losing": 0,
        "open_profit": 0,
        "open_loss": 0,
        "best": None,
        "worst": None,
    }

    if not tokens:

        return result

    result["total"] = len(tokens)

    ranked = []

    for token in tokens:

        pnl = token.get(
            "pnl",
            {}
        )

        total_usd = num(
            pnl.get("total_usd")
        )

        realized = num(
            pnl.get("realized_profit_usd")
        )

        unrealized = num(
            pnl.get("unrealized_usd")
        )

        total_percent = num(
            pnl.get("total_percent")
        )

        symbol = safe_text(
            token.get("symbol")
        )

        address = safe_text(
            token.get(
                "address",
                token.get(
                    "token_address",
                    ""
                )
            ),
            ""
        )

        item = {
            "symbol": symbol,
            "address": address,
            "total_usd": total_usd,
            "realized": realized,
            "unrealized": unrealized,
            "percent": total_percent,
        }

        ranked.append(item)

        if total_usd > 0:

            result["profitable"] += 1

        elif total_usd < 0:

            result["losing"] += 1

        if unrealized > 0:

            result["open_profit"] += 1

        elif unrealized < 0:

            result["open_loss"] += 1

    ranked.sort(
        key=lambda x: x["total_usd"],
        reverse=True
    )

    if ranked:

        result["best"] = ranked[0]

        result["worst"] = ranked[-1]

    result["ranked"] = ranked

    return result


# ============================================================
# SMART SCORE V8
# ============================================================

def score_wallet(summary, token_analysis):

    counts = summary.get(
        "counts",
        {}
    )

    pnl = summary.get(
        "pnl",
        {}
    )

    # --------------------------------------------------------
    # TRADING ACTIVITY
    # --------------------------------------------------------

    buys = num(
        counts.get("total_buy")
    )

    sells = num(
        counts.get("total_sell")
    )

    trades = num(
        counts.get("total_trade")
    )

    # fallback
    if trades <= 0:

        trades = buys + sells

    # --------------------------------------------------------
    # WIN RATE
    # --------------------------------------------------------

    win_rate = pct(
        counts.get("win_rate")
    )

    if win_rate >= 70:
        win_score = 25

    elif win_rate >= 60:
        win_score = 22

    elif win_rate >= 50:
        win_score = 18

    elif win_rate >= 40:
        win_score = 12

    else:
        win_score = 5

    # --------------------------------------------------------
    # REALIZED PNL
    # --------------------------------------------------------

    realized = num(
        pnl.get(
            "realized_profit_usd"
        )
    )

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

    # --------------------------------------------------------
    # EXPERIENCE
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # PROFITABLE TOKENS
    # --------------------------------------------------------

    profitable = token_analysis["profitable"]

    if profitable >= 10:
        diversity_score = 15

    elif profitable >= 5:
        diversity_score = 13

    elif profitable >= 3:
        diversity_score = 11

    elif profitable >= 2:
        diversity_score = 8

    elif profitable >= 1:
        diversity_score = 5

    else:
        diversity_score = 0

    # --------------------------------------------------------
    # REALIZED VS UNREALIZED RISK
    # --------------------------------------------------------

    unrealized = num(
        pnl.get(
            "unrealized_usd"
        )
    )

    total = num(
        pnl.get(
            "total_usd"
        )
    )

    if total > 0:

        ratio = max(
            unrealized,
            0
        ) / total

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

    # --------------------------------------------------------
    # BUY / SELL BALANCE
    # --------------------------------------------------------

    if buys > 0:

        sell_ratio = sells / buys

    else:

        sell_ratio = 0

    if 0.30 <= sell_ratio <= 1.50:

        execution_score = 10

    elif sell_ratio > 0:

        execution_score = 6

    else:

        execution_score = 2

    # --------------------------------------------------------
    # TOTAL
    # --------------------------------------------------------

    raw_total = (
        win_score
        + realized_score
        + trade_score
        + diversity_score
        + risk_score
    )

    # V8 uses execution as secondary modifier
    # to avoid changing the original 100-point model.

    if execution_score >= 10:

        final_score = min(
            100,
            raw_total + 2
        )

    elif execution_score <= 2:

        final_score = max(
            0,
            raw_total - 2
        )

    else:

        final_score = raw_total

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if final_score >= 80:

        status = "CORE"

    elif final_score >= 70:

        status = "STRONG WATCH"

    elif final_score >= 65:

        status = "WATCH"

    elif final_score >= 50:

        status = "WEAK"

    else:

        status = "REJECT"

    return {
        "total": final_score,
        "win": win_score,
        "realized": realized_score,
        "experience": trade_score,
        "diversity": diversity_score,
        "risk": risk_score,
        "execution": execution_score,
        "status": status,
        "buys": buys,
        "sells": sells,
        "trades": trades,
        "win_rate": win_rate,
        "realized_usd": realized,
    }


# ============================================================
# WALLET ANALYSIS
# ============================================================

def analyze(name, wallet):

    print()
    print("=" * 70)
    print(f"SMART MONEY V8 | {name}")
    print(wallet)
    print("=" * 70)

    # --------------------------------------------------------
    # GET DATA
    # --------------------------------------------------------

    summary_data = get_summary(
        wallet
    )

    if not summary_data:

        print(
            "Gagal mengambil wallet summary."
        )

        return None

    details_data = get_details(
        wallet
    )

    if not details_data:

        print(
            "Gagal mengambil wallet details."
        )

        return None

    # --------------------------------------------------------
    # EXTRACT
    # --------------------------------------------------------

    summary = extract_summary(
        summary_data,
        details_data
    )

    tokens = extract_tokens(
        details_data
    )

    if not summary:

        print(
            "Summary kosong."
        )

        return None

    # --------------------------------------------------------
    # ANALYSIS
    # --------------------------------------------------------

    token_analysis = analyze_tokens(
        tokens
    )

    score = score_wallet(
        summary,
        token_analysis
    )

    counts = summary.get(
        "counts",
        {}
    )

    pnl = summary.get(
        "pnl",
        {}
    )

    cashflow = summary.get(
        "cashflow_usd",
        {}
    )

    # --------------------------------------------------------
    # BASIC STATS
    # --------------------------------------------------------

    print()
    print("WALLET STATISTICS")
    print("------------------")

    print(
        f"BUY         : "
        f"{counts.get('total_buy', 0)}"
    )

    print(
        f"SELL        : "
        f"{counts.get('total_sell', 0)}"
    )

    print(
        f"TRADE       : "
        f"{counts.get('total_trade', 0)}"
    )

    print(
        f"WIN RATE    : "
        f"{score['win_rate']:.2f}%"
    )

    print(
        f"WIN         : "
        f"{counts.get('total_win', 0)}"
    )

    print(
        f"LOSS        : "
        f"{counts.get('total_loss', 0)}"
    )

    print(
        f"TOKENS      : "
        f"{len(tokens)}"
    )

    # --------------------------------------------------------
    # PNL
    # --------------------------------------------------------

    print()
    print("PNL")
    print("---")

    print(
        f"Invested    : "
        f"{money(cashflow.get('total_invested'))}"
    )

    print(
        f"Sold        : "
        f"{money(cashflow.get('total_sold'))}"
    )

    print(
        f"Current     : "
        f"{money(cashflow.get('current_value'))}"
    )

    print(
        f"Realized    : "
        f"{money(pnl.get('realized_profit_usd'))}"
    )

    print(
        f"Unrealized  : "
        f"{money(pnl.get('unrealized_usd'))}"
    )

    print(
        f"Total PnL   : "
        f"{money(pnl.get('total_usd'))}"
    )

    print(
        f"Avg Trade   : "
        f"{money(pnl.get('avg_profit_per_trade_usd'))}"
    )

    # --------------------------------------------------------
    # SMART SCORE
    # --------------------------------------------------------

    print()
    print("SMART SCORE V8")
    print("--------------")

    print(
        f"TOTAL          : "
        f"{score['total']}/100"
    )

    print(
        f"Win Rate       : "
        f"{score['win']}/25"
    )

    print(
        f"Realized PnL   : "
        f"{score['realized']}/25"
    )

    print(
        f"Experience     : "
        f"{score['experience']}/15"
    )

    print(
        f"Diversification: "
        f"{score['diversity']}/15"
    )

    print(
        f"Risk           : "
        f"{score['risk']}/20"
    )

    print(
        f"Execution      : "
        f"{score['execution']}/10"
    )

    print(
        f"STATUS         : "
        f"{score['status']}"
    )

    # --------------------------------------------------------
    # TOKEN QUALITY
    # --------------------------------------------------------

    print()
    print("TOKEN QUALITY")
    print("-------------")

    print(
        f"Profitable : "
        f"{token_analysis['profitable']}"
    )

    print(
        f"Losing     : "
        f"{token_analysis['losing']}"
    )

    print(
        f"Open Profit: "
        f"{token_analysis['open_profit']}"
    )

    print(
        f"Open Loss  : "
        f"{token_analysis['open_loss']}"
    )

    # --------------------------------------------------------
    # BEST TOKEN
    # --------------------------------------------------------

    best = token_analysis.get(
        "best"
    )

    if best:

        print()
        print("BEST TOKEN")
        print("----------")

        print(
            f"{best['symbol']} | "
            f"PnL={money(best['total_usd'])} | "
            f"ROI={best['percent']:.2f}%"
        )

    # --------------------------------------------------------
    # WORST TOKEN
    # --------------------------------------------------------

    worst = token_analysis.get(
        "worst"
    )

    if worst:

        print()
        print("WORST TOKEN")
        print("-----------")

        print(
            f"{worst['symbol']} | "
            f"PnL={money(worst['total_usd'])} | "
            f"ROI={worst['percent']:.2f}%"
        )

    # --------------------------------------------------------
    # TOP TOKENS
    # --------------------------------------------------------

    print()
    print("TOP 10 TOKENS")
    print("-------------")

    ranked = token_analysis.get(
        "ranked",
        []
    )

    for i, token in enumerate(
        ranked[:10],
        1
    ):

        print(
            f"{i:02d}. "
            f"{token['symbol']:<15} "
            f"PnL={money(token['total_usd']):>15} | "
            f"ROI={token['percent']:>8.2f}%"
        )

    # --------------------------------------------------------
    # INVESTMENT SIGNAL
    # --------------------------------------------------------

    print()
    print("V8 SIGNAL")
    print("---------")

    if (
        score["total"] >= 80
        and score["win_rate"] >= 60
        and score["realized_usd"] > 0
        and token_analysis["profitable"] >= 3
    ):

        signal = "🟢 HIGH QUALITY SMART MONEY"

    elif (
        score["total"] >= 70
        and score["win_rate"] >= 50
        and score["realized_usd"] > 0
    ):

        signal = "🟡 SMART MONEY WATCH"

    elif score["total"] >= 60:

        signal = "🟠 NEED MORE DATA"

    else:

        signal = "🔴 LOW QUALITY"

    print(signal)

    print()
    print("-" * 70)

    return {
        "name": name,
        "wallet": wallet,
        "score": score,
        "tokens": token_analysis,
        "summary": summary,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print(
        "=============================================="
    )

    print(
        "      SMART MONEY WALLET ANALYZER V8"
    )

    print(
        "=============================================="
    )

    print(
        f"Duration : {DURATION}"
    )

    print(
        f"Wallets  : {len(WALLETS)}"
    )

    results = []

    # --------------------------------------------------------
    # ANALYZE ALL WALLETS
    # --------------------------------------------------------

    for index, (name, wallet) in enumerate(
        WALLETS
    ):

        result = analyze(
            name,
            wallet
        )

        if result:

            results.append(
                result
            )

        if index < len(WALLETS) - 1:

            print()
            print(
                f"Waiting "
                f"{DELAY_BETWEEN_WALLETS} seconds..."
            )

            time.sleep(
                DELAY_BETWEEN_WALLETS
            )

    # --------------------------------------------------------
    # FINAL COMPARISON
    # --------------------------------------------------------

    print()
    print()
    print(
        "=============================================="
    )

    print(
        "              V8 FINAL RANKING"
    )

    print(
        "=============================================="
    )

    ranked_wallets = sorted(
        results,
        key=lambda x: x["score"]["total"],
        reverse=True
    )

    for index, result in enumerate(
        ranked_wallets,
        1
    ):

        score = result["score"]

        print(
            f"{index}. "
            f"{result['name']} | "
            f"SCORE={score['total']}/100 | "
            f"WR={score['win_rate']:.1f}% | "
            f"BUY={int(score['buys'])} | "
            f"SELL={int(score['sells'])} | "
            f"{score['status']}"
        )

    # --------------------------------------------------------
    # WINNER
    # --------------------------------------------------------

    if ranked_wallets:

        winner = ranked_wallets[0]

        print()
        print(
            "V8 BEST WALLET"
        )

        print(
            f"{winner['name']}"
        )

        print(
            f"Score : "
            f"{winner['score']['total']}/100"
        )

        print(
            f"Status: "
            f"{winner['score']['status']}"
        )

    print()
    print(
        "ANALYSIS COMPLETE"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
