from flask import Flask, request, jsonify
import json
import os
import sys
import subprocess
import threading
import random
import time
from collections import deque

CONFIG_FILE = 'config.json'
MAIN_SCRIPT = 'main.py'
bot_process = None
bot_output = deque(maxlen=2000)
_lock = threading.Lock()

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
    # Atomic write with simple retry
    tmp = CONFIG_FILE + ".tmp"
    last_err = None
    for i in range(3):
        try:
            with open(tmp, 'w') as f:
                json.dump(data, f, indent=4)
            os.replace(tmp, CONFIG_FILE)
            return
        except Exception as e:
            last_err = e
            time.sleep(0.1 * (2 ** i))
    raise last_err

@app.route("/api/config", methods=["GET", "POST"])
def config():
    if request.method == "POST":
        if not request.is_json:
            return jsonify({"error": "application/json required"}), 400
        data = request.get_json(silent=True) or {}
        # validate fields
        invalid = [k for k in data if k not in CONFIG_FIELDS]
        if invalid:
            return jsonify({"error": f"Invalid field(s): {', '.join(invalid)}"}), 400
        try:
            merged = load_config()
            merged.update({k: str(v) for k, v in data.items()})
            save_config(merged)
            return jsonify({"status": "ok"})
        except Exception as e:
            return jsonify({"error": f"Failed to save config: {e}"}), 500
    return jsonify(load_config())

def _start_subprocess_with_retry():
    global bot_process
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    last_err = None
    for i in range(3):
        try:
            bot_process = subprocess.Popen(
                [sys.executable, "-u", MAIN_SCRIPT, "--client-id", str(random.randint(100, 999))],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                bufsize=1,
                text=True,
                encoding="utf-8",
                errors="ignore",
                env=env,
            )
            return True
        except Exception as e:
            last_err = e
            time.sleep(0.3 * (2 ** i))
    bot_process = None
    return False

@app.route("/api/start", methods=["POST"])
def start_bot():
    global bot_process, bot_output
    with _lock:
        if bot_process is None or bot_process.poll() is not None:
            bot_output.clear()
            ok = _start_subprocess_with_retry()
            if not ok:
                return jsonify({"status": "failed"}), 500
            threading.Thread(target=read_bot_output, daemon=True).start()
    return jsonify({"status": "started"})

@app.route("/api/stop", methods=["POST"])
def stop_bot():
    global bot_process, bot_output
    with _lock:
        if bot_process and bot_process.poll() is None:
            try:
                bot_process.terminate()
                try:
                    bot_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    bot_process.kill()
                finally:
                    if bot_process.stdout: bot_process.stdout.close()
                    if bot_process.stdin: bot_process.stdin.close()
            finally:
                bot_process = None
        # Clear output when stopped
        bot_output.clear()
    return jsonify({"status": "stopped"})

@app.route("/api/output")
def get_output():
    with _lock:
        return jsonify({"output": list(bot_output)})

@app.route("/api/input", methods=["POST"])
def bot_input():
    global bot_process
    if not request.is_json:
        return jsonify({"error": "application/json required"}), 400
    data = (request.get_json(silent=True) or {}).get("input", "")
    if not isinstance(data, str) or not data.strip():
        return jsonify({"error": "Input cannot be empty"}), 400
    with _lock:
        if bot_process and bot_process.poll() is None:
            try:
                bot_process.stdin.write(data + "\n")
                bot_process.stdin.flush()
                return jsonify({"status": "ok"})
            except Exception as e:
                return jsonify({"error": f"Failed to send input: {e}"}), 500
    return jsonify({"status": "not_running"})

def read_bot_output():
    global bot_process, bot_output
    try:
        assert bot_process and bot_process.stdout
        for line in iter(bot_process.stdout.readline, ""):
            with _lock:
                bot_output.append(line.rstrip())
    except Exception:
        pass
    finally:
        with _lock:
            bot_process = None

@app.route("/api/status")
def bot_status():
    with _lock:
        running = bot_process is not None and bot_process.poll() is None
    return jsonify({"running": running})

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