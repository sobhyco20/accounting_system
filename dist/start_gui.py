import threading
import webview
import time
import subprocess
import socket
import sys
import os
import ctypes

def show_error(msg):
    """عرض رسالة خطأ في نافذة"""
    ctypes.windll.user32.MessageBoxW(0, msg, "Error", 1)

def runserver():
    # نحاول تحديد مكان manage.py مهما كان مكان exe
    base_dir = os.path.dirname(os.path.abspath(__file__))
    manage_py = os.path.join(base_dir, "manage.py")
    if not os.path.exists(manage_py):
        show_error("لم يتم العثور على ملف manage.py!\nتأكد أن البرنامج في نفس مجلد المشروع.")
        sys.exit(1)

    # استخدم sys.executable لتحديد مسار بايثون الصحيح حتى من داخل EXE
    python_exe = sys.executable
    try:
        subprocess.run([python_exe, manage_py, "runserver", "127.0.0.1:8000"])
    except Exception as e:
        show_error(f"حدث خطأ أثناء تشغيل السيرفر:\n{e}")
        sys.exit(1)

def wait_for_server(host, port, timeout=30):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except OSError:
            time.sleep(0.5)
    return False

if __name__ == '__main__':
    try:
        # شغل Django كسيرفر فرعي
        threading.Thread(target=runserver, daemon=True).start()

        # انتظر حتى يتأكد أن السيرفر بدأ
        if wait_for_server("127.0.0.1", 8000):
            webview.create_window("برنامج المحاسبة", "http://127.0.0.1:8000", width=1200, height=800)
            webview.start()
        else:
            show_error("السيرفر لم يعمل.\nتأكد من أن جميع ملفات المشروع موجودة وأنه يعمل بدون مشاكل.")
    except Exception as e:
        show_error(f"حدث خطأ غير متوقع:\n{e}")
