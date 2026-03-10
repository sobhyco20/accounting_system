import threading
import webview
import subprocess
import time
import socket
import os
import sys
import ctypes

def show_error(msg):
    ctypes.windll.user32.MessageBoxW(0, msg, "Error", 1)

def runserver():
    try:
        subprocess.Popen([sys.executable, "manage.py", "runserver", "127.0.0.1:8000"])
    except Exception as e:
        show_error(f"تشغيل سيرفر Django فشل:\n{e}")

def wait_for_server(host, port, timeout=30):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except OSError:
            time.sleep(0.5)
    return False

if __name__ == "__main__":
    threading.Thread(target=runserver, daemon=True).start()
    if wait_for_server("127.0.0.1", 8000):
        webview.create_window("Accounting System", "http://127.0.0.1:8000", width=1200, height=800)
        webview.start()
    else:
        show_error("السيرفر لم يعمل. تأكد أن كل الملفات الضرورية متوفرة.")
