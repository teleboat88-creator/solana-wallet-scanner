import os
import time
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIG
# ============================================================

RPC_URL = os.getenv(
    "SOLANA_RPC_URL",
    "https://api.mainnet-beta.solana.com"
)

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN"
)

TELEGRAM_CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID"
)

POLL_INTERVAL = int(
    os.getenv("POLL_INTERVAL", "15")
)

SIGNATURE_LIMIT = 10

STATE_FILE = "wallet_state.json"

# ============================================================
# 3 WALLET YANG DIPANTAU
# ============================================================

WALLETS = {
    "CORE_CANDIDATE":
        "9xn3JjPreFAaAEBZL3VVvcou33jrfRWhsuiNbD4sJcEe",

    "CONTROL":
        "F6Fh9BjBXb1GyacHto4cwqcKF4K4xK8SwEyDv9Ayp8j9",

    "WALLET_3":
        "5d8tDay1ZDV4XVUBtTvFvQiLxDe8dz2ZCdsrkmTDcbm5",
}

# ============================================================
# SOLANA RPC
# ============================================================

session = requests.Session()

session.headers.update({
    "Content-Type": "application/json"
})


def rpc_call(method, params):

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params
    }

    try:

        r = session.post(
            RPC_URL,
            json=payload,
            timeout=30
        )

        if r.status_code != 200:

            print(
                f"RPC HTTP ERROR {r.status_code}: "
                f"{r.text[:300]}"
            )

            return None

        data = r.json()

        if "error" in data:

            print(
                "RPC ERROR:",
                data["error"]
            )

            return None

        return data.get("result")

    except Exception as e:

        print(
            "RPC REQUEST ERROR:",
            e
        )

        return None


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN belum diatur")
        return False

    if not TELEGRAM_CHAT_ID:
        print("TELEGRAM_CHAT_ID belum diatur")
        return False

    url = (
        "https://api.telegram.org/bot"
        + TELEGRAM_BOT_TOKEN
        + "/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": True
    }

    try:

        r = session.post(
            url,
            json=payload,
            timeout=20
        )

        if r.status_code != 200:

            print(
                "TELEGRAM ERROR:",
                r.text[:300]
            )

            return False

        return True

    except Exception as e:

        print(
            "TELEGRAM REQUEST ERROR:",
            e
        )

        return False


# ============================================================
# STATE
# ============================================================

def load_state():

    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return {}


def save_state(state):

    try:

        with open(
            STATE_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                state,
                f,
                indent=2
            )

    except Exception as e:

        print(
            "STATE SAVE ERROR:",
            e
        )


# ============================================================
# GET LATEST SIGNATURES
# ============================================================

def get_signatures(wallet):

    result = rpc_call(
        "getSignaturesForAddress",
        [
            wallet,
            {
                "limit": SIGNATURE_LIMIT,
                "commitment": "confirmed"
            }
        ]
    )

    if not result:
        return []

    return result


# ============================================================
# GET TRANSACTION
# ============================================================

def get_transaction(signature):

    return rpc_call(
        "getTransaction",
        [
            signature,
            {
                "encoding": "jsonParsed",
                "commitment": "confirmed",
                "maxSupportedTransactionVersion": 0
            }
        ]
    )


# ============================================================
# HELPERS
# ============================================================

def lamports_to_sol(value):

    try:
        return float(value) / 1_000_000_000

    except Exception:

        return 0.0


def get_account_keys(tx):

    try:

        return (
            tx["transaction"]
            ["message"]
            ["accountKeys"]
        )

    except Exception:

        return []


def get_wallet_balance_change(
    tx,
    wallet
):

    try:

        meta = tx.get(
            "meta"
        )

        if not meta:
            return 0.0

        keys = get_account_keys(
            tx
        )

        wallet_index = None

        for i, item in enumerate(keys):

            if isinstance(
                item,
                dict
            ):

                pubkey = item.get(
                    "pubkey"
                )

            else:

                pubkey = item

            if pubkey == wallet:

                wallet_index = i
                break

        if wallet_index is None:
            return 0.0

        pre = meta.get(
            "preBalances",
            []
        )

        post = meta.get(
            "postBalances",
            []
        )

        if (
            wallet_index >= len(pre)
            or wallet_index >= len(post)
        ):
            return 0.0

        change = (
            post[wallet_index]
            - pre[wallet_index]
        )

        return lamports_to_sol(
            change
        )

    except Exception:

        return 0.0


# ============================================================
# TOKEN BALANCE CHANGES
# ============================================================

def token_changes(
    tx,
    wallet
):

    changes = []

    try:

        meta = tx.get(
            "meta"
        )

        if not meta:
            return changes

        pre = meta.get(
            "preTokenBalances",
            []
        )

        post = meta.get(
            "postTokenBalances",
            []
        )

        # ----------------------------------------------------
        # PRE
        # ----------------------------------------------------

        before = {}

        for item in pre:

            owner = item.get(
                "owner"
            )

            if owner != wallet:
                continue

            mint = item.get(
                "mint"
            )

            amount = (
                item.get(
                    "uiTokenAmount",
                    {}
                )
                .get(
                    "uiAmount",
                    0
                )
            )

            before[mint] = (
                before.get(
                    mint,
                    0
                )
                + float(amount or 0)
            )

        # ----------------------------------------------------
        # POST
        # ----------------------------------------------------

        after = {}

        for item in post:

            owner = item.get(
                "owner"
            )

            if owner != wallet:
                continue

            mint = item.get(
                "mint"
            )

            amount = (
                item.get(
                    "uiTokenAmount",
                    {}
                )
                .get(
                    "uiAmount",
                    0
                )
            )

            after[mint] = (
                after.get(
                    mint,
                    0
                )
                + float(amount or 0)
            )

        # ----------------------------------------------------
        # COMPARE
        # ----------------------------------------------------

        all_mints = (
            set(before)
            | set(after)
        )

        for mint in all_mints:

            old = before.get(
                mint,
                0
            )

            new = after.get(
                mint,
                0
            )

            change = new - old

            if abs(change) < 0.00000001:
                continue

            changes.append({
                "mint": mint,
                "change": change,
                "before": old,
                "after": new
            })

    except Exception as e:

        print(
            "TOKEN PARSE ERROR:",
            e
        )

    return changes


