import os
import time
import json
import requests
from dotenv import load_dotenv

# ============================================================
# SMART MONEY WALLET MONITOR V9
# SOLANA + BIRDEYE + TELEGRAM
# ============================================================

load_dotenv()

# ============================================================
# ENV
# ============================================================

API_KEY = os.getenv("BIRDEYE_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not API_KEY:
    raise RuntimeError("BIRDEYE_API_KEY belum diatur")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN belum diatur")

if not TELEGRAM_CHAT_ID:
    raise RuntimeError("TELEGRAM_CHAT_ID belum diatur")


# ============================================================
# WALLET
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


# ============================================================
# CONFIG
# ============================================================

BASE_URL = "https://public-api.birdeye.so"

HEADERS = {
    "X-API-KEY": API_KEY,
    "x-chain": "solana",
}

# Jangan terlalu kecil.
# Wallet API mempunyai rate limit khusus.
POLL_INTERVAL = 20

REQUEST_TIMEOUT = 30

MAX_RETRIES = 4

RETRY_BASE = 10

# Berapa transaksi terakhir yang diminta
TX_LIMIT = 20

# Cache token
TOKEN_CACHE_FILE = "token_cache.json"

# Transaksi yang sudah pernah diproses
SEEN_FILE = "seen_transactions.json"

# Maksimal item cache
MAX_SEEN = 500


# ============================================================
# MEMORY
# ============================================================

token_cache = {}
seen_transactions = set()


# ============================================================
# BASIC HELPERS
# ============================================================

def num(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def safe_text(value, default="UNKNOWN"):

    if value is None:
        return default

    value = str(value).strip()

    if not value:
        return default

    return value


def money(value):

    return f"${num(value):,.2f}"


def shorten(value, length=12):

    value = safe_text(value, "")

    if not value:
        return ""

    if len(value) <= length:
        return value

    return value[:length] + "..."


# ============================================================
# CACHE
# ============================================================

def load_json_file(filename, default):

    try:

        if not os.path.exists(filename):
            return default

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        print(
            f"CACHE READ ERROR {filename}: {e}"
        )

        return default


def save_json_file(filename, data):

    try:

        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:

        print(
            f"CACHE WRITE ERROR {filename}: {e}"
        )


def load_cache():

    global token_cache
    global seen_transactions

    token_cache = load_json_file(
        TOKEN_CACHE_FILE,
        {}
    )

    seen = load_json_file(
        SEEN_FILE,
        []
    )

    if isinstance(seen, list):

        seen_transactions = set(seen)

    else:

        seen_transactions = set()

    print(
        f"Token cache   : {len(token_cache)}"
    )

    print(
        f"Seen tx cache  : {len(seen_transactions)}"
    )


def save_seen():

    global seen_transactions

    if len(seen_transactions) > MAX_SEEN:

        seen_transactions = set(
            list(seen_transactions)[-MAX_SEEN:]
        )

    save_json_file(
        SEEN_FILE,
        list(seen_transactions)
    )


# ============================================================
# HTTP GET
# ============================================================

def api_get(endpoint, params=None):

    for attempt in range(MAX_RETRIES):

        try:

            response = requests.get(
                f"{BASE_URL}{endpoint}",
                headers=HEADERS,
                params=params or {},
                timeout=REQUEST_TIMEOUT
            )

            # ------------------------------------------------
            # SUCCESS
            # ------------------------------------------------

            if response.status_code == 200:

                try:

                    return response.json()

                except ValueError:

                    print(
                        "INVALID JSON RESPONSE"
                    )

                    return None

            # ------------------------------------------------
            # RATE LIMIT
            # ------------------------------------------------

            if response.status_code == 429:

                wait = RETRY_BASE * (
                    2 ** attempt
                )

                print(
                    f"429 RATE LIMIT | "
                    f"retry {attempt + 1}/{MAX_RETRIES} | "
                    f"wait {wait}s"
                )

                time.sleep(wait)

                continue

            # ------------------------------------------------
            # AUTH
            # ------------------------------------------------

            if response.status_code in (
                401,
                403
            ):

                print(
                    f"AUTH ERROR "
                    f"{response.status_code}: "
                    f"{response.text[:300]}"
                )

                return None

            # ------------------------------------------------
            # OTHER ERROR
            # ------------------------------------------------

            print(
                f"API ERROR "
                f"{response.status_code}: "
                f"{response.text[:300]}"
            )

            return None

        except requests.RequestException as e:

            wait = RETRY_BASE * (
                2 ** attempt
            )

            print(
                f"REQUEST ERROR: {e} | "
                f"wait {wait}s"
            )

            time.sleep(wait)

    print(
        "API RETRY EXHAUSTED"
    )

    return None


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

    url = (
        "https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": True,
    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=20
        )

        if response.status_code != 200:

            print(
                "TELEGRAM ERROR:",
                response.text[:500]
            )

            return False

        return True

    except requests.RequestException as e:

        print(
            f"TELEGRAM REQUEST ERROR: {e}"
        )

        return False


# ============================================================
# WALLET PNL
# ============================================================

def get_wallet_profile(wallet):

    data = api_get(
        "/wallet/v2/pnl/summary",
        {
            "wallet": wallet,
            "duration": "90d",
            "position_scope": "duration_only",
            "pnl_method": "net_cash",
        }
    )

    if not data:
        return None

    return (
        data.get("data", {})
    )


# ============================================================
# WALLET TRANSACTIONS
# ============================================================

def get_wallet_transactions(wallet):

    return api_get(
        "/v1/wallet/tx_list",
        {
            "wallet": wallet,
            "limit": TX_LIMIT,
            "ui_amount_mode": "scaled",
        }
    )


# ============================================================
# TOKEN OVERVIEW
# ============================================================

def get_token_info(address):

    if not address:
        return None

    # Cache
    if address in token_cache:

        return token_cache[address]

    data = api_get(
        "/defi/token_overview",
        {
            "address": address,
            "frames": "1m,5m,1h,24h",
            "ui_amount_mode": "scaled",
        }
    )

    if not data:

        return None

    info = data.get(
        "data",
        {}
    )

    if not isinstance(info, dict):

        return None

    token_cache[address] = info

    save_json_file(
        TOKEN_CACHE_FILE,
        token_cache
    )

    return info


# ============================================================
# TOKEN ADDRESS EXTRACTION
# ============================================================

def find_token_addresses(obj):

    addresses = []

    def walk(value):

        if isinstance(value, dict):

            for key, item in value.items():

                key_lower = str(key).lower()

                if key_lower in (
                    "address",
                    "token_address",
                    "mint",
                    "token_mint",
                    "token_address"
                ):

                    if isinstance(item, str):

                        if len(item) >= 32:

                            addresses.append(item)

                walk(item)

        elif isinstance(value, list):

            for item in value:

                walk(item)

    walk(obj)

    # remove duplicates
    result = []

    for address in addresses:

        if address not in result:

            result.append(address)

    return result


# ============================================================
# BUY DETECTION
# ============================================================

def text_contains_buy(obj):

    found = False

    def walk(value):

        nonlocal found

        if found:
            return

        if isinstance(value, dict):

            for key, item in value.items():

                key_lower = str(key).lower()

                # Explicit side/type/action
                if key_lower in (
                    "side",
                    "type",
                    "action",
                    "tx_type",
                    "trade_type",
                    "event_type"
                ):

                    text = str(item).lower()

                    if text in (
                        "buy",
                        "bought",
                        "swap_buy"
                    ):

                        found = True
                        return

                walk(item)

        elif isinstance(value, list):

            for item in value:

                walk(item)

        elif isinstance(value, str):

            text = value.lower()

            if text in (
                "buy",
                "bought"
            ):

                found = True

    walk(obj)

    return found


# ============================================================
# TRANSACTION ID
# ============================================================

def get_transaction_id(tx):

    if not isinstance(tx, dict):

        return None

    for key in (
        "txHash",
        "tx_hash",
        "signature",
        "transactionHash",
        "hash"
    ):

        value = tx.get(key)

        if value:

            return str(value)

    return None


# ============================================================
# TRANSACTION TIME
# ============================================================

def get_transaction_time(tx):

    if not isinstance(tx, dict):

        return ""

    for key in (
        "blockTime",
        "block_time",
        "timestamp",
        "time",
        "unixTime"
    ):

        value = tx.get(key)

        if value:

            return str(value)

    return ""


# ============================================================
# SCORE WALLET
# ============================================================

def calculate_wallet_score(profile):

    if not profile:

        return {
            "score": 0,
            "status": "UNKNOWN",
            "win_rate": 0,
            "realized": 0,
            "trades": 0,
        }

    counts = profile.get(
        "counts",
        {}
    )

    pnl = profile.get(
        "pnl",
        {}
    )

    trades = num(
        counts.get("total_trade")
    )

    win_rate = num(
        counts.get("win_rate")
    )

    if win_rate <= 1:

        win_rate *= 100

    realized = num(
        pnl.get(
            "realized_profit_usd"
        )
    )

    score = 0

    # Win rate 30
    if win_rate >= 70:
        score += 30

    elif win_rate >= 60:
        score += 25

    elif win_rate >= 50:
        score += 20

    elif win_rate >= 40:
        score += 12

    else:
        score += 5

    # Realized PnL 30
    if realized >= 50000:
        score += 30

    elif realized >= 25000:
        score += 27

    elif realized >= 10000:
        score += 23

    elif realized > 0:
        score += 15

    # Experience 20
    if trades >= 500:
        score += 20

    elif trades >= 200:
        score += 17

    elif trades >= 100:
        score += 14

    elif trades >= 50:
        score += 10

    else:
        score += 5

    # Positive realized bonus
    if realized > 0:

        score += 10

    # Status
    if score >= 80:

        status = "CORE"

    elif score >= 65:

        status = "WATCH"

    elif score >= 50:

        status = "WEAK"

    else:

        status = "REJECT"

    return {
        "score": min(score, 100),
        "status": status,
        "win_rate": win_rate,
        "realized": realized,
        "trades": trades,
    }


# ============================================================
# BUILD ALERT
# ============================================================

def build_alert(
    wallet_name,
    wallet,
    token_address,
    token_info,
    profile,
    tx
):

    wallet_score = calculate_wallet_score(
        profile
    )

    symbol = safe_text(
        token_info.get("symbol")
        if token_info
        else None
    )

    name = safe_text(
        token_info.get("name")
        if token_info
        else None
    )

    price = num(
        token_info.get("price")
        if token_info
        else 0
    )

    liquidity = num(
        token_info.get("liquidity")
        if token_info
        else 0
    )

    market_cap = num(
        token_info.get("mc")
        if token_info
        else 0
    )

    holder = num(
        token_info.get("holder")
        if token_info
        else 0
    )

    buy_24h = num(
        token_info.get("buy24h")
        if token_info
        else 0
    )

    sell_24h = num(
        token_info.get("sell24h")
        if token_info
        else 0
    )

    change_24h = num(
        token_info.get("priceChange24hPercent")
        if token_info
        else 0
    )

    tx_id = get_transaction_id(
        tx
    )

    signal = "WATCH"

    if wallet_score["score"] >= 80:

        signal = "HIGH QUALITY SMART MONEY"

    elif wallet_score["score"] >= 65:

        signal = "SMART MONEY WATCH"

    message = (
        "🚨 SMART MONEY BUY\n"
        "\n"
        f"🟢 Wallet: {wallet_name}\n"
        f"📊 Score: {wallet_score['score']}/100\n"
        f"🏆 Status: {wallet_score['status']}\n"
        "\n"
        f"🪙 Token: {symbol}\n"
        f"📛 Name: {name}\n"
        f"📍 Mint: {token_address}\n"
        "\n"
        f"💰 Price: {money(price)}\n"
        f"💧 Liquidity: {money(liquidity)}\n"
        f"🏦 Market Cap: {money(market_cap)}\n"
        f"👥 Holders: {int(holder):,}\n"
        "\n"
        f"🟢 24H BUY: {int(buy_24h):,}\n"
        f"🔴 24H SELL: {int(sell_24h):,}\n"
        f"📈 24H Change: {change_24h:.2f}%\n"
        "\n"
        f"📈 Win Rate: {wallet_score['win_rate']:.2f}%\n"
        f"💵 Realized PnL: {money(wallet_score['realized'])}\n"
        f"🔄 Trades: {int(wallet_score['trades']):,}\n"
        "\n"
        f"🔥 SIGNAL: {signal}\n"
    )

    if tx_id:

        message += (
            "\n"
            f"🔗 TX: {shorten(tx_id, 20)}"
        )

    message += (
        "\n\n"
        "⚠️ DYOR — bukan nasihat keuangan."
    )

    return message


# ============================================================
# PROCESS TRANSACTION
# ============================================================

def process_transaction(
    wallet_name,
    wallet,
    tx,
    profile
):

    tx_id = get_transaction_id(
        tx
    )

    if not tx_id:

        return

    # Sudah pernah diproses
    if tx_id in seen_transactions:

        return

    # Tandai terlebih dahulu agar
    # tidak double alert
    seen_transactions.add(
        tx_id
    )

    # Jangan langsung save setiap tx
    # supaya disk tidak terlalu sering ditulis.

    # --------------------------------------------------------
    # BUY DETECTION
    # --------------------------------------------------------

    if not text_contains_buy(tx):

        return

    print()
    print(
        "=========================================="
    )

    print(
        "🔥 BUY DETECTED"
    )

    print(
        f"Wallet : {wallet_name}"
    )

    print(
        f"TX     : {tx_id}"
    )

    # --------------------------------------------------------
    # FIND TOKEN
    # --------------------------------------------------------

    addresses = find_token_addresses(
        tx
    )

    if not addresses:

        print(
            "Token address tidak ditemukan."
        )

        return

    # Ambil kandidat token pertama.
    # Pada swap kompleks bisa ada beberapa address.
    token_address = addresses[0]

    print(
        f"Token  : {token_address}"
    )

    # --------------------------------------------------------
    # TOKEN INFO
    # --------------------------------------------------------

    token_info = get_token_info(
        token_address
    )

    if token_info:

        print(
            f"Symbol : "
            f"{token_info.get('symbol', 'UNKNOWN')}"
        )

    else:

        print(
            "Token overview gagal."
        )

        token_info = {}

    # --------------------------------------------------------
    # BUILD ALERT
    # --------------------------------------------------------

    alert = build_alert(
        wallet_name,
        wallet,
        token_address,
        token_info,
        profile,
        tx
    )

    print()
    print(alert)

    # --------------------------------------------------------
    # TELEGRAM
    # --------------------------------------------------------

    sent = send_telegram(
        alert
    )

    if sent:

        print(
            "✅ Telegram alert sent."
        )

    else:

        print(
            "❌ Telegram alert failed."
        )


# ============================================================
# WELCOME
# ============================================================

def send_start_message():

    message = (
        "🤖 SMART MONEY MONITOR V9\n"
        "\n"
        "Status: ONLINE 🟢\n"
        f"Wallet monitored: {len(WALLETS)}\n"
        f"Poll interval: {POLL_INTERVAL}s\n"
        "\n"
        "Bot sedang memonitor transaksi BUY."
    )

    send_telegram(
        message
    )


# ============================================================
# MAIN MONITOR
# ============================================================

def main():

    print()
    print(
        "=============================================="
    )

    print(
        "       SMART MONEY WALLET MONITOR V9"
    )

    print(
        "=============================================="
    )

    print(
        f"Wallets       : {len(WALLETS)}"
    )

    print(
        f"Poll interval : {POLL_INTERVAL}s"
    )

    print(
        f"TX limit      : {TX_LIMIT}"
    )

    print(
        "=============================================="
    )

    load_cache()

    # --------------------------------------------------------
    # WALLET PROFILES
    # --------------------------------------------------------

    profiles = {}

    print()
    print(
        "Loading wallet profiles..."
    )

    for index, (
        wallet_name,
        wallet
    ) in enumerate(WALLETS):

        print()
        print(
            f"Profile: {wallet_name}"
        )

        profile = get_wallet_profile(
            wallet
        )

        profiles[wallet] = profile

        if profile:

            score = calculate_wallet_score(
                profile
            )

            print(
                f"Score     : "
                f"{score['score']}/100"
            )

            print(
                f"Win Rate  : "
                f"{score['win_rate']:.2f}%"
            )

            print(
                f"Realized  : "
                f"{money(score['realized'])}"
            )

            print(
                f"Trades    : "
                f"{int(score['trades'])}"
            )

            print(
                f"Status    : "
                f"{score['status']}"
            )

        else:

            print(
                "Profile gagal diambil."
            )

        if index < len(WALLETS) - 1:

            time.sleep(
                5
            )

    # --------------------------------------------------------
    # TELEGRAM ONLINE
    # --------------------------------------------------------

    send_start_message()

    # --------------------------------------------------------
    # IMPORTANT:
    # INITIAL SNAPSHOT IS MARKED AS SEEN
    # sehingga bot tidak mengirim semua transaksi lama
    # ketika pertama kali start.
    # --------------------------------------------------------

    print()
    print(
        "Creating initial transaction snapshot..."
    )

    for wallet_name, wallet in WALLETS:

        data = get_wallet_transactions(
            wallet
        )

        if not data:

            continue

        transactions = (
            data
            .get("data", {})
            .get("solana", [])
        )

        if not transactions:

            transactions = (
                data
                .get("data", {})
                .get("items", [])
            )

        if isinstance(
            transactions,
            list
        ):

            for tx in transactions:

                tx_id = get_transaction_id(
                    tx
                )

                if tx_id:

                    seen_transactions.add(
                        tx_id
                    )

        time.sleep(
            3
        )

    save_seen()

    print()
    print(
        f"Initial snapshot: "
        f"{len(seen_transactions)} tx"
    )

    print()
    print(
        "=============================================="
    )

    print(
        "MONITORING ACTIVE 🟢"
    )

    print(
        "=============================================="
    )

    # ========================================================
    # CONTINUOUS MONITOR
    # ========================================================

    cycle = 0

    while True:

        cycle += 1

        print()
        print(
            f"[CYCLE {cycle}] "
            f"Checking wallets..."
        )

        for wallet_name, wallet in WALLETS:

            print()
            print(
                f"Checking "
                f"{wallet_name}"
            )

            data = get_wallet_transactions(
                wallet
            )

            if not data:

                print(
                    "No transaction data."
                )

                continue

            transactions = (
                data
                .get("data", {})
                .get("solana", [])
            )

            if not transactions:

                transactions = (
                    data
                    .get("data", {})
                    .get("items", [])
                )

            if not isinstance(
                transactions,
                list
            ):

                print(
                    "Unexpected transaction format."
                )

                continue

            print(
                f"Transactions: "
                f"{len(transactions)}"
            )

            profile = profiles.get(
                wallet
            )

            # Process newest first
            for tx in reversed(
                transactions
            ):

                process_transaction(
                    wallet_name,
                    wallet,
                    tx,
                    profile
                )

            # small pause
            time.sleep(
                2
            )

        # Save state after cycle
        save_seen()

        print()
        print(
            f"Sleeping "
            f"{POLL_INTERVAL}s..."
        )

        time.sleep(
            POLL_INTERVAL
        )


# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print()
        print(
            "Bot stopped."
        )

        save_seen()

    except Exception as e:

        print()
        print(
            "FATAL ERROR:"
        )

        print(
            repr(e)
        )

        save_seen()

        raise
