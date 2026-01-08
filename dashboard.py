from flask import Flask, jsonify, render_template
import json
from pathlib import Path

app = Flask(__name__)
STATE = Path("state.json")

def load():
    return json.loads(STATE.read_text()) if STATE.exists() else {}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/state")
def state():
    return jsonify(load())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
