import telebot
import os
import json
import threading
import string
import random
import time
import requests
from flask import Flask, request

# --- CONFIGURATION SETTINGS ---
# BOT_TOKEN is loaded from environment variables (Render Environment Variables)
BOT_TOKEN = os.environ.get('BOT_TOKEN', '7902930015:AAEnGzQaZHdRcmuAxWIPDIcerJVqRhmx9D4') 
ADMIN_ID = 5312279751  # Your Admin ID
BOT_USERNAME = 'One_piece_is_real_bot'  # Your Bot Username
DATABASE_FILE = 'database.json'
SHORT_ID_LENGTH = 6
# >>> Deletion time set to 10 minutes (600 seconds)
DELETION_TIME_MINUTES = 10
DELETION_TIME_SECONDS = DELETION_TIME_MINUTES * 60

# Required Channel Subscriptions (ID and Invite Link)
REQUIRED_CHANNELS = [
    {
        "name": "Channel 1 (Anime Content)",
        "id": -1003144969778,
        "invite_link": "https://t.me/onepieceisreal144"
    },
    {
        "name": "Channel 2 (Anime Content)",
        "id": -1003104977687,
        "invite_link": "https://t.me/onepieceisreal155" 
    },
    {
        "name": "Channel 3 (Anime Content)",
        "id": -1002965575141,
        "invite_link": "https://t.me/entertaining166"
    },
    {
        "name": "Channel 4 (Anime Content)",
        "id": -1003069758570,
        "invite_link": "https://t.me/anime14400"
    },
]

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- DATABASE FUNCTIONS ---

def load_database():
    """ Loads database from JSON file. """
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("⚠️ WARNING: database.json is corrupted or empty. Starting with an empty dict.")
            return {}
    return {}


def save_database(db):
    """ Saves the database to JSON file. """
    with open(DATABASE_FILE, 'w') as f:
        json.dump(db, f, indent=4) # <-- FIX: Changed 'db' to 'f' here
        # Note: This change fixes the 'Failed to generate Deep Link' error.


def generate_short_id(db):
    """ Generates a unique, short Base64-safe ID. """
    chars = string.ascii_letters + string.digits + '-_'
    while True:
        short_id = ''.join(
            random.choice(chars) for _ in range(SHORT_ID_LENGTH))
        if short_id not in db:
            return short_id


# --- Deep Link GENERATION FUNCTION ---


def create_deep_link_and_send(chat_id, content_data):
    """
    Saves the file ID and caption to the database and generates a short Deep Link.
    """
    try:
        db = load_database()
        short_id = generate_short_id(db)

        db[short_id] = content_data
        save_database(db)

        deep_link = f"https://t.me/{BOT_USERNAME}?start={short_id}"

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(
            telebot.types.InlineKeyboardButton(
                "🚀 Click Here to View Content! 🚀", url=deep_link))

        bot.send_message(
            chat_id,
            f"✅ <b>Deep Link Generated Successfully!</b>\n\n"
            f"<b>Content Type:</b> <code>Telegram File (MKV/Video)</code>\n"
            f"<b>Attached Caption (Preview):</b> \n<code>{content_data.get('caption', 'None')}</code>\n\n"
            f"This link is <b>short</b> and <b>fully functional</b>.\n\n"
            f"Use the button below in your channel post:",
            parse_mode='HTML', 
            reply_markup=markup)

        bot.send_message(chat_id,
                         f"🔗 Deep Link URL: <code>{deep_link}</code>",
                         parse_mode='HTML')

    except Exception as e:
        print(f"Error generating Deep Link: {e}")
        bot.send_message(
            chat_id,
            "❌ <b>Error:</b> Failed to generate Deep Link. Please check the console.",
            parse_mode='HTML')


# --- DELETION LOGIC ---

def schedule_deletion_cleanup(chat_id, message_id_to_delete, delay_seconds):
    """ Helper function to clean up the confirmation message after a short delay (e.g., 5 minutes). """
    time.sleep(delay_seconds)
    try:
        bot.delete_message(chat_id, message_id_to_delete)
        print(f"✅ Cleaned up confirmation message {message_id_to_delete}.")
    except Exception as e:
        print(f"⚠️ Could not delete cleanup message {message_id_to_delete}: {e}")

