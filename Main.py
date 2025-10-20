import telebot
import os
import json
import threading
import string
import random
import time 
from flask import Flask, request

# --- CONFIGURATION SETTINGS ---
# BOT_TOKEN is loaded from environment variables (Render Secrets)
BOT_TOKEN = os.environ.get('BOT_TOKEN', '7902930015:AAH9vyXEVlRIdLDQP1NbGtImg-xrW9Flrb0') 
ADMIN_ID = 5312279751 # Your Admin ID
BOT_USERNAME = 'One_piece_is_real_bot' # Your Bot Username
DATABASE_FILE = 'database.json' # Database file name
SHORT_ID_LENGTH = 6 # Payload length, e.g., 'oev4Di'
DELETION_TIME_MINUTES = 30 # Time after which the file will be deleted
DELETION_TIME_SECONDS = DELETION_TIME_MINUTES * 60

# Required Channel Subscriptions (ID and Invite Link)
REQUIRED_CHANNELS = [
    {"name": "Channel 1 (Anime Content)", "id": -1003144969778, "invite_link": "https://t.me/onepieceisreal144"},
    {"name": "Channel 2 (Anime Content)", "id": -1003104977687, "invite_link": "https://t.me/onepieceisreal155"},
    {"name": "Channel 3 (Anime Content)", "id": -1002965575141, "invite_link": "https://t.me/entertaining166"},
    {"name": "Channel 4 (Anime Content)", "id": -1003069758570, "invite_link": "https://t.me/anime14400"}, 
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

def create_deep_link_and_send(chat_id, content_data):
    """
    Saves the file ID and caption to the database and generates a short Deep Link.
    content_data is a dictionary: {'file_id': '...', 'caption': '...'}
    """
    try:
        db = load_database()
        short_id = generate_short_id(db)
        
        db[short_id] = content_data 
        save_database(db)

        deep_link = f"https://t.me/{BOT_USERNAME}?start={short_id}"
        
        # Inline button generation
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🚀 Click Here to View Content! 🚀", url=deep_link))

        bot.send_message(
            chat_id,
            f"✅ <b>Deep Link Generated Successfully!</b>\n\n"
            f"<b>Content Type:</b> <code>Telegram File (MKV/Video)</code>\n"
            f"<b>Attached Caption (Preview):</b> \n<code>{content_data.get('caption', 'None')}</code>\n\n"
            f"This link is <b>short</b> and <b>fully functional</b>.\n\n"
            f"Use the button below in your channel post:",
            parse_mode='HTML', 
            reply_markup=markup
        )
        
        # Also send the URL for admin to copy
        bot.send_message(chat_id, f"🔗 Deep Link URL: <code>{deep_link}</code>", parse_mode='HTML')

    except Exception as e:
        print(f"Error generating Deep Link: {e}")
        bot.send_message(chat_id, "❌ <b>Error:</b> Failed to generate Deep Link. Please check the console.", parse_mode='HTML')


# --- DELETION LOGIC ---

def schedule_deletion(chat_id, message_id, delay_seconds):
    """
    Schedules the deletion of a specific message after a given delay 
    using a background thread.
    """
    def delete_message():
        time.sleep(delay_seconds)
        try:
            bot.delete_message(chat_id, message_id)
            print(f"✅ Deleted message {message_id} in chat {chat_id} after {delay_seconds} seconds.")
        except Exception as e:
            print(f"⚠️ Could not delete message {message_id} in chat {chat_id}: {e}")

    deletion_thread = threading.Thread(target=delete_message)
    deletion_thread.daemon = True 
    deletion_thread.start()


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
            unsubscribed_channels.append(channel)
    return unsubscribed_channels

def send_final_content(chat_id, short_id):
    """
    Retrieves the content data and sends the file with the associated caption 
    and schedules it for deletion. 
    """
    try:
        db = load_database()
        content_data = db.get(short_id) 

        if not content_data or 'file_id' not in content_data:
            raise ValueError("Content data or File ID not found in the database.")
        
        file_id = content_data['file_id']
        caption = content_data.get('caption', None) # Get the original custom caption (now auto-bold HTML)

        # Send the confirmation message first
        bot.send_message(chat_id, "✅ <b>Verification Successful!</b> Fetching your file now...", parse_mode='HTML')
        
        # --- WARNING MESSAGE ---
        warning_message = bot.send_message(
            chat_id,
            "🚨 <b>SECURITY ALERT!</b> 🚨\n\n"
            "<b>This file will be automatically deleted from this chat in 30 minutes.</b>\n\n"
            "To keep the content, please <b>Forward</b> it immediately to your <i>Saved Messages</i> or another private chat/channel. The link will expire after the deletion.",
            parse_mode='HTML' 
        )
        
        # --- SEND FILE AND GET MESSAGE ID ---
        file_message = bot.send_document(
            chat_id, 
            file_id, 
            caption=caption, # The caption is already wrapped in <b>bold</b> by the input handler
            parse_mode='HTML' 
        )
        
        # --- SCHEDULE DELETION ---
        schedule_deletion(chat_id, warning_message.message_id, DELETION_TIME_SECONDS)
        schedule_deletion(chat_id, file_message.message_id, DELETION_TIME_SECONDS)
            
    except Exception as e:
        print(f"Error sending content or invalid link: {e}")
        bot.send_message(chat_id, "❌ <b>Error:</b> This link is invalid or has expired.", parse_mode='HTML')


# --- COMMAND HANDLERS ---

@bot.message_handler(commands=['start'])
def handle_start(message):
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
            "3️⃣ I will verify your subscription and instantly deliver the file to you! ✅\n\n"
            "<b>Thank you for choosing us!</b> Enjoy the content! ✨"
        )
        
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        for i, channel in enumerate(REQUIRED_CHANNELS):
            button_label = f"🔗 Channel {i+1} - View Content"
            markup.add(telebot.types.InlineKeyboardButton(button_label, url=channel['invite_link']))
            
        bot.send_message(chat_id, welcome_text, parse_mode='HTML', reply_markup=markup)
        return 

    unsubscribed_channels = get_unsubscribed_channels(chat_id)

    if not unsubscribed_channels:
        send_final_content(chat_id, payload)
    else:
        text = "⚠️ <b>Subscription Required!</b> Please subscribe to ALL the channels below to proceed, then click the '✅ I Have Subscribed' button."
        
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        for channel in unsubscribed_channels:
            button_label = f"🔗 Join Channel {REQUIRED_CHANNELS.index(channel) + 1}"
            markup.add(telebot.types.InlineKeyboardButton(button_label, url=channel['invite_link']))
        
        callback_data = f"check_{payload}"
        markup.add(telebot.types.InlineKeyboardButton("✅ I Have Subscribed", callback_data=callback_data))

        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')

