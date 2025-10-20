import threading
from main import app, run_bot_polling
import time # Import time for the slight delay check

# Flag to ensure polling starts only once
polling_started = False

def start_polling_thread():
    global polling_started

    if polling_started:
        return

    print("Attempting to start Telegram Polling Thread...")

    polling_thread = threading.Thread(target=run_bot_polling, name="telegram-polling-thread")
    polling_thread.daemon = True 
    polling_thread.start()

    # Give the polling thread a moment to start up and connect
    time.sleep(5) 

    if polling_thread.is_alive():
        print("SUCCESS: Background Telegram Polling Thread is now active.")
        polling_started = True
    else:
        print("WARNING: Polling Thread failed to stay alive immediately.")

# 1. Start the Polling in a background thread
start_polling_thread()

# 2. Export the Flask app for Gunicorn
app = app 
