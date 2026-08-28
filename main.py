import os
import time
import json
import requests
from collections import deque
from dotenv import load_dotenv

# ============================================================
# SMART MONEY WALLET MONITOR V10
# SOLANA
# BIRDEYE
# TELEGRAM
#
# FOCUS:
# - BUY
# - SELL
# - WALLET MOVEMENT
#
# NO PNL ENDPOINT
# NO ONLINE MESSAGE
# NO STARTUP TELEGRAM MESSAGE
# ============================================================


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

API_KEY = os.getenv("BIRDEYE_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


if not API_KEY:
    raise RuntimeError(
        "BIRDEYE_API_KEY belum diatur"
    )


if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN belum diatur"
    )


if not TELEGRAM_CHAT_ID:
    raise RuntimeError(
        "TELEGRAM_CHAT_ID belum diatur"
    )


# ============================================================
# WALLETS
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


# Jangan mendekati limit 60 RPM.
# Target bot sekitar 10-20 RPM.
POLL_INTERVAL = 30

REQUEST_TIMEOUT = 30

MAX_RETRIES = 4

RETRY_BASE_SECONDS = 10

TX_LIMIT = 20

MAX_SEEN_TRANSACTIONS = 1000

TOKEN_CACHE_FILE = "token_cache.json"

SEEN_FILE = "seen_transactions.json"


# ============================================================
# MEMORY
# ============================================================

seen_transactions = set()

token_cache = {}

# pencatat request untuk proteksi RPM
request_times = deque()


# ============================================================
# BASIC HELPERS
# ============================================================

def num(value):

    try:
        return float(value or 0)

    except (
        TypeError,
        ValueError
    ):

        return 0.0


def safe_text(
    value,
    default="UNKNOWN"
):

    if value is None:
        return default

    value = str(value).strip()

    if not value:
        return default

    return value


def money(value):

    value = num(value)

    return f"${value:,.2f}"


def shorten(
    value,
    length=16
):

    value = safe_text(
        value,
        ""
    )

    if not value:
        return ""

    if len(value) <= length:
        return value

    return (
        value[:length]
        + "..."
    )


# ============================================================
# LOCAL JSON
# ============================================================

def load_json(
    filename,
    default
):

    try:

        if not os.path.exists(
            filename
        ):

            return default

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        print(
            f"LOAD ERROR {filename}: {e}"
        )

        return default


def save_json(
    filename,
    data
):

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
            f"SAVE ERROR {filename}: {e}"
        )


def load_state():

    global seen_transactions
    global token_cache

    seen = load_json(
        SEEN_FILE,
        []
    )

    if isinstance(
        seen,
        list
    ):

        seen_transactions = set(
            seen
        )

    token_cache = load_json(
        TOKEN_CACHE_FILE,
        {}
    )

    print(
        f"Seen TX : "
        f"{len(seen_transactions)}"
    )

    print(
        f"Tokens  : "
        f"{len(token_cache)}"
    )


def save_state():

    global seen_transactions

    if len(
        seen_transactions
    ) > MAX_SEEN_TRANSACTIONS:

        # set tidak memiliki urutan,
        # jadi simpan sebagian terakhir
        seen_transactions = set(
            list(
                seen_transactions
            )[
                -MAX_SEEN_TRANSACTIONS:
            ]
        )

    save_json(
        SEEN_FILE,
        list(
            seen_transactions
        )
    )

    save_json(
        TOKEN_CACHE_FILE,
        token_cache
    )


# ============================================================
# RATE LIMITER
# ============================================================

def wait_for_rate_limit():

    now = time.time()

    # Buang request yang sudah lebih
    # dari 60 detik.
    while request_times:

        if (
            now
            - request_times[0]
            > 60
        ):

            request_times.popleft()

        else:

            break

    # Safety limit internal.
    # Kita sengaja hanya memakai maksimal
    # 45 request dalam 60 detik.
    if len(request_times) >= 45:

        wait = (
            60
            - (
                now
                - request_times[0]
            )
            + 1
        )

        print(
            f"Internal rate protection "
            f"waiting {wait:.1f}s"
        )

        time.sleep(
            max(wait, 1)
        )

    request_times.append(
        time.time()
    )


# ============================================================
# BIRDEYE GET
# ============================================================