# ============================================================
# DETECT BUY / SELL
# ============================================================

def analyze_transaction(
    tx,
    wallet
):

    if not tx:
        return None

    if tx.get(
        "meta",
        {}
    ).get("err") is not None:

        return None

    tokens = token_changes(
        tx,
        wallet
    )

    if not tokens:
        return None

    sol_change = get_wallet_balance_change(
        tx,
        wallet
    )

    received = [
        x for x in tokens
        if x["change"] > 0
    ]

    sent = [
        x for x in tokens
        if x["change"] < 0
    ]

    # --------------------------------------------------------
    # BUY
    #
    # Wallet kehilangan SOL
    # dan mendapatkan token.
    # --------------------------------------------------------

    if (
        sol_change < -0.00001
        and received
    ):

        token = max(
            received,
            key=lambda x: x["change"]
        )

        return {
            "side": "BUY",
            "mint": token["mint"],
            "amount": token["change"],
            "sol_change": sol_change
        }

    # --------------------------------------------------------
    # SELL
    #
    # Wallet mendapatkan SOL
    # dan kehilangan token.
    # --------------------------------------------------------

    if (
        sol_change > 0.00001
        and sent
    ):

        token = max(
            sent,
            key=lambda x: abs(x["change"])
        )

        return {
            "side": "SELL",
            "mint": token["mint"],
            "amount": abs(token["change"]),
            "sol_change": sol_change
        }

    return None


# ============================================================
# TELEGRAM MESSAGE
# ============================================================

def build_message(
    wallet_name,
    wallet,
    signature,
    analysis
):

    side = analysis["side"]

    if side == "BUY":

        emoji = "🟢"
        title = "WALLET BUY"

    else:

        emoji = "🔴"
        title = "WALLET SELL"

    mint = analysis["mint"]

    amount = analysis["amount"]

    sol_change = analysis[
        "sol_change"
    ]

    message = (
        f"{emoji} {title}\n"
        "\n"
        f"👛 Wallet: {wallet_name}\n"
        f"📍 {wallet}\n"
        "\n"
        f"🪙 Token Mint:\n"
        f"{mint}\n"
        "\n"
        f"🔢 Token Amount: "
        f"{amount:,.8f}\n"
        f"◎ SOL Change: "
        f"{sol_change:+.6f} SOL\n"
        "\n"
        f"🔗 Transaction:\n"
        f"https://solscan.io/tx/{signature}"
    )

    return message


# ============================================================
# INITIALIZE
# ============================================================

def initialize_state():

    state = load_state()

    changed = False

    for name, wallet in WALLETS.items():

        signatures = get_signatures(
            wallet
        )

        if not signatures:
            continue

        latest = signatures[0][
            "signature"
        ]

        if name not in state:

            state[name] = latest

            changed = True

            print(
                f"{name}: initial snapshot saved"
            )

    if changed:

        save_state(
            state
        )

    return state


# ============================================================
# CHECK WALLET
# ============================================================

def check_wallet(
    name,
    wallet,
    state
):

    signatures = get_signatures(
        wallet
    )

    if not signatures:
        return

    last_signature = state.get(
        name
    )

    new_transactions = []

    for item in signatures:

        signature = item.get(
            "signature"
        )

        if not signature:
            continue

        if signature == last_signature:
            break

        new_transactions.append(
            signature
        )

    # Tidak ada transaksi baru
    if not new_transactions:
        return

    # --------------------------------------------------------
    # Process oldest -> newest
    # --------------------------------------------------------

    for signature in reversed(
        new_transactions
    ):

        print(
            f"{name} new TX: "
            f"{signature[:20]}..."
        )

        tx = get_transaction(
            signature
        )

        if not tx:
            continue

        analysis = analyze_transaction(
            tx,
            wallet
        )

        if not analysis:
            continue

        message = build_message(
            name,
            wallet,
            signature,
            analysis
        )

        print(
            f"{analysis['side']} detected: "
            f"{analysis['mint']}"
        )

        send_telegram(
            message
        )

        # Sedikit jeda supaya
        # tidak spam Telegram
        time.sleep(1)

    # Simpan transaksi terbaru
    state[name] = signatures[0][
        "signature"
    ]

    save_state(
        state
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "SMART MONEY WALLET MONITOR"
    )

    print(
        "Wallets:",
        len(WALLETS)
    )

    print(
        "RPC:",
        RPC_URL
    )

    # --------------------------------------------------------
    # INITIAL SNAPSHOT
    #
    # Transaksi lama TIDAK dikirim Telegram.
    # --------------------------------------------------------

    state = initialize_state()

    print(
        "Monitoring started."
    )

    # --------------------------------------------------------
    # LOOP
    # --------------------------------------------------------

    while True:

        for name, wallet in WALLETS.items():

            try:

                check_wallet(
                    name,
                    wallet,
                    state
                )

            except Exception as e:

                print(
                    f"{name} ERROR:",
                    repr(e)
                )

            # Jeda antar-wallet
            time.sleep(1)

        time.sleep(
            POLL_INTERVAL
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
