import threading
from main import app, run_bot_polling
import time

# Flag to ensure polling starts only once
polling_started = False

def start_polling_thread():
    global polling_started
    
    if polling_started:
        return

    # Gunicorn worker को शुरू होने के लिए 1 सेकंड दें
    time.sleep(1) 
    
    print("Attempting to start Telegram Polling Thread...")
    
    polling_thread = threading.Thread(target=run_bot_polling, name="telegram-polling-thread")
    polling_thread.daemon = True 
    polling_thread.start()
    
    # Polling thread को Telegram से कनेक्ट होने के लिए पर्याप्त समय दें
    time.sleep(5) 
    
    if polling_thread.is_alive():
        print("SUCCESS: Background Telegram Polling Thread is now active and SHOULD handle wake-up.")
        polling_started = True
    else:
        print("WARNING: Polling Thread failed to stay alive immediately.")

# 1. Start the Polling in a background thread
start_polling_thread()

# 2. Export the Flask app for Gunicorn
app = app 
