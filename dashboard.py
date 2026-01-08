from flask import Flask, jsonify, render_template
import json
from pathlib import Path

app = Flask(__name__)
STATE = Path("state.json")
NIGHT = Path("night_log.json")

def load(p):
    return json.loads(p.read_text()) if p.exists() else {}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/state")
def state():
    return jsonify(load(STATE))

@app.route("/api/night")
def night():
    return jsonify(load(NIGHT))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
