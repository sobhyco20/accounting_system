import subprocess
import threading
import webview
import time
import os

def start_django():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    subprocess.Popen(["python", "manage.py", "runserver", "127.0.0.1:8000"])

# شغّل Django في الخلفية
threading.Thread(target=start_django).start()

# انتظر تشغيل السيرفر (يمكنك زيادة الوقت حسب الحاجة)
time.sleep(3)

# افتح نافذة البرنامج
webview.create_window("Sobhy ERP", "http://127.0.0.1:8000/admin/", width=1200, height=800, resizable=True)
webview.start()
