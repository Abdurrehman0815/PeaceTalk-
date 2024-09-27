import random
import sqlite3
import string
import smtplib
from email.message import EmailMessage
import google.generativeai as genai
from flask import Flask, request, jsonify, flash, render_template, redirect, url_for, session
from twilio.rest import Client
from chat_db import init_db, log_chat, get_chat_history
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Initialize the database
init_db()

# Configure the Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Define the generation parameters
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

# Create the model
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    generation_config=generation_config,
    system_instruction=os.getenv("SYSTEM_INSTRUCTION")
)

# Initialize chat session
chat_session = model.start_chat(history=[])

# Twilio credentials
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_NUMBER")
doctor_number = os.getenv("DOCTOR_NUMBER")

client = Client(account_sid, auth_token)

# Define abnormal words
abnormal_words = [
    "kill", "killing", "die", "suicide", "self-harm", "self-injury", "overdose", "harm",
    "depression", "end my life", "take my life", "commit suicide", 
    "poison", "cut", "murder", "assault", "danger", "dangerous", "death", "die by", "end it all", 
    "end it", "not worth living", "worthless"
]

def trigger_call(user_id):
    try:
        call_message = f"Alert: User ID {user_id} has mentioned concerning words in their chat. Please check on them immediately."
        twiml_response = f'<Response><Say>{call_message}</Say><Pause length="1"/><Say>{call_message}</Say></Response>'

        # Create the call
        call = client.calls.create(
            twiml=twiml_response,
            to=doctor_number,
            from_=twilio_number
        )
        print(f"Call triggered to doctor: {call.sid}")
    except Exception as e:
        print(f"Failed to trigger call: {e}")

def create_user_table():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                     (user_id TEXT PRIMARY KEY NOT NULL,
                      name TEXT NOT NULL,
                      email_id TEXT NOT NULL,
                      phone_number TEXT UNIQUE NOT NULL,
                      password TEXT NOT NULL);''')
    conn.commit()
    conn.close()

create_user_table()

def init_sense_db():
    """
    Initialize the sense database by creating the sensitive_triggers table.
    """
    try:
        conn = sqlite3.connect('sense.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS sensitive_triggers (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               user_id TEXT NOT NULL,
               name TEXT NOT NULL,
               phone_number TEXT NOT NULL,
               triggered_word TEXT NOT NULL,
               user_input TEXT NOT NULL,
               timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
           )''')
        conn.commit()
    finally:
        if conn:
            conn.close()

# Call this during initialization
init_sense_db()

def get_user_details(user_id):
    """
    Retrieve the user's name and phone number from user.db using their user_id.
    """
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT name, phone_number FROM users WHERE user_id = ?", (user_id,))
        user_details = c.fetchone()  # This will return a tuple (name, phone_number)
        return user_details
    finally:
        if conn:
            conn.close()

def log_sensitive_trigger(user_id, triggered_word, user_input):
    """
    Log the sensitive word trigger to sense.db.
    """
    user_details = get_user_details(user_id)

    if user_details:
        name, phone_number = user_details
        try:
            conn = sqlite3.connect('sense.db')
            c = conn.cursor()
            c.execute('''INSERT INTO sensitive_triggers (user_id, name, phone_number, triggered_word, user_input)
                         VALUES (?, ?, ?, ?, ?)''',
                      (user_id, name, phone_number, triggered_word, user_input))
            conn.commit()
        finally:
            if conn:
                conn.close()
    else:
        print(f"No user details found for user_id: {user_id}")

def generate_user_id():
    digits = ''.join(random.choices(string.digits, k=4))
    letters = ''.join(random.choices(string.ascii_uppercase, k=2))
    return digits + letters

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def send_email(recipient, subject, content):
    try:
        msg = EmailMessage()
        msg.set_content(content)
        msg['Subject'] = subject
        msg['From'] = os.getenv("SMTP_EMAIL")
        msg['To'] = recipient

        with smtplib.SMTP(os.getenv("SMTP_SERVER"), int(os.getenv("SMTP_PORT"))) as server:
            server.starttls()
            server.login(os.getenv("SMTP_EMAIL"), os.getenv("SMTP_APP_PASSWORD"))
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

# Flask routes...

if __name__ == "__main__":
    app.run(debug=True)