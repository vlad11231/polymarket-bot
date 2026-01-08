import time, json, requests
from pathlib import Path
from datetime import datetime
import pytz

# ===== TELEGRAM =====
BOT_TOKEN = "8408560792:AAEQS7JF-D8ivGj9kpJuAEV1vFVwDDFO7BQ"
CHAT_ID = "6854863928"

def tg(msg):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg},
        timeout=20
    )

# ===== CONFIG =====
API = "https://data-api.polymarket.com/activity"
POLL = 60
STATE_FILE = Path("state.json")

SELF = "Pufu"
SELF_ADDR = "0x872ec2644addbbf526744d8e3cb6b0356c0b73d7"

TRADERS = {
    "Euan": "0xdd225a03cd7ed89e3931906c67c75ab31cf89ef1",
    "Car": "0x7c3db723f1d4d8cb9c550095203b686cb11e5c6b",
    "JJo": "0xc4086b708cd3a50880b7069add1a1a80000f4675",
    "Scottilicious": "0x000d257d2dc7616feaef4ae0f14600fdf50a758e",
    "aenews": "0x44c1dfe43260c94ed4f1d00de2e1f80fb113ebc1",
}

MIN_TRADE = 500
MINI, NORMAL, BIG = 2500, 5000, 10000

RO = pytz.timezone("Europe/Bucharest")

# ===== HELPERS =====
def load():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "initialized": False,
        "last": {},
        "positions": {},
        "scores": {},
        "last_update": ""
    }

def save(s):
    STATE_FILE.write_text(json.dumps(s))

def fetch(addr):
    r = requests.get(API, params={"user": addr, "limit": 50}, timeout=20)
    r.raise_for_status()
    return r.json()

def usd(e):
    try: return float(e["size"]) * float(e["price"])
    except: return 0

def price(e):
    try: return float(e["price"])
    except: return 1.0

# ===== SCOR =====
def calc_score(cluster, p):
    score = 0
    if cluster >= BIG: score += 40
    elif cluster >= NORMAL: score += 25
    elif cluster >= MINI: score += 10

    if p < 0.90: score += 20
    elif p < 0.95: score += 10
    else: score -= 10

    return max(0, min(100, score))

# ===== START =====
state = load()
tg("🚀 Bot pornit – SCOR + DEBUG activ")

while True:
    try:
        # INGEST
        for name, addr in {**TRADERS, SELF: SELF_ADDR}.items():
            evs = fetch(addr)

            if not state["initialized"]:
                if evs:
                    state["last"][name] = max(e["timestamp"] for e in evs)
                continue

            last = state["last"].get(name, 0)

            for e in evs:
                if e["timestamp"] <= last:
                    continue

                m = e.get("title", "unknown")
                s = e.get("side", "")
                t = e.get("type")
                v = usd(e)

                key = f"{name}|{m}|{s}"

                if t == "buy":
                    state["positions"][key] = state["positions"].get(key, 0) + v

                    if name != SELF and v >= MIN_TRADE:
                        tg(
                            f"📌 TRADE MARE\n\n"
                            f"{name}\n{m}\n{s}\n${v:.0f}"
                        )

                elif t == "sell":
                    state["positions"][key] = max(
                        state["positions"].get(key, 0) - v, 0
                    )

            if evs:
                state["last"][name] = max(e["timestamp"] for e in evs)

        # CLUSTERE + SCOR
        clusters = {}
        prices = {}

        for k, v in state["positions"].items():
            name, m, s = k.split("|")
            if name == SELF or v <= 0:
                continue
            clusters[f"{m}|{s}"] = clusters.get(f"{m}|{s}", 0) + v

        for key, total in clusters.items():
            m, s = key.split("|")
            p = prices.get(key, 1.0)
            score = calc_score(total, p)
            state["scores"][key] = score

            if total >= MINI:
                tg(
                    f"📊 CLUSTER\n\n"
                    f"{m}\n{s}\n"
                    f"Total: ${total:.0f}\n"
                    f"Scor: {score}/100"
                )

        state["initialized"] = True
        state["last_update"] = datetime.now(RO).isoformat()
        save(state)

    except Exception as e:
        tg(f"❌ Eroare bot: {e}")

    time.sleep(POLL)