# Admin Command: Deep Link Generation Mode
@bot.message_handler(commands=['generate'])
def handle_generate_command(message):
    if message.chat.id != ADMIN_ID:
        return bot.send_message(message.chat.id, "❌ <b>Error:</b> This command is for the <b>Admin Only</b>.", parse_mode='HTML')

    bot.send_message(
        ADMIN_ID,
        "✅ <b>Deep Link Generation Mode (File):</b> Please send the file (Video, MKV, or any Document) for which you want to generate a <b>Short Deep Link</b>. <i>Note: The caption will automatically be formatted as BOLD.</i>",
        parse_mode='HTML'
    )
    bot.register_next_step_handler(message, handle_file_upload)


# --- NEXT STEP HANDLERS ---

def handle_file_upload(message):
    """ Captures the file ID and asks for the caption. """
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
            parse_mode='HTML'
        )
        bot.register_next_step_handler(message, handle_caption_input, file_id)

    else:
        bot.send_message(
            ADMIN_ID, 
            "❌ <b>Error:</b> No file (MKV/Video/Document) detected. Please ensure you <b>upload it directly or forward a message that contains an actual file</b>. Send the file again.",
            parse_mode='HTML'
        )
        bot.register_next_step_handler(message, handle_file_upload)


def handle_caption_input(message, file_id):
    """ Captures the caption, automatically makes it BOLD (using HTML <b>), and generates the final deep link. """
    if message.chat.id != ADMIN_ID:
        return

    caption_text = message.text.strip() if message.text else "" 

    if not message.text:
        bot.send_message(
            ADMIN_ID, 
            "❌ <b>Error:</b> Caption was not detected as text. Please send the caption text again.",
            parse_mode='HTML'
        )
        bot.register_next_step_handler(message, handle_caption_input, file_id)
        return

    # FIX: Automatically wrap the caption in bold HTML tags (<b>)
    auto_bold_caption = f"<b>{caption_text}</b>"

    content_data = {
        'file_id': file_id,
        'caption': auto_bold_caption 
    }
    
    create_deep_link_and_send(ADMIN_ID, content_data)

# --- WEBHOOK ROUTE (Handles incoming Telegram updates) ---
@app.route('/' + BOT_TOKEN, methods=['POST'])
def get_message():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        # Process the update
        bot.process_new_updates([update])
        return "!", 200
    # Deny invalid requests
    return "Error: Invalid request content type", 400


# --- SERVER HEALTH CHECK ROUTE ---
@app.route('/', methods=['GET', 'HEAD'])
def index():
    return 'Bot is running...', 200
