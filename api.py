import os
import sys
import webbrowser
import threading
import print_utils
from collections import deque
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import json
import subprocess
import random
import time
from pathlib import Path
import argparse
import re
from config import get_user_data_dir

# --- INITIALIZE GLOBAL VARIABLES HERE ---
_lock = threading.Lock()
bot_process = None
bot_output = deque(maxlen=5000)
# --- END INITIALIZATION ---

# --- HELPER FUNCTIONS (resource_path is unchanged) ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
# --- END HELPER FUNCTIONS ---


# --- UPDATE ALL FILE PATHS ---
USER_DATA_DIR = get_user_data_dir()
# User-specific config is now in a writable location
CONFIG_FILE = os.path.join(USER_DATA_DIR, 'config.json')
# The default config is still bundled with the app
DEFAULT_CONFIG_FILE = resource_path('config.json')
# Session files also go in the user data directory
SESSION_FILES = [os.path.join(USER_DATA_DIR, "session_name.session"), os.path.join(USER_DATA_DIR, "session_name.session-journal")]
# Log file also goes in the user data directory
LOG_FILE = os.path.join(USER_DATA_DIR, "bot_console.log")

MAIN_SCRIPT = resource_path('main.py')
REACT_DIST = resource_path("raising-bot-web/dist")
# --- END PATH UPDATES ---

# --- UPDATE FLASK APP DEFINITION ---
app = Flask(__name__, static_folder=REACT_DIST, static_url_path="")
socketio = SocketIO(app, cors_allowed_origins="*")

CONFIG_FIELDS = [
    "IBKR_ACCOUNT", "IBKR_PORT", "TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_CHANNEL",
    "IBKR_HOST", "IBKR_CLIENT_ID", "UNDERLYING_SYMBOL", "DEFAULT_ORDER_TYPE", "SNAPMID_OFFSET",
    "DEFAULT_LIMIT_PRICE", "DEFAULT_STOP_PRICE", "WAIT_AFTER_OPEN_SECONDS",
    "LMT_PRICE_FOR_SPREAD_30", "LMT_PRICE_FOR_SPREAD_35", "PEG_MID_PRICE_CAP"
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
    "SNAPMID_OFFSET": "0.1",
    "WAIT_AFTER_OPEN_SECONDS": "3",
    "LMT_PRICE_FOR_SPREAD_30": "",
    "LMT_PRICE_FOR_SPREAD_35": "",
}

VALID_ORDER_TYPES = [
    "SNAP MID", "SNAP MKT", "LMT", "MKT", "STP", "STP LMT", "REL", "TRAIL", "TRAIL LIMIT", "PEG MID"
]

# --- UPDATE CONFIG LOADING LOGIC ---
def load_config():
    # If user config doesn't exist, create it from the default bundled with the app
    if not os.path.exists(CONFIG_FILE) and os.path.exists(DEFAULT_CONFIG_FILE):
        import shutil
        shutil.copy(DEFAULT_CONFIG_FILE, CONFIG_FILE)

    config = CONFIG_DEFAULTS.copy()
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            try:
                config.update(json.load(f))
            except Exception:
                pass # If file is corrupt, we'll use defaults
    return config

# `save_config` is now fine because CONFIG_FILE points to a writable location.

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

