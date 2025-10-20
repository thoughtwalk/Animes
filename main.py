import telebot
import os
import json
import threading
import string
import random
import time
from flask import Flask # Flask imported for Render Web Service compliance

# --- CONFIGURATION SETTINGS ---
# BOT_TOKEN is loaded from environment variables (Render Environment Variables)
BOT_TOKEN = os.environ.get('BOT_TOKEN', '7902930015:AAH9vyXEVlRIdLDQP1NbGtImg-xrW9Flrb0')
ADMIN_ID = 5312279751 # Your Admin ID
BOT_USERNAME = 'One_piece_is_real_bot' # Your Bot Username
DATABASE_FILE = 'database.json'
SHORT_ID_LENGTH = 6

# Required Channel Subscriptions (ID and Invite Link)
REQUIRED_CHANNELS = [
    {"name": "Channel 1 (Anime Content)", "id": -1003144969778, "invite_link": "https://t.me/onepieceisreal144"},
    {"name": "Channel 2 (Anime Content)", "id": -1003104977687, "invite_link": "https://t.me/onepieceisreal155"},
    {"name": "Channel 3 (Anime Content)", "id": -1002965575141, "invite_link": "https://t.me/entertaining166"},
    {"name": "Channel 4 (Anime Content)", "id": -1003069758570, "invite_link": "https://t.me/anime14400"} 
]

# --- TEMPORARY FILE SETTINGS ---
DELETION_TIME_SECONDS = 30 * 60  # 30 minutes in seconds
DELETION_NOTICE = "🗑️ **This message has been automatically deleted.** The file's temporary viewing period has expired."
WARNING_MESSAGE = "🚨 **Important Notice:** This file is temporary and will be automatically deleted from this chat in **30 minutes**. Please forward/save the content immediately to your Saved Messages or another secure location."


bot = telebot.TeleBot(BOT_TOKEN)
# Temporary storage for file_id during the multi-step caption input process
file_id_storage = {} 

# --- DATABASE FUNCTIONS ---

def load_database():
    """ Loads database from JSON file. """
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            # If file is empty or corrupted, return empty dict
            return {}
    return {}

def save_database(db):
    """ Saves the database to JSON file. """
    with open(DATABASE_FILE, 'w') as f:
        json.dump(db, f, indent=4)

def generate_short_id(db):
    """ Generates a unique, short Base64-safe ID. """
    chars = string.ascii_letters + string.digits + '-_'
    while True:
        short_id = ''.join(random.choice(chars) for _ in range(SHORT_ID_LENGTH))
        if short_id not in db:
            return short_id

# --- Deep Link GENERATION FUNCTION ---

def create_deep_link_and_send(chat_id, file_id, caption):
    """
    Saves the file ID and caption to the database and generates a short Deep Link.
    """
    try:
        db = load_database()
        short_id = generate_short_id(db)
        
        # Save file_id and caption
        db[short_id] = {"file_id": file_id, "caption": caption}
        save_database(db)

        deep_link = f"https://t.me/{BOT_USERNAME}?start={short_id}"
        
        # Inline button generation
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🚀 Click Here to View Content! 🚀", url=deep_link))

        bot.send_message(
            chat_id,
            f"✅ **Deep Link Generated Successfully!**\n\n"
            f"**Content Type:** `Telegram File`\n"
            f"**Caption:** `{caption[:50]}...`\n" 
            f"This link is **short** and **fully functional**.\n\n"
            f"Use the button below in your channel post:",
            parse_mode='Markdown',
            reply_markup=markup
        )
        
        # Also send the URL for admin to copy
        bot.send_message(chat_id, f"🔗 Deep Link URL: `{deep_link}`", parse_mode='Markdown')

    except Exception as e:
        print(f"Error generating Deep Link: {e}")
        bot.send_message(chat_id, "❌ **Error:** Failed to generate Deep Link. Please check the console.")


# --- DELETION LOGIC ---

def schedule_deletion(chat_id, file_message_id, warning_message_id):
    """
    Deletes the warning message and edits the file message after the timer expires.
    This function runs in a separate thread.
    """
    try:
        # 1. Delete the warning message
        bot.delete_message(chat_id, warning_message_id)
        print(f"Deleted warning message {warning_message_id} in chat {chat_id}")
    except Exception as e:
        print(f"Warning message {warning_message_id} already deleted or error during deletion: {e}")

    try:
        # 2. Edit the file message with the deletion notice
        bot.edit_message_text(
            DELETION_NOTICE, 
            chat_id, 
            file_message_id, 
            parse_mode='Markdown'
        )
        print(f"Edited file message {file_message_id} in chat {chat_id} to deletion notice.")
    except Exception as e:
        print(f"File message {file_message_id} already deleted or error during editing: {e}")


# --- OTHER UTILITY FUNCTIONS ---

def get_unsubscribed_channels(user_id):
    """ Checks which required channels the user has not subscribed to. """
    unsubscribed_channels = []
    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(channel['id'], user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                unsubscribed_channels.append(channel)
        except Exception:
            # Assume not subscribed if error occurs (e.g., bot not in channel)
            unsubscribed_channels.append(channel)
    return unsubscribed_channels

def send_final_content(chat_id, short_id):
    """
    Retrieves the File ID and caption from the database, sends the file, 
    sends the warning, and schedules the deletion.
    """
    try:
        db = load_database()
        data = db.get(short_id)

        if not data or not isinstance(data, dict):
            raise ValueError("File data not found or invalid.")

        file_id = data.get("file_id")
        caption = data.get("caption", "")

        if not file_id:
             raise ValueError("File ID not found in the database.")

        formatted_caption = f"*{caption}*"

        # 1. Send success message 
        bot.send_message(chat_id, "✅ **Verification Successful!** Your requested file is here:")

        # 2. Send the file (Document)
        sent_file_msg = bot.send_document(
            chat_id, 
            file_id, 
            caption=formatted_caption, 
            parse_mode='Markdown'
        )
        file_message_id = sent_file_msg.message_id
        
        # 3. Send the Warning Message
        sent_warning_msg = bot.send_message(
            chat_id, 
            WARNING_MESSAGE, 
            parse_mode='Markdown'
        )
        warning_message_id = sent_warning_msg.message_id
        
        # 4. Schedule deletion after 30 minutes (1800 seconds)
        timer = threading.Timer(
            DELETION_TIME_SECONDS, 
            schedule_deletion, 
            args=[chat_id, file_message_id, warning_message_id]
        )
        timer.start()
            
    except Exception as e:
        print(f"Error sending content or invalid link: {e}")
        bot.send_message(chat_id, "❌ **Error:** This link is invalid or has expired.")


# --- COMMAND HANDLERS ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    payload = None

    if message.text and len(message.text.split()) > 1:
        payload = message.text.split()[1]
        
    # --- WELCOME MESSAGE LOGIC (No Payload) ---
    if not payload:
        
        welcome_text = (
            "👋 **Welcome to your Anime Content Bot!** 🎬\n\n"
            "My main purpose is to provide you with your favorite **Anime Content Files** (MKV/Videos/Documents).\n\n"
            "To access the content, please follow these simple steps:\n"
            "1️⃣ **Join our Channels** below and find the content you want to view.\n"
            "2️⃣ Click the **button** provided beneath the content in the channel.\n"
            "3️⃣ I will verify your subscription and instantly deliver the file to you! ✅\n\n"
            "**Thank you for choosing us!** Enjoy the content! ✨"
        )
        
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        
        for i, channel in enumerate(REQUIRED_CHANNELS):
            button_label = f"🔗 **Channel {i+1}** - View Content"
            markup.add(telebot.types.InlineKeyboardButton(button_label, url=channel['invite_link']))
            
        bot.send_message(chat_id, welcome_text, parse_mode='Markdown', reply_markup=markup)
        return

    # --- Deep Link LOGIC (Payload exists) ---
    
    unsubscribed_channels = get_unsubscribed_channels(chat_id)

    if not unsubscribed_channels:
        bot.send_message(chat_id, "🚀 **Subscription Confirmed!** Fetching your file now...")
        send_final_content(chat_id, payload)
    else:
        text = "⚠️ **Subscription Required!** Please subscribe to ALL the channels below to proceed, then click the '✅ I Have Subscribed' button."
        
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        for channel in unsubscribed_channels:
            button_label = f"🔗 **Join Channel {REQUIRED_CHANNELS.index(channel) + 1}**"
            markup.add(telebot.types.InlineKeyboardButton(button_label, url=channel['invite_link']))
        
        callback_data = f"check_{payload}"
        markup.add(telebot.types.InlineKeyboardButton("✅ I Have Subscribed", callback_data=callback_data))

        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='Markdown')

# Admin Command: Deep Link Generation Mode
@bot.message_handler(commands=['generate'])
def handle_generate_command(message):
    if message.chat.id != ADMIN_ID:
        return bot.send_message(message.chat.id, "❌ **Error:** This command is for the **Admin Only**.")

    bot.send_message(
        ADMIN_ID,
        "✅ **Deep Link Generation Mode (File):** Please send the file (Video, MKV, or any Document) for which you want to generate a **Short Deep Link**."
    )
    bot.register_next_step_handler(message, handle_file_upload)


# --- MULTI-STEP HANDLERS ---

def handle_file_upload(message):
    if message.chat.id != ADMIN_ID:
        return

    file_id = None
    
    if message.document:
        file_id = message.document.file_id
    elif message.video:
        file_id = message.video.file_id
    elif message.photo:
        file_id = message.photo[-1].file_id 

    if file_id:
        file_id_storage[ADMIN_ID] = file_id 
        msg = bot.send_message(
            ADMIN_ID, 
            "📝 **Caption Input:** Please send the **caption** you want to attach to this file. (Example: Use mx player. @yourchannel)"
        )
        bot.register_next_step_handler(msg, handle_caption_input)
    else:
        bot.send_message(
            ADMIN_ID, 
            "❌ **Error:** No file (MKV/Video/Document) detected. Please ensure you **upload it directly** (do not forward). Send the file again."
        )
        bot.register_next_step_handler(message, handle_file_upload)

def handle_caption_input(message):
    if message.chat.id != ADMIN_ID:
        return
    
    if ADMIN_ID in file_id_storage:
        file_id = file_id_storage.pop(ADMIN_ID) 
        caption = message.text 
        
        create_deep_link_and_send(ADMIN_ID, file_id, caption)
    else:
         bot.send_message(
            ADMIN_ID, 
            "❌ **Error:** File information was lost. Please start again with the `/generate` command."
        )

# --- GENERAL TEXT HANDLER ---

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text_messages(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if not text.startswith('/'): 
        bot.send_message(chat_id, "🤖 **I'm an automated bot.** Please use a Deep Link from one of our channels or send **/start** to see my welcome message. ✨")
    
# --- CALLBACK HANDLERS ---

@bot.callback_query_handler(func=lambda call: call.data.startswith('check_'))
def check_callback(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    bot.answer_callback_query(call.id, "Checking subscription status...")
    
    data = call.data.split('_', 1) 
    payload = data[1] if len(data) > 1 and data[1] != 'None' else None

    unsubscribed_channels = get_unsubscribed_channels(chat_id)
    
    if not unsubscribed_channels:
        bot.edit_message_text(
            "✅ **Verification Successful!** Sending your file now... 🚀", 
            chat_id, 
            message_id, 
            parse_mode='Markdown'
        )
        if payload:
            send_final_content(chat_id, payload)
        
    else:
        text = "❌ **Still Incomplete!** Please subscribe to ALL the required channels below and then press '🔄 Check Again'."
        
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        for channel in unsubscribed_channels:
            button_label = f"🔗 **Join Channel {REQUIRED_CHANNELS.index(channel) + 1}**"
            markup.add(telebot.types.InlineKeyboardButton(button_label, url=channel['invite_link']))
        
        callback_data = f"check_{payload}"
        markup.add(telebot.types.InlineKeyboardButton("🔄 Check Again", callback_data=callback_data))

        bot.edit_message_text(
            text, 
            chat_id, 
            message_id, 
            reply_markup=markup, 
            parse_mode='Markdown'
        )

# --- Telegram Polling Logic (Runs in a separate thread) ---

def run_bot_polling():
    """Starts the bot polling in a resilient manner with retries and cleanup."""
    print("Starting Resilient Polling for Telegram updates with cleanup...")
    
    # CRITICAL: 409 Error Fix (Webhook Cleanup)
    try:
        # Webhook को हटाना सुनिश्चित करता है कि Polling शुरू करने से पहले कोई पुराना Webhook/Polling session सक्रिय न हो
        bot.delete_webhook()
        print("Successfully cleaned up any old webhook/polling sessions.")
    except Exception as e:
        # यह पहली बार में विफल हो सकता है, लेकिन हम इसे नज़रअंदाज़ कर सकते हैं
        print(f"Webhook cleanup failed (may be harmless): {e}") 

    # यह अनंत लूप सुनिश्चित करता है कि Polling thread कभी भी स्थायी रूप से क्रैश न हो।
    while True:
        try:
            print("Attempting connection to Telegram...")
            # Polling will run indefinitely, looking for updates
            bot.infinity_polling(timeout=20, long_polling_timeout=20, skip_pending=True)
            # Should not reach here normally
            break 
        except Exception as e:
            # त्रुटि होने पर 10 सेकंड प्रतीक्षा करें और फिर से प्रयास करें।
            print(f"Polling connection ERROR: {e}. Retrying in 10 seconds...")
            time.sleep(10)


# --- FLASK APP FOR RENDER COMPLIANCE (NEW) ---

# Create a Flask instance for Gunicorn to run
# This is exported for Gunicorn via wsgi.py
app = Flask(__name__)

@app.route('/')
def home():
    """Simple route to satisfy Render's health check."""
    return "Telegram Bot Polling Service is Running in Background.", 200


# --- STARTUP LOGIC ---

if __name__ == '__main__':
    # This block runs ONLY when you execute 'python main.py' locally.
    print("Running locally. Starting bot polling directly.")
    run_bot_polling()
        