def schedule_deletion(chat_id, message_id_to_delete, delay_seconds, is_file=False):
    """
    Schedules the deletion of a specific message after a given delay 
    using a background thread.
    """

    def delete_message_thread():
        # Wait for the specified time (10 minutes)
        time.sleep(delay_seconds)
        
        try:
            # Attempt to delete the original message (Warning or File)
            bot.delete_message(chat_id, message_id_to_delete)
            print(f"✅ Successfully deleted message {message_id_to_delete} in chat {chat_id} (is_file: {is_file}).")
            
            # Send the confirmation message only when deleting the actual file message (is_file=True)
            if is_file:
                # Updated confirmation message as requested: "This file is deleted due to 10 minutes time limit"
                confirmation_msg = bot.send_message(
                    chat_id,
                    "**🚨 File Deleted: This file is deleted due to the 10-minute time limit.**",
                    parse_mode='Markdown'
                )
                # Schedule the confirmation message itself to be deleted after 5 minutes (300 seconds)
                threading.Thread(target=schedule_deletion_cleanup, 
                                 args=(chat_id, confirmation_msg.message_id, 5 * 60)).start()

        except telebot.apihelper.ApiException as e:
            # Ignore "Message to delete not found" 
            if 'message to delete not found' not in str(e):
                print(f"⚠️ Could not delete message {message_id_to_delete} in chat {chat_id}: {e}")
        except Exception as e:
            # Prevents unexpected errors from crashing the thread
            print(f"🚨 Unexpected error in deletion thread for {message_id_to_delete}: {e}")

    deletion_thread = threading.Thread(target=delete_message_thread)
    deletion_thread.daemon = True
    deletion_thread.start()


# --- OTHER UTILITY FUNCTIONS ---


