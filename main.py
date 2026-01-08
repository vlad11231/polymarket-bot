import time
import json
import threading
import requests
from pathlib import Path
from flask import Flask, jsonify

# ================= CONFIG =================

POLL_INTERVAL = 60
STATE_FILE = Path("state.json")

API_URL = "https://data-api.polymarket.com/activity"

TRADERS = {
    "Euan": "0xdd225a03cd7ed89e3931906c67c75ab31cf89ef1",
    "Car": "0x7c3db723f1d4d8cb9c550095203b686cb11e5c6b",
    "JJo": "0xc4086b708cd3a50880b7069add1a1a80000f4675",
    "scottilicious": "0x000d257d2dc7616feaef4ae0f14600fdf50a758e",
    "aenews2": "0x44c1dfe43260c94ed4f1d00de2e1f80fb113ebc1",
    "Pufu": "0x872ec2644addbbf526744d8e3cb6b0356c0b73d7"
}

state = {
    "last_update": None,
    "events": [],
    "positions": {},
}

# ================= BOT =================

def fetch_activity(address):
    r = requests.get(API_URL, params={"user": address, "limit": 20}, timeout=10)
    r.raise_for_status()
    return r.json()

def bot_loop():
    while True:
        try:
            for name, addr in TRADERS.items():
                events = fetch_activity(addr)
                for e in events:
                    e["trader"] = name
                state["events"] = events[:50]

            state["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
            STATE_FILE.write_text(json.dumps(state, indent=2))

        except Exception as e:
            print("Bot error:", e)

        time.sleep(POLL_INTERVAL)

# ================= DASHBOARD =================

app = Flask(__name__)

@app.route("/")
def index():
    return jsonify(state)

# ================= START =================

if __name__ == "__main__":
    t = threading.Thread(target=bot_loop, daemon=True)
    t.start()

    app.run(host="0.0.0.0", port=8080)