def api_get(
    endpoint,
    params=None
):

    for attempt in range(
        MAX_RETRIES
    ):

        wait_for_rate_limit()

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
                        "Invalid JSON response"
                    )

                    return None

            # ------------------------------------------------
            # RATE LIMIT
            # ------------------------------------------------

            if response.status_code == 429:

                retry_after = (
                    response.headers.get(
                        "Retry-After"
                    )
                )

                if retry_after:

                    try:

                        wait = float(
                            retry_after
                        )

                    except ValueError:

                        wait = (
                            RETRY_BASE_SECONDS
                            * (
                                2
                                ** attempt
                            )
                        )

                else:

                    wait = (
                        RETRY_BASE_SECONDS
                        * (
                            2
                            ** attempt
                        )
                    )

                print(
                    f"429 RATE LIMIT | "
                    f"retry {attempt + 1}/"
                    f"{MAX_RETRIES} | "
                    f"wait {wait:.1f}s"
                )

                time.sleep(
                    wait
                )

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
                    f"{response.text[:500]}"
                )

                return None

            # ------------------------------------------------
            # OTHER
            # ------------------------------------------------

            print(
                f"API ERROR "
                f"{response.status_code}: "
                f"{response.text[:500]}"
            )

            return None

        except requests.RequestException as e:

            wait = (
                RETRY_BASE_SECONDS
                * (
                    2
                    ** attempt
                )
            )

            print(
                f"REQUEST ERROR: {e}"
            )

            print(
                f"Retry in {wait}s"
            )

            time.sleep(
                wait
            )

    print(
        "API RETRIES EXHAUSTED"
    )

    return None


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(
    message
):

    url = (
        "https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}"
        "/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": True
    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=20
        )

        if response.status_code != 200:

            print(
                "TELEGRAM ERROR:"
            )

            print(
                response.text[:500]
            )

            return False

        return True

    except requests.RequestException as e:

        print(
            f"TELEGRAM ERROR: {e}"
        )

        return False


# ============================================================
# WALLET TRANSACTION LIST
# ============================================================

def get_transactions(
    wallet
):

    data = api_get(
        "/v1/wallet/tx_list",
        {
            "wallet": wallet,
            "limit": TX_LIMIT
        }
    )

    if not data:

        return []

    data_section = data.get(
        "data",
        {}
    )

    # Beberapa response memakai
    # data.solana
    transactions = (
        data_section.get(
            "solana",
            []
        )
    )

    # Fallback
    if not transactions:

        transactions = (
            data_section.get(
                "items",
                []
            )
        )

    if not isinstance(
        transactions,
        list
    ):

        return []

    return transactions


# ============================================================
# TRANSACTION ID
# ============================================================

def get_tx_id(
    tx
):

    if not isinstance(
        tx,
        dict
    ):

        return None

    for key in (
        "txHash",
        "tx_hash",
        "signature",
        "transactionHash",
        "hash"
    ):

        value = tx.get(
            key
        )

        if value:

            return str(
                value
            )

    return None


# ============================================================
# FIND VALUES RECURSIVELY
# ============================================================

def find_values(
    obj,
    target_keys
):

    found = []

    target_keys = {
        str(x).lower()
        for x in target_keys
    }

    def walk(
        value
    ):

        if isinstance(
            value,
            dict
        ):

            for key, item in value.items():

                key_lower = str(
                    key
                ).lower()

                if key_lower in target_keys:

                    found.append(
                        item
                    )

                walk(
                    item
                )

        elif isinstance(
            value,
            list
        ):

            for item in value:

                walk(
                    item
                )

    walk(
        obj
    )

    return found


# ============================================================
# DETECT SIDE
# ============================================================

def detect_side(
    tx
):

    # --------------------------------------------------------
    # 1. Explicit fields
    # --------------------------------------------------------

    side_values = find_values(
        tx,
        {
            "side",
            "action",
            "trade_type",
            "tx_type",
            "type",
            "event_type"
        }
    )

    for value in side_values:

        text = str(
            value
        ).lower().strip()

        if text in (
            "buy",
            "bought",
            "swap_buy"
        ):

            return "BUY"

        if text in (
            "sell",
            "sold",
            "swap_sell"
        ):

            return "SELL"

    # --------------------------------------------------------
    # 2. Search textual fields
    # --------------------------------------------------------

    text_values = find_values(
        tx,
        {
            "description",
            "name",
            "label",
            "description_text"
        }
    )

    for value in text_values:

        text = str(
            value
        ).lower()

        if "buy" in text:

            return "BUY"

        if "sell" in text:

            return "SELL"

    # --------------------------------------------------------
    # Unknown
    # --------------------------------------------------------

    return "UNKNOWN"


# ============================================================
# TOKEN ADDRESSES
# ============================================================

