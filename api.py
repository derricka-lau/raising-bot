from flask import Flask, request, jsonify
import json
import os
import sys
import subprocess
import threading
import random

CONFIG_FILE = 'config.json'
MAIN_SCRIPT = 'main.py'
bot_process = None
bot_output = []

# Point to the React build folder
REACT_DIST = os.path.abspath("./raising-bot-web/dist")
app = Flask(__name__, static_folder=REACT_DIST, static_url_path="")

CONFIG_FIELDS = [
    "IBKR_ACCOUNT", "IBKR_PORT", "TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_CHANNEL",
    "IBKR_HOST", "IBKR_CLIENT_ID", "UNDERLYING_SYMBOL", "DEFAULT_ORDER_TYPE", "SNAPMID_OFFSET"
]

CONFIG_DEFAULTS = {
    "IBKR_ACCOUNT": "YOUR_ACCOUNT_NUMBER",
    "IBKR_PORT": "7496",
    "TELEGRAM_API_ID": "",
    "TELEGRAM_API_HASH": "",
    "TELEGRAM_CHANNEL": "",
    "IBKR_HOST": "127.0.0.1",
    "IBKR_CLIENT_ID": "144",
    "UNDERLYING_SYMBOL": "SPX",
    "DEFAULT_ORDER_TYPE": "SNAP MID",
    "SNAPMID_OFFSET": "0.1"
}

def load_config():
    config = CONFIG_DEFAULTS.copy()
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            try:
                config.update(json.load(f))
            except Exception:
                pass
    return config

def save_config(data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@app.route("/api/config", methods=["GET", "POST"])
def config():
    if request.method == "POST":
        save_config(request.json)
        return jsonify({"status": "ok"})
    return jsonify(load_config())

@app.route("/api/start", methods=["POST"])
def start_bot():
    global bot_process, bot_output
    if bot_process is None or bot_process.poll() is not None:
        bot_output = []
        # Generate a random client ID to avoid conflicts
        random_client_id = random.randint(100, 999)
        bot_process = subprocess.Popen(
            [sys.executable, MAIN_SCRIPT, '--client-id', str(random_client_id)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            bufsize=1
        )
        threading.Thread(target=read_bot_output, daemon=True).start()
    return jsonify({"status": "started"})

@app.route("/api/stop", methods=["POST"])
def stop_bot():
    global bot_process
    if bot_process and bot_process.poll() is None:
        bot_process.terminate()
        bot_process = None
    return jsonify({"status": "stopped"})

@app.route("/api/output")
def get_output():
    return jsonify({"output": bot_output})

@app.route("/api/input", methods=["POST"])
def bot_input():
    global bot_process
    if bot_process and bot_process.poll() is None:
        data = request.json.get("input", "")
        if data:
            bot_process.stdin.write((data + "\n").encode("utf-8"))
            bot_process.stdin.flush()
        return jsonify({"status": "ok"})
    return jsonify({"status": "not_running"})

@app.route("/api/status")
def bot_status():
    global bot_process
    running = bot_process is not None and bot_process.poll() is None
    return jsonify({"running": running})

def read_bot_output():
    global bot_process, bot_output
    for line in iter(bot_process.stdout.readline, b''):
        bot_output.append(line.decode('utf-8', errors='ignore').rstrip())
    bot_process = None

# Serve React static files
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return app.send_static_file(path)
    else:
        return app.send_static_file("index.html")

if __name__ == "__main__":
    app.run(debug=True, port=5000)