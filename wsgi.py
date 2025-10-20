import threading
from main import app, run_bot_polling
import time
import signal # Signal module import करें
import sys

# Global variable for the polling thread
polling_thread = None
polling_started = False

def start_polling_thread():
    global polling_started, polling_thread
    
    if polling_started:
        return

    time.sleep(1) 
    
    print("Attempting to start Telegram Polling Thread...")
    
    polling_thread = threading.Thread(target=run_bot_polling, name="telegram-polling-thread")
    polling_thread.daemon = True 
    polling_thread.start()
    
    time.sleep(5) 
    
    if polling_thread.is_alive():
        print("SUCCESS: Background Telegram Polling Thread is now active.")
        polling_started = True
    else:
        print("WARNING: Polling Thread failed to stay alive immediately.")

# --- SIGTERM Signal Handler ---
def sigterm_handler(_signo, _stack_frame):
    """Gracefully shuts down the polling thread on SIGTERM from Gunicorn."""
    global polling_thread
    print("Received SIGTERM signal. Attempting to shut down Polling Thread...")
    
    # NOTE: Python's threading library doesn't easily allow forced thread termination.
    # The best we can do is signal the main process to exit gracefully.
    # Since our polling is in an infinite loop, we rely on the parent process exit.
    
    # We rely on the daemon=True setting, but explicitly exiting the process helps.
    sys.exit(0)


# 1. Register the signal handler
# Gunicorn sends SIGTERM when shutting down.
signal.signal(signal.SIGTERM, sigterm_handler)

# 2. Start the Polling in a background thread
start_polling_thread()

# 3. Export the Flask app for Gunicorn
app = app 