def get_unsubscribed_channels(user_id):
    """ Checks which required channels the user has not joined to. """
    unsubscribed_channels = []
    for channel in REQUIRED_CHANNELS:
        try:
            # Check if user is a member/admin/creator
            member = bot.get_chat_member(channel['id'], user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                unsubscribed_channels.append(channel)
        except telebot.apihelper.ApiException as e:
            if 'user not found' in str(e) or 'Bad Request: chat not found' in str(e):
                unsubscribed_channels.append(channel)
            else:
                 # Log other API errors but proceed
                print(f"⚠️ Telegram API Error in get_unsubscribed_channels for {channel['name']}: {e}")
                unsubscribed_channels.append(channel) 
        except Exception:
            unsubscribed_channels.append(channel)
    return unsubscribed_channels


# --- send_final_content() (UPDATED Warning Message) ---


def send_final_content(chat_id, short_id):
    """
    Retrieves the content data and sends the file with the associated caption 
    and schedules it for deletion. 
    """
    try:
        db = load_database()
        content_data = db.get(short_id)

        if not content_data or 'file_id' not in content_data:
            raise ValueError(
                "Content data or File ID not found in the database.")

        file_id = content_data['file_id']
        caption = content_data.get(
            'caption',
            None)  

        bot.send_message(
            chat_id,
            "✅ <b>Verification Successful!</b> Fetching your file now...",
            parse_mode='HTML')

        # --- WARNING MESSAGE ---
        # Warning message updated to 10 minutes and made entirely BOLD
        warning_message = bot.send_message(
            chat_id,
            "<b>🚨 SECURITY ALERT! 🚨\n\n"
            "This file will be automatically deleted from this chat in 10 minutes.\n\n"
            "To keep the content, please Forward it immediately to your Saved Messages or another private chat/channel. The link will expire after the deletion.</b>",
            parse_mode='HTML'
        )

        # --- SEND FILE AND GET MESSAGE ID ---
        file_message = bot.send_document(
            chat_id,
            file_id,
            caption=
            caption,  
            parse_mode='HTML'
        )

        # --- SCHEDULE DELETION ---
        # 1. Schedule the Warning message for deletion (is_file=False)
        schedule_deletion(chat_id, warning_message.message_id,
                          DELETION_TIME_SECONDS, is_file=False)
                          
        # 2. Schedule the actual File message for deletion (is_file=True)
        #    This is the message whose deletion will trigger the final confirmation.
        schedule_deletion(chat_id, file_message.message_id,
                          DELETION_TIME_SECONDS, is_file=True)

    except Exception as e:
        # Prevents bot from crashing on invalid/expired file_id
        print(f"Error sending content or invalid link: {e}")
        bot.send_message(
            chat_id,
            "❌ <b>Error:</b> This link is invalid or has expired.",
            parse_mode='HTML')


# --- COMMAND HANDLERS ---


@bot.message_handler(commands=['start'])
def handle_start(message):
    try:
        chat_id = message.chat.id
        payload = None

        if message.text and len(message.text.split()) > 1:
            payload = message.text.split()[1]

        if not payload:

            welcome_text = (
                "👋 <b>Welcome to your Anime Content Bot!</b> 🎬\n\n"
                "My main purpose is to provide you with your favorite <b>Anime Content Files</b> (MKV/Videos/Documents).\n\n"
                "To access the content, please follow these simple steps:\n"
                "1️⃣ <b>Join our Channels</b> below and find the content you want to view.\n"
                "2️⃣ Click the <b>button</b> provided beneath the content in the channel.\n"
                "3️⃣ I will verify your joining and instantly deliver the file to you! ✅\n\n" 
                "<b>Thank you for choosing us!</b> Enjoy the content! ✨")

            markup = telebot.types.InlineKeyboardMarkup(row_width=1)
            for i, channel in enumerate(REQUIRED_CHANNELS):
                button_label = f"🔗 Channel {i+1} - View Content"
                markup.add(
                    telebot.types.InlineKeyboardButton(button_label,
                                                       url=channel['invite_link']))

            bot.send_message(chat_id,
                            welcome_text,
                            parse_mode='HTML',
                            reply_markup=markup)  
            return

        unsubscribed_channels = get_unsubscribed_channels(chat_id)

        if not unsubscribed_channels:
            send_final_content(chat_id, payload)
        else:
            
            text = "⚠️ <b>Joining Required!</b> Please join ALL the channels below to proceed, then click the '✅ I Have Joined' button."

            markup = telebot.types.InlineKeyboardMarkup(row_width=1)
            for channel in unsubscribed_channels:
                button_label = f"🔗 Join Channel {REQUIRED_CHANNELS.index(channel) + 1}"
                markup.add(
                    telebot.types.InlineKeyboardButton(button_label,
                                                       url=channel['invite_link']))

            callback_data = f"check_{payload}"
            markup.add(
                telebot.types.InlineKeyboardButton("✅ I Have Joined",
                                                   callback_data=callback_data))

            bot.send_message(chat_id, text, reply_markup=markup,
                            parse_mode='HTML')
    except Exception as e:
        print(f"Error in handle_start: {e}")


# Admin Command: Deep Link Generation Mode
@bot.message_handler(commands=['generate'])
def handle_generate_command(message):
    try:
        if message.chat.id != ADMIN_ID:
            return bot.send_message(
                message.chat.id,
                "❌ <b>Error:</b> This command is for the <b>Admin Only</b>.",
                parse_mode='HTML')

        bot.send_message(
            ADMIN_ID,
            "✅ <b>Deep Link Generation Mode (File):</b> Please send the file (Video, MKV, or any Document) for which you want to generate a <b>Short Deep Link</b>. <i>Note: The caption will automatically be formatted as BOLD.</i>",
            parse_mode='HTML')
        bot.register_next_step_handler(message, handle_file_upload)
    except Exception as e:
        print(f"Error in handle_generate_command: {e}")


# --- NEXT STEP HANDLERS ---


def handle_file_upload(message):
    """ Captures the file ID and asks for the caption. """
    try:
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
            bot.send_message(
                ADMIN_ID,
                "📝 <b>Caption Required:</b> Please send the text (Caption) you want to attach to this content. <i>You can include @usernames, and the entire caption will be automatically made BOLD.</i>",
                parse_mode='HTML')
            bot.register_next_step_handler(message, handle_caption_input, file_id)

        else:
            bot.send_message(
                ADMIN_ID,
                "❌ <b>Error:</b> No file (MKV/Video/Document) detected. Please ensure you <b>upload it directly or forward a message that contains an actual file</b>. Send the file again.",
                parse_mode='HTML')
            bot.register_next_step_handler(message, handle_file_upload)
    except Exception as e:
        print(f"Error in handle_file_upload: {e}")


def handle_caption_input(message, file_id):
    """ Captures the caption, automatically makes it BOLD (using HTML <b>), and generates the final deep link. """
    try:
        if message.chat.id != ADMIN_ID:
            return

        caption_text = message.text.strip() if message.text else ""

        if not message.text:
            bot.send_message(
                ADMIN_ID,
                "❌ <b>Error:</b> Caption was not detected as text. Please send the caption text again.",
                parse_mode='HTML')
            bot.register_next_step_handler(message, handle_caption_input, file_id)
            return

        auto_bold_caption = f"<b>{caption_text}</b>"

        content_data = {'file_id': file_id, 'caption': auto_bold_caption}

        create_deep_link_and_send(ADMIN_ID, content_data)
    except Exception as e:
        print(f"Error in handle_caption_input: {e}")


# --- GENERAL TEXT HANDLER ---


@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text_messages(message):
    try:
        chat_id = message.chat.id
        # text = message.text.strip() # Not used in this version

        bot.send_message(
            chat_id,
            "🤖 <b>I'm an automated bot.</b> Please use a Deep Link from one of our channels or send /start to see my welcome message. ✨",
            parse_mode='HTML')
    except Exception as e:
        print(f"Error in handle_text_messages: {e}")


# --- CALLBACK HANDLERS ---


@bot.callback_query_handler(func=lambda call: call.data.startswith('check_'))
def check_callback(call):
    try:
        chat_id = call.message.chat.id
        message_id = call.message.message_id

        bot.answer_callback_query(call.id, "Checking joining status...") 

        data = call.data.split('_', 1)
        payload = data[1] if len(data) > 1 and data[1] != 'None' else None

        unsubscribed_channels = get_unsubscribed_channels(chat_id)

        if not unsubscribed_channels:
            
            bot.edit_message_text(
                "✅ <b>Verification Successful!</b> Sending your file now... 🚀",
                chat_id,
                message_id,
                parse_mode='HTML'  
            )
            if payload:
                send_final_content(chat_id, payload)

        else:
            
            text = "❌ <b>Join Incomplete!</b> Please join ALL the required channels below and then press '🔄 Check Again'."

            markup = telebot.types.InlineKeyboardMarkup(row_width=1)
            for channel in unsubscribed_channels:
                button_label = f"🔗 Join Channel {REQUIRED_CHANNELS.index(channel) + 1}"
                markup.add(
                    telebot.types.InlineKeyboardButton(button_label,
                                                       url=channel['invite_link']))

            callback_data = f"check_{payload}"
            markup.add(
                telebot.types.InlineKeyboardButton("🔄 Check Again",
                                                   callback_data=callback_data))

            bot.edit_message_text(
                text,
                chat_id,
                message_id,
                reply_markup=markup,
                parse_mode='HTML'  
            )
    except Exception as e:
        print(f"Error in check_callback: {e}")


# --- KEEP-ALIVE MECHANISM ---

def keep_alive():
    """ 
    Sends an external request every 25 minutes to prevent the inactivity timer.
    """
    # NOTE: RENDER_EXTERNAL_URL is set in your Render dashboard Environment Variables
    RENDER_PUBLIC_URL = os.environ.get('RENDER_EXTERNAL_URL', 'https://animes1.onrender.com/')
    PING_INTERVAL_SECONDS = 25 * 60 

    while True:
        try:
            # We ping the Render URL to keep it awake
            requests.get(RENDER_PUBLIC_URL, timeout=10)
            # print(f"🚀 Keep-Alive Ping Sent to {RENDER_PUBLIC_URL}. Timer reset.")
        except Exception as e:
            # If the ping fails, log the error but keep the thread alive
            print(f"⚠️ Keep-Alive Error (Pinging Render URL): {e}. Trying again soon.")
        
        time.sleep(PING_INTERVAL_SECONDS)

# --- START SERVER AND POLLING (FIXED Indentation) ---


@app.route('/', methods=['GET', 'HEAD'])
def index():
    # Ensures the root path always returns 200 OK for UptimeRobot
    try:
        # print("🌐 Received GET/HEAD request on root path. Returning 200 OK.")
        return 'Bot is running...', 200
    except Exception as e:
        print(f"🚨 Critical Flask Error in index route: {e}")
        return 'Internal Server Error', 500 


def run_bot():
    print("Starting Polling for updates...")
    while True: 
        try:
            # Added long_polling_timeout=30 for better resilience against network issues
            bot.polling(timeout=30, 
                        skip_pending=True,
                        non_stop=True,
                        long_polling_timeout=30) 
        except Exception as e:
            # Restarts the polling loop on a fatal error, but keeps the Flask server alive.
            print(f"🚨 FATAL POLLING ERROR: {e}. Restarting polling loop in 5 seconds...")
            time.sleep(5) 

if __name__ == '__main__':
    print("✅ Bot Initialization Successful.")
    
    # 1. Start the Polling Thread (for Telegram updates)
    polling_thread = threading.Thread(target=run_bot)
    polling_thread.daemon = True
    polling_thread.start()
    
    # 2. Start the Keep-Alive Thread (to prevent sleeping)
    keep_alive_thread = threading.Thread(target=keep_alive)
    keep_alive_thread.daemon = True
    keep_alive_thread.start()

    # 3. Start the Flask Server (This keeps the Render URL alive)
    app.run(h