def find_token_addresses(
    tx
):

    values = find_values(
        tx,
        {
            "token_address",
            "tokenAddress",
            "mint",
            "token_mint",
            "tokenMint",
            "address"
        }
    )

    addresses = []

    for value in values:

        if not isinstance(
            value,
            str
        ):

            continue

        value = value.strip()

        # Solana mint biasanya
        # sekitar 32-44 karakter.
        if (
            32
            <= len(value)
            <= 50
        ):

            if value not in addresses:

                addresses.append(
                    value
                )

    return addresses


# ============================================================
# TOKEN INFO
# ============================================================

def get_token_info(
    address
):

    if not address:

        return None

    if address in token_cache:

        return token_cache[
            address
        ]

    data = api_get(
        "/defi/token_overview",
        {
            "address": address
        }
    )

    if not data:

        return None

    info = data.get(
        "data",
        {}
    )

    if not isinstance(
        info,
        dict
    ):

        return None

    token_cache[
        address
    ] = info

    save_json(
        TOKEN_CACHE_FILE,
        token_cache
    )

    return info


# ============================================================
# FIND BEST TOKEN
# ============================================================

def choose_token(
    tx
):

    addresses = find_token_addresses(
        tx
    )

    if not addresses:

        return None, None

    # Coba satu per satu sampai
    # mendapatkan token overview.
    for address in addresses:

        info = get_token_info(
            address
        )

        if info:

            return (
                address,
                info
            )

    # Jika overview tidak tersedia,
    # tetap kembalikan address pertama.
    return (
        addresses[0],
        {}
    )


# ============================================================
# EXTRACT AMOUNT
# ============================================================

def find_amount(
    tx
):

    values = find_values(
        tx,
        {
            "amount",
            "ui_amount",
            "uiAmount",
            "token_amount",
            "tokenAmount",
            "value"
        }
    )

    for value in values:

        number = num(
            value
        )

        if number > 0:

            return number

    return 0.0


# ============================================================
# BUILD WALLET MOVEMENT
# ============================================================

def build_wallet_message(
    wallet_name,
    wallet,
    tx,
    side,
    token_address,
    token_info
):

    symbol = safe_text(
        token_info.get(
            "symbol"
        )
        if token_info
        else None
    )

    token_name = safe_text(
        token_info.get(
            "name"
        )
        if token_info
        else None
    )

    price = num(
        token_info.get(
            "price"
        )
        if token_info
        else 0
    )

    liquidity = num(
        token_info.get(
            "liquidity"
        )
        if token_info
        else 0
    )

    market_cap = num(
        token_info.get(
            "mc"
        )
        if token_info
        else 0
    )

    holders = num(
        token_info.get(
            "holder"
        )
        if token_info
        else 0
    )

    buy_24h = num(
        token_info.get(
            "buy24h"
        )
        if token_info
        else 0
    )

    sell_24h = num(
        token_info.get(
            "sell24h"
        )
        if token_info
        else 0
    )

    change_24h = num(
        token_info.get(
            "priceChange24hPercent"
        )
        if token_info
        else 0
    )

    tx_id = get_tx_id(
        tx
    )

    amount = find_amount(
        tx
    )

    if side == "BUY":

        title = "🟢 WALLET BUY"

    elif side == "SELL":

        title = "🔴 WALLET SELL"

    else:

        title = "🔵 WALLET MOVEMENT"

    message = (
        f"{title}\n"
        "\n"
        f"👛 Wallet: {wallet_name}\n"
        f"📍 {wallet}\n"
        "\n"
        f"🪙 Token: {symbol}\n"
        f"📛 Name: {token_name}\n"
        f"🔑 Mint: {token_address}\n"
    )

    if amount > 0:

        message += (
            f"\n"
            f"💰 Amount: "
            f"{amount:,.6f}"
        )

    if price > 0:

        message += (
            f"\n"
            f"💵 Price: "
            f"{money(price)}"
        )

    if liquidity > 0:

        message += (
            f"\n"
            f"💧 Liquidity: "
            f"{money(liquidity)}"
        )

    if market_cap > 0:

        message += (
            f"\n"
            f"🏦 Market Cap: "
            f"{money(market_cap)}"
        )

    if holders > 0:

        message += (
            f"\n"
            f"👥 Holders: "
            f"{int(holders):,}"
        )

    message += (
        "\n"
        "\n"
        f"📊 24H BUY: "
        f"{int(buy_24h):,}\n"
        f"📉 24H SELL: "
        f"{int(sell_24h):,}\n"
        f"📈 24H Change: "
        f"{change_24h:.2f}%"
    )

    if tx_id:

        message += (
            "\n\n"
            f"🔗 TX: "
            f"{shorten(tx_id, 24)}"
        )

    message += (
        "\n\n"
        "⚠️ Wallet movement detected."
    )

    return message


