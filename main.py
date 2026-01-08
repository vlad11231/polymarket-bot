import time, json, requests
from pathlib import Path
from datetime import datetime, timedelta
import pytz

# ================= TELEGRAM =================
BOT_TOKEN = "8408560792:AAEQS7JF-D8ivGj9kpJuAEV1vFVwDDFO7BQ"
CHAT_ID = "6854863928"

def tg(msg):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg},
        timeout=20
    )

# ================= CONFIG =================
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

CAPITAL = 1780
MIN_TRADE = 500

MINI, NORMAL, BIG = 2500, 5000, 10000
MAX_MARKET_EXPOSURE = 0.35
MAX_POSITIONS = 3

RO = pytz.timezone("Europe/Bucharest")

# ================= HELPERS =================
def load():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "initialized": False,
        "last": {},
        "positions": {},     # name|market|side -> usd
        "cumulative": {},    # trader|market|side -> usd
        "events": {},        # trader|market|side -> [timestamps]
        "last_alert": {},    # market|side -> score
        "priority": {},      # market|side -> score
        "journal": [],       # decizii zilnice
        "pnl": {}            # market|side -> est pnl proxy
    }

def save(s): STATE_FILE.write_text(json.dumps(s))
def fetch(addr):
    r = requests.get(API, params={"user": addr, "limit": 50}, timeout=20)
    r.raise_for_status(); return r.json()
def usd(e):
    try: return float(e["size"]) * float(e["price"])
    except: return 0
def price(e):
    try: return float(e["price"])
    except: return 1.0
def now(): return datetime.now(RO)

# ================= SCORING =================
def score_opportunity(cluster, cum, p, scalping):
    s = 0
    s += 40 if cluster>=BIG else 25 if cluster>=NORMAL else 10 if cluster>=MINI else 0
    s += 20 if cum>=5000 else 10 if cum>=2500 else 0
    s += 20 if p<0.90 else 10 if p<0.95 else -10
    if scalping: s -= 20
    return max(0, min(100, s))

def classify(score):
    return "STRONG" if score>=75 else "GOOD" if score>=55 else "WEAK" if score>=35 else "IGNORE"

# ================= START =================
state = load()
tg("🚀 Bot pornit – PROP DESK+++ activ")

