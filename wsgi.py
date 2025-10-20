import threading
from main import app, run_bot_polling

# Ensure the Polling thread is started only once when Gunicorn begins

def start_polling_thread():
    # Check if the polling thread is already running
    for t in threading.enumerate():
        if t.name == "telegram-polling-thread":
            return

    # If not running, start the thread
    polling_thread = threading.Thread(target=run_bot_polling, name="telegram-polling-thread")
    polling_thread.daemon = True 
    polling_thread.start()
    print("Background Telegram Polling Thread Started.")

# 1. Start the Polling in a background thread
start_polling_thread()

# 2. Export the Flask app for Gunicorn
app = app # Re-export the app instance for Gunicorn