# ============================================================
# PROCESS TRANSACTION
# ============================================================

def process_transaction(
    wallet_name,
    wallet,
    tx
):

    tx_id = get_tx_id(
        tx
    )

    if not tx_id:

        return

    # Jangan ulangi
    if tx_id in seen_transactions:

        return

    # --------------------------------------------------------
    # DETECT SIDE
    # --------------------------------------------------------

    side = detect_side(
        tx
    )

    # --------------------------------------------------------
    # TOKEN
    # --------------------------------------------------------

    token_address, token_info = (
        choose_token(
            tx
        )
    )

    # Tandai sudah diproses
    seen_transactions.add(
        tx_id
    )

    # --------------------------------------------------------
    # UNKNOWN MOVEMENT
    # --------------------------------------------------------

    if side == "UNKNOWN":

        print(
            f"Movement detected but "
            f"side unknown: {tx_id}"
        )

        return

    if not token_address:

        print(
            f"{side} detected but "
            f"token tidak ditemukan: "
            f"{tx_id}"
        )

        return

    # --------------------------------------------------------
    # CONSOLE
    # --------------------------------------------------------

    print()
    print(
        "=========================================="
    )

    print(
        f"{side} DETECTED"
    )

    print(
        f"Wallet : {wallet_name}"
    )

    print(
        f"Token  : "
        f"{token_address}"
    )

    print(
        f"TX     : "
        f"{tx_id}"
    )

    # --------------------------------------------------------
    # MESSAGE
    # --------------------------------------------------------

    message = build_wallet_message(
        wallet_name,
        wallet,
        tx,
        side,
        token_address,
        token_info
    )

    # --------------------------------------------------------
    # TELEGRAM
    # --------------------------------------------------------

    sent = send_telegram(
        message
    )

    if sent:

        print(
            "Telegram sent."
        )

    else:

        print(
            "Telegram failed."
        )


# ============================================================
# INITIAL SNAPSHOT
# ============================================================

def create_initial_snapshot():

    print()
    print(
        "Creating initial snapshot..."
    )

    for (
        wallet_name,
        wallet
    ) in WALLETS:

        transactions = get_transactions(
            wallet
        )

        print(
            f"{wallet_name}: "
            f"{len(transactions)} transactions"
        )

        for tx in transactions:

            tx_id = get_tx_id(
                tx
            )

            if tx_id:

                seen_transactions.add(
                    tx_id
                )

        time.sleep(
            3
        )

    save_state()

    print(
        f"Initial snapshot saved: "
        f"{len(seen_transactions)} TX"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print(
        "=============================================="
    )

    print(
        "       SMART MONEY WALLET MONITOR V10"
    )

    print(
        "=============================================="
    )

    print(
        "Mode          : Wallet Movement"
    )

    print(
        "Telegram      : BUY / SELL only"
    )

    print(
        "PnL Endpoint  : DISABLED"
    )

    print(
        "RPM Safety    : 45 / 60"
    )

    print(
        f"Poll Interval : "
        f"{POLL_INTERVAL}s"
    )

    print(
        "=============================================="
    )

    load_state()

    # --------------------------------------------------------
    # INITIAL SNAPSHOT
    # --------------------------------------------------------

    create_initial_snapshot()

    print()
    print(
        "Monitoring started."
    )

    # --------------------------------------------------------
    # LOOP
    # --------------------------------------------------------

    cycle = 0

    while True:

        cycle += 1

        print()
        print(
            f"[CYCLE {cycle}] "
            f"Checking wallets..."
        )

        for (
            wallet_name,
            wallet
        ) in WALLETS:

            print(
                f"Checking "
                f"{wallet_name}"
            )

            transactions = get_transactions(
                wallet
            )

            print(
                f"Transactions: "
                f"{len(transactions)}"
            )

            # ------------------------------------------------
            # Process oldest -> newest
            # ------------------------------------------------

            for tx in reversed(
                transactions
            ):

                process_transaction(
                    wallet_name,
                    wallet,
                    tx
                )

            time.sleep(
                2
            )

        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

        save_state()

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

        print(
            "Bot stopped."
        )

        save_state()

    except Exception as e:

        print(
            "FATAL ERROR:"
        )

        print(
            repr(e)
        )

        save_state()

        raise
