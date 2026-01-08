import time, json, requests
from pathlib import Path
from datetime import datetime
import pytz

TELEGRAM_BOT_TOKEN = "8408560792:AAEQS7JF-D8ivGj9kpJuAEV1vFVwDDFO7BQ"
TELEGRAM_CHAT_ID = "6854863928"

def tg(msg):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
        timeout=15
    )

API_URL = "https://data-api.polymarket.com/activity"
POLL = 60

STATE = Path("state.json")
NIGHT = Path("night_log.json")

SELF = "Pufu"
SELF_ADDR = "0x872ec2644addbbf526744d8e3cb6b0356c0b73d7"

TRADERS = {
    "Euan": "0xdd225a03cd7ed89e3931906c67c75ab31cf89ef1",
    "Car": "0x7c3db723f1d4d8cb9c550095203b686cb11e5c6b",
    "JJo": "0xc4086b708cd3a50880b7069add1a1a80000f4675",
    "Scottilicious": "0x000d257d2dc7616feaef4ae0f14600fdf50a758e",
    "aenews": "0x44c1dfe43260c94ed4f1d00de2e1f80fb113ebc1",
}

CAPITAL = 1780
MINI = 2500
NORMAL = 5000
BIG = 10000

RO = pytz.timezone("Europe/Bucharest")

def load(p, d):
    return json.loads(p.read_text()) if p.exists() else d

def save(p, d):
    p.write_text(json.dumps(d))

def fetch(addr):
    r = requests.get(API_URL, params={"user": addr, "limit": 50}, timeout=15)
    r.raise_for_status()
    return r.json()

def usd(e):
    try:
        return float(e["size"]) * float(e["price"])
    except:
        return 0

def night_time():
    h = datetime.now(RO).hour
    return h >= 22 or h < 7

state = load(STATE, {"last": {}})
night_log = load(NIGHT, [])

tg("🚀 Bot pornit – monitorizare activă")

while True:
    try:
        all_pos = {}

        for name, addr in {**TRADERS, SELF: SELF_ADDR}.items():
            ev = fetch(addr)
            last = state["last"].get(name, 0)

            for e in ev:
                if e["timestamp"] <= last:
                    continue

                market = e.get("title", "unknown")
                side = e.get("side", "")
                key = f"{market}|{side}"
                all_pos[key] = all_pos.get(key, 0) + usd(e)

                if name != SELF:
                    msg = f"📌 {name} {e.get('type','').upper()} {side}\n{market}"
                    tg(msg)
                    if night_time():
                        night_log.append(msg)

            if ev:
                state["last"][name] = max(x["timestamp"] for x in ev)

        for mk, total in all_pos.items():
            if total >= BIG:
                msg = f"🔴 BIG CLUSTER\n{mk}\nTOTAL ${total:.0f}\n➡️ ALL-IN"
            elif total >= NORMAL:
                msg = f"🟠 CLUSTER\n{mk}\nTOTAL ${total:.0f}\n➡️ INTRĂ"
            elif total >= MINI:
                msg = f"🟡 MINI CLUSTER\n{mk}\nTOTAL ${total:.0f}\n➡️ WATCH"
            else:
                continue

            tg(msg)
            if night_time():
                night_log.append(msg)

        now = datetime.now(RO)
        if now.hour == 7 and now.minute < 2 and night_log:
            tg("🌙 NIGHT SUMMARY\n\n" + "\n\n".join(night_log))
            night_log.clear()

        save(STATE, state)
        save(NIGHT, night_log)

    except Exception as e:
        tg(f"❌ Eroare: {e}")

    time.sleep(POLL)