while True:
    try:
        clusters, prices, scalping = {}, {}, {}

        # ===== INGEST =====
        for name, addr in {**TRADERS, SELF: SELF_ADDR}.items():
            evs = fetch(addr)
            if not state["initialized"]:
                if evs: state["last"][name] = max(e["timestamp"] for e in evs)
                continue

            last = state["last"].get(name, 0)
            for e in evs:
                if e["timestamp"] <= last: continue
                m, s, t = e.get("title","unknown"), e.get("side",""), e.get("type")
                v, p = usd(e), price(e)
                posk = f"{name}|{m}|{s}"
                evk  = f"{name}|{m}|{s}"
                state["events"].setdefault(evk, []).append(now().isoformat())
                state["events"][evk] = state["events"][evk][-10:]

                if t=="buy":
                    state["positions"][posk] = state["positions"].get(posk,0)+v
                    if name!=SELF and v>=MIN_TRADE:
                        ck = f"{name}|{m}|{s}"
                        state["cumulative"][ck] = state["cumulative"].get(ck,0)+v
                        clusters[f"{m}|{s}"] = clusters.get(f"{m}|{s}",0)+v
                        prices[f"{m}|{s}"] = p
                elif t=="sell":
                    state["positions"][posk] = max(state["positions"].get(posk,0)-v,0)
                    if name==SELF:
                        # confirmare acțiune TA
                        score = state["last_alert"].get(f"{m}|{s}",0)
                        eval_ = "FOARTE BUNĂ ✅" if score>=75 else "OK" if score>=55 else "SLABĂ ⚠️"
                        tg(f"🧾 ACȚIUNE CONFIRMATĂ\n\nAi SELL pe {m} ({s})\nScor oportunitate: {score}/100\n➡️ Evaluare: {eval_}")
                        state["journal"].append({"time": now().isoformat(),"act":"SELL","market":m,"side":s,"score":score})

                if name==SELF and t=="buy":
                    score = state["last_alert"].get(f"{m}|{s}",0)
                    eval_ = "FOARTE BUNĂ ✅" if score>=75 else "OK" if score>=55 else "SLABĂ ⚠️"
                    tg(f"🧾 ACȚIUNE CONFIRMATĂ\n\nAi BUY pe {m} ({s})\nScor oportunitate: {score}/100\n➡️ Evaluare: {eval_}")
                    state["journal"].append({"time": now().isoformat(),"act":"BUY","market":m,"side":s,"score":score})

            if evs: state["last"][name] = max(e["timestamp"] for e in evs)

        # ===== SCALPING =====
        for k,ts in state["events"].items():
            if len(ts)>=4:
                t0,tN = datetime.fromisoformat(ts[0]), datetime.fromisoformat(ts[-1])
                if (tN-t0)<timedelta(minutes=30):
                    _,m,s = k.split("|")
                    scalping[f"{m}|{s}"]=True

        # ===== DECISIONS + EXIT ENGINE =====
        scores = {}
        for key,total in clusters.items():
            m,s = key.split("|"); p = prices.get(key,1.0)
            cum = max((v for ck,v in state["cumulative"].items() if ck.endswith(f"|{m}|{s}")), default=0)
            sc = score_opportunity(total,cum,p,scalping.get(key,False))
            prev = state["last_alert"].get(key,-1)
            if sc<=prev: continue
            state["last_alert"][key]=sc
            scores[key]=sc

            your = sum(v for k,v in state["positions"].items() if k.startswith(f"{SELF}|{m}|{s}"))
            max_allowed = CAPITAL*MAX_MARKET_EXPOSURE
            label = classify(sc)

            if label=="STRONG":
                rec,sz = "INTRĂ AGRESIV / MENȚINE", f"până la ${max_allowed-your:.0f}"
            elif label=="GOOD":
                rec,sz = "INTRĂ PARȚIAL", "300–600$"
            elif label=="WEAK":
                rec,sz = "AȘTEAPTĂ", "NU modifica"
            else:
                continue

            tg(f"📊 OPORTUNITATE {label}\n\nPiață: {m}\nDirecție: {s}\nCluster: ${total:.0f}\nConvingere: ${cum:.0f}\nPreț: {p:.2f}\nScor: {sc}/100\n\nPoziția ta: ${your:.0f}\n➡️ Recomandare: {rec}\n➡️ Sugerare: {sz}")

            # EXIT ENGINE
            if your>0 and (sc<40 or scalping.get(key,False)):
                tg(f"⚠️ EXIT ENGINE\n\n{m} ({s})\nScor scăzut / scalping\n➡️ Recomandare: REDU / IEȘI")

        # ===== PRIORITY LIST =====
        top = sorted(scores.items(), key=lambda x:x[1], reverse=True)[:3]
        if top:
            msg = "🧭 TOP 3 OPORTUNITĂȚI\n\n" + "\n".join([f"{k} – {v}/100" for k,v in top])
            tg(msg)

        # ===== DAILY SUMMARY (07:00 RO) =====
        if now().hour==7 and now().minute<2 and state["journal"]:
            good = sum(1 for j in state["journal"] if j["score"]>=55)
            bad  = len(state["journal"])-good
            tg(f"📘 DAILY REVIEW\n\nDecizii bune: {good}\nDecizii slabe: {bad}\n➡️ Continuă disciplina")
            state["journal"].clear()

        state["initialized"]=True
        save(state)

    except Exception as e:
        tg(f"❌ Eroare bot: {e}")

    time.sleep(POLL)