def _start_subprocess_with_retry():
    global bot_process
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    last_err = None

    # Create the correct command based on whether the app is packaged or not.
    if getattr(sys, 'frozen', False):
        # In a packaged app, sys.executable is the app itself.
        command = [sys.executable, "--run-main", "--client-id", str(random.randint(100, 999))]
    else:
        # In development, we must explicitly call the script (api.py).
        # sys.argv[0] is the path to the current script (api.py).
        command = [sys.executable, sys.argv[0], "--run-main", "--client-id", str(random.randint(100, 999))]

    for i in range(3):
        try:
            bot_process = subprocess.Popen(
                command,
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

def read_bot_output():
    global bot_process, bot_output
    try:
        assert bot_process and bot_process.stdout
        for line in iter(bot_process.stdout.readline, ""):
            raw = line.rstrip()
            stripped = re.sub(r'^\[TS:[^\]]+\]\s*', '', raw)
            UPDATABLE_PREFIXES = ("Waiting for market open:", "Live SPX Price:")

            def is_updatable_line(line):
                stripped = re.sub(r'^\[TS:[^\]]+\]\s*', '', line)
                return any(stripped.startswith(prefix) for prefix in UPDATABLE_PREFIXES)

            is_updatable = any(stripped.startswith(prefix) for prefix in UPDATABLE_PREFIXES)

            with _lock:
                if is_updatable:
                    if bot_output and is_updatable_line(bot_output[-1]):
                        bot_output[-1] = raw
                    else:
                        bot_output.append(raw)
                else:
                    bot_output.append(raw)
            # Emit the new line to all connected clients
            socketio.emit("output", {"line": raw})

            if not is_updatable:
                try:
                    with open(LOG_FILE, "a") as f:
                        f.write(raw + "\n")
                except Exception:
                    pass
    except Exception:
        pass
    finally:
        with _lock:
            bot_process = None

@app.route("/api/config", methods=["GET", "POST"])
def config():
    if request.method == "POST":
        if not request.is_json:
            return jsonify({"error": "application/json required"}), 400
        data = request.get_json(silent=True) or {}
        invalid = [k for k in data if k not in CONFIG_FIELDS]
        if invalid:
            return jsonify({"error": f"Invalid field(s): {', '.join(invalid)}"}), 400

        # --- Start of Corrected Validation Logic ---

        # Validate required fields
        required_fields = [
            "IBKR_ACCOUNT", "IBKR_PORT", "IBKR_HOST", "IBKR_CLIENT_ID", "UNDERLYING_SYMBOL", "DEFAULT_ORDER_TYPE", "SNAPMID_OFFSET"
        ]
        missing = [k for k in required_fields if not str(data.get(k, "")).strip()]
        if missing:
            return jsonify({"error": f"Missing required field(s): {', '.join(missing)}"}), 400

        # Validate order type
        order_type = data.get("DEFAULT_ORDER_TYPE", "").strip().upper()
        if order_type and order_type not in VALID_ORDER_TYPES:
            return jsonify({"error": f"Invalid DEFAULT_ORDER_TYPE: {order_type}. Allowed: {', '.join(VALID_ORDER_TYPES)}"}), 400

        # Conditional validation based on order type
        if order_type == "STP" and not str(data.get("DEFAULT_STOP_PRICE", "")).strip():
            return jsonify({"error": "Stop price required for STP order type"}), 400
        
        if order_type == "STP LMT":
            if not str(data.get("DEFAULT_LIMIT_PRICE", "")).strip() or not str(data.get("DEFAULT_STOP_PRICE", "")).strip():
                return jsonify({"error": "Both limit and stop price required for STP LMT order type"}), 400
        
        if order_type in ("LMT", "PEG MID"):
            has_default_lmt = str(data.get("DEFAULT_LIMIT_PRICE", "")).strip()
            has_spread_30_lmt = str(data.get("LMT_PRICE_FOR_SPREAD_30", "")).strip()
            has_spread_35_lmt = str(data.get("LMT_PRICE_FOR_SPREAD_35", "")).strip()
            if not any([has_default_lmt, has_spread_30_lmt, has_spread_35_lmt]):
                return jsonify({"error": f"For {order_type} orders, you must provide a Default Price Cap or at least one spread-specific price cap."}), 400

        # Additional validation for numeric fields
        def is_float(val):
            try:
                float(val)
                return True
            except (ValueError, TypeError):
                return False

        if str(data.get("DEFAULT_LIMIT_PRICE", "")).strip() and not is_float(data.get("DEFAULT_LIMIT_PRICE")):
            return jsonify({"error": "Default Limit Price must be a number."}), 400
        if str(data.get("DEFAULT_STOP_PRICE", "")).strip() and not is_float(data.get("DEFAULT_STOP_PRICE")):
            return jsonify({"error": "Default Stop Price must be a number."}), 400
        if str(data.get("SNAPMID_OFFSET", "")).strip() and not is_float(data.get("SNAPMID_OFFSET")):
            return jsonify({"error": "Midpoint Offset must be a number."}), 400
        if str(data.get("LMT_PRICE_FOR_SPREAD_30", "")).strip() and not is_float(data.get("LMT_PRICE_FOR_SPREAD_30")):
            return jsonify({"error": "LMT Price for 30-wide Spread must be a number."}), 400
        if str(data.get("LMT_PRICE_FOR_SPREAD_35", "")).strip() and not is_float(data.get("LMT_PRICE_FOR_SPREAD_35")):
            return jsonify({"error": "LMT Price for 35-wide Spread must be a number."}), 400

        # --- End of Corrected Validation Logic ---

        try:
            merged = load_config()
            merged.update({k: str(v) for k, v in data.items()})
            save_config(merged)
            return jsonify({"status": "ok"})
        except Exception as e:
            return jsonify({"error": f"Failed to save config: {e}"}), 500
    return jsonify(load_config())

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

@app.route("/api/status")
def bot_status():
    with _lock:
        running = bot_process is not None and bot_process.poll() is None
    return jsonify({"running": running})

def _session_exists():
    return any(os.path.exists(p) for p in SESSION_FILES)

@app.route("/api/telegram/session", methods=["GET", "DELETE"])
def telegram_session():
    # GET: check if a session exists
    if request.method == "GET":
        return jsonify({
            "exists": _session_exists(),
            "files": [p for p in SESSION_FILES if os.path.exists(p)]
        })

    # DELETE: clear session files (require bot stopped)
    global bot_process
    with _lock:
        if bot_process and bot_process.poll() is None:
            return jsonify({"error": "Bot is running. Stop it before clearing session."}), 409
        removed, errors = [], []
        for p in SESSION_FILES:
            try:
                os.remove(p)
                removed.append(p)
            except FileNotFoundError:
                pass
            except Exception as e:
                errors.append(f"{p}: {e}")
        return jsonify({"status": "ok", "removed": removed, "errors": errors})

@app.route('/api/shutdown', methods=['POST'])
def shutdown():
    """Shuts down the Flask server."""
    shutdown_func = request.environ.get('werkzeug.server.shutdown')
    if shutdown_func is None:
        # This is a fallback for non-development servers, though it's an abrupt exit.
        # For the default Flask server, the above line is the clean way.
        os._exit(0)
    shutdown_func()
    return jsonify({"status": "shutting down"})

# Serve React static files
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return app.send_static_file(path)
    else:
        return app.send_static_file("index.html")

@app.route("/api/history")
def get_history():
    date_str = request.args.get("date")  # Format: YYYY-MM-DD
    if not date_str:
        return jsonify({"history": []})
    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
        if date_str:
            # Filter lines by date prefix, e.g. [TS:2025-08-27 ...]
            filtered = [line.rstrip() for line in lines if line.startswith(f"[TS:{date_str}")]
        else:
            filtered = [line.rstrip() for line in lines]
        return jsonify({"history": filtered})
    except Exception:
        return jsonify({"history": []})

# --- ADD THIS BROWSER-OPENING LOGIC AT THE VERY END ---
def open_browser():
    # Opens the browser to your app after a short delay
    webbrowser.open_new_tab("http://127.0.0.1:9527")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-main", action="store_true", help="Run the main_loop for the bot subprocess.")
    args, unknown = parser.parse_known_args()

    if args.run_main:
        from main import main_loop
        sys.argv = [sys.argv[0]] + unknown
        main_loop()
    else:
        if getattr(sys, 'frozen', False):
            threading.Timer(1.5, open_browser).start()
        # Use socketio.run instead of app.run
        socketio.run(app, host='0.0.0.0', port=9527, debug=False, allow_unsafe_werkzeug=True)