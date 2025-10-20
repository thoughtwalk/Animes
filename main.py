import telebot
import os
import json
import threading
import string
import random
# from flask import Flask, request  # ❌ FLASK IMPORT हटा दिया गया है

# --- CONFIGURATION SETTINGS ---
# BOT_TOKEN is loaded from environment variables (Replit Secrets)
# NOTE: Render reads this from Environment Variables, the default value is for local testing.
BOT_TOKEN = os.environ.get('BOT_TOKEN', '7902930015:AAH9vyXEVlRIdLDQP1NbGtImg-xrW9Flrb0')
ADMIN_ID = 5312279751 # Your Admin ID
BOT_USERNAME = 'One_piece_is_real_bot' # Your Bot Username
DATABASE_FILE = 'database.json' # Database file name
SHORT_ID_LENGTH = 6 # Payload length, e.g., 'oev4Di'

# Required Channel Subscriptions (ID and Invite Link)
REQUIRED_CHANNELS = [
    {"name": "Channel 1 (Anime Content)", "id": -1003144969778, "invite_link": "https://t.me/onepieceisreal144"},
    {"name": "Channel 2 (Anime Content)", "id": -1003104977687, "invite_link": "https://t.me/onepieceisreal155"},
    {"name": "Channel 3 (Anime Content)", "id": -1002965575141, "invite_link": "https://t.me/entertaining166"},
]

bot = telebot.TeleBot(BOT_TOKEN)
# app = Flask(__name__) # ❌ FLASK APP OBJECT हटा दिया गया है

# --- DATABASE FUNCTIONS ---

def load_database():
    """ Loads database from JSON file. """
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            # If the file is empty or corrupt, return an empty dictionary
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

def create_deep_link_and_send(chat_id, file_id):
    """
    Saves the file ID to the database and generates a short Deep Link using the Key.
    """
    try:
        db = load_database()
        short_id = generate_short_id(db)
        db[short_id] = file_id
        save_database(db)

        deep_link = f"https://t.me/{BOT_USERNAME}?start={short_id}"
        
        # Inline button generation
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🚀 Click Here to View Content! 🚀", url=deep_link))

        bot.send_message(
            chat_id,
            f"✅ **Deep Link Generated Successfully!**\n\n"
            f"**Content Type:** `Telegram File (MKV/Video)`\n"
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


# --- OTHER UTILITY FUNCTIONS ---

def get_unsubscribed_channels(user_id):
    """ Checks which required channels the user has not subscribed to. """
    unsubscribed_channels = []
    for channel in REQUIRED_CHANNELS:
        try:
            # NOTE: We use try/except block to handle cases where the user blocks the bot, 
            # or the channel ID is wrong.
            member = bot.get_chat_member(channel['id'], user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                unsubscribed_channels.append(channel)
        except Exception:
            unsubscribed_channels.append(channel)
    return unsubscribed_channels

def send_final_content(chat_id, short_id):
    """
    Retrieves the File ID from the database using the short ID and sends the file.
    """
    try:
        db = load_database()
        file_id = db.get(short_id)

        if not file_id:
            raise ValueError("File ID not found in the database.")

        bot.send_message(chat_id, "✅ **Verification Successful!** Your requested file is here:")
        bot.send_document(chat_id, file_id)
            
    except Exception as e:
        print(f"Error sending content or invalid link: {e}")
        bot.send_message(chat_id, "❌ **Error:** This link is invalid or has expired.")


# --- COMMAND HANDLERS ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    payload = None

    # Extract the argument (payload) after the /start command
    if message.text and len(message.text.split()) > 1:
        payload = message.text.split()[1]
        
    # --- NEW WELCOME MESSAGE LOGIC ---
    if not payload:
        # If there is no Payload (i.e., just /start)
        
        welcome_text = (
            "👋 **Welcome to your Anime Content Bot!** 🎬\n\n"
            "My main purpose is to provide you with your favorite **Anime Content Files** (MKV/Videos/Documents).\n\n"
            "To access the content, please follow these simple steps:\n"
            "1️⃣ **Join our Channels** below and find the content you want to view.\n"
            "2️⃣ Click the **button** provided beneath the content in the channel.\n"
            "3️⃣ I will verify your subscription and instantly deliver the file to you! ✅\n\n"
            "**Thank you for choosing us!** Enjoy the content! ✨"
        )
        
        # Generate channel buttons
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        
        # Button labels (Channel 1, 2, 3) and links
        for i, channel in enumerate(REQUIRED_CHANNELS):
            button_label = f"🔗 **Channel {i+1}** - View Content"
            markup.add(telebot.types.InlineKeyboardButton(button_label, url=channel['invite_link']))
            
        bot.send_message(chat_id, welcome_text, parse_mode='Markdown', reply_markup=markup)
        return # Stop here, no need for subscription check

    # --- Deep Link LOGIC (Payload exists) ---
    
    # Check subscription
    unsubscribed_channels = get_unsubscribed_channels(chat_id)

    if not unsubscribed_channels:
        # Subscription is complete
        bot.send_message(chat_id, "🚀 **Subscription Confirmed!** Fetching your file now...")
        send_final_content(chat_id, payload)
    else:
        # Subscription is incomplete, show buttons to join
        text = "⚠️ **Subscription Required!** Please subscribe to ALL the channels below to proceed, then click the '✅ I Have Subscribed' button."
        
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        for channel in unsubscribed_channels:
            # Use Channel N label for the required channels
            button_label = f"🔗 **Join Channel {REQUIRED_CHANNELS.index(channel) + 1}**"
            markup.add(telebot.types.InlineKeyboardButton(button_label, url=channel['invite_link']))
        
        # Check button
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


# --- NEXT STEP HANDLER ---

def handle_file_upload(message):
    if message.chat.id != ADMIN_ID:
        return

    file_id = None
    
    if message.document:
        file_id = message.document.file_id
    elif message.video:
        file_id = message.video.file_id
    elif message.photo:
        # Get the largest photo file_id
        file_id = message.photo[-1].file_id

    if file_id:
        create_deep_link_and_send(ADMIN_ID, file_id)
    else:
        bot.send_message(
            ADMIN_ID, 
            "❌ **Error:** No file (MKV/Video/Document) detected. Please ensure you **upload it directly** (do not forward). Send the file again."
        )
        bot.register_next_step_handler(message, handle_file_upload)

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
        # Subscription is complete
        bot.edit_message_text(
            "✅ **Verification Successful!** Sending your file now... 🚀", 
            chat_id, 
            message_id, 
            parse_mode='Markdown'
        )
        if payload:
            send_final_content(chat_id, payload)
        
    else:
        # Subscription is incomplete, show updated buttons
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

# --- START POLLING ONLY ---

def run_bot():
    print("Starting Polling for updates...")
    # Polling will keep the bot running indefinitely
    bot.infinity_polling(timeout=20, long_polling_timeout=20, skip_pending=True)

if __name__ == '__main__':
    print("✅ Bot Initialization Successful. Starting Polling...")
    # Polling को सीधे main thread में शुरू करें
    run_bot()

