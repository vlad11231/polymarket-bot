import time
import json
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta
from telegram import Bot

# ================= CONFIG =================

API_URL = "https://data-api.polymarket.com/activity"
POLL_INTERVAL = 60

STATE_FILE = Path("state.json")

TELEGRAM_TOKEN = "8408560792:AAEQS7JF-D8ivGj9kpJuAEV1vFVwDDFO7BQ"
TELEGRAM_CHAT_ID = 6854863928

bot = Bot(token=TELEGRAM_TOKEN)

# ============ TRADERI ============

TRADERS = {
    "Euan": {
        "address": "0xdd225a03cd7ed89e3931906c67c75ab31cf89ef1",
        "min_trade": 450
    },
    "Car": {
        "address": "0x7c3db723f1d4d8cb9c550095203b686cb11e5c6b",
        "min_trade": 350
    },
    "JJo": {
        "address": "0xc4086b708cd3a50880b7069add1a1a80000f4675",
        "min_trade": 450
    },
    "Scottilicious": {
        "address": "0x000d257d2dc7616feaef4ae0f14600fdf50a758e",
        "min_trade": 300
    },
    "aenews2": {
        "address": "0x44c1dfe43260c94ed4f1d00de2e1f80fb113ebc1",
        "min_trade": 350
    },
    "Pufu": {
        "address": "0x872ec2644addbbf526744d8e3cb6b0356c0b73d7",
        "min_trade":10
    }
}

# ============ STATE ============

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "last_timestamp": int(datetime.now(tz=timezone.utc).timestamp()),
        "positions": {},
        "clusters": {}
    }

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

state = load_state()

# ============ UTILS ============

def fetch_activity(address):
    r = requests.get(API_URL, params={"user": address, "limit": 50}, timeout=15)
    r.raise_for_status()
    return r.json()

def send(msg):
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)

def score_trade(price, size):
    score = 5
    if price < 0.9:
        score += 2
    if size > 1000:
        score += 2
    if price > 0.97:
        score -= 2
    return max(1, min(10, score))

# ============ MAIN LOOP ============

send("🤖 Bot pornit – monitorizare LIVE (fără alerte vechi)")

while True:
    try:
        for name, cfg in TRADERS.items():
            events = fetch_activity(cfg["address"])

            for e in events:
                ts = e.get("timestamp", 0)
                if ts <= state["last_timestamp"]:
                    continue

                size = float(e.get("size", 0))
                price = float(e.get("price", 0))
                side = e.get("side", "")
                outcome = e.get("outcome", "")
                title = e.get("title", "Unknown")

                value = size * price
                if value < cfg["min_trade"]:
                    continue

                score = score_trade(price, value)

                msg = (
                    f"📌 {name} TRADE {side}\n"
                    f"{title}\n"
                    f"➡️ {outcome}\n"
                    f"💵 ${value:.0f} @ {price}\n"
                    f"⭐ Score: {score}/10\n"
                )

                if name == "Pufu":
                    msg += "👤 Acțiunea TA – verifică dacă e aliniată cu strategia\n"
                elif score >= 7:
                    msg += "✅ Recomandare: merită considerat\n"
                else:
                    msg += "⏸️ Recomandare: așteaptă\n"

                send(msg)

                state["positions"].setdefault(title, []).append({
                    "trader": name,
                    "side": side,
                    "outcome": outcome,
                    "value": value,
                    "price": price,
                    "timestamp": ts
                })

                state["last_timestamp"] = max(state["last_timestamp"], ts)

        save_state(state)

    except Exception as ex:
        send(f"❌ Eroare bot: {ex}")

    time.sleep(POLL_INTERVAL)
