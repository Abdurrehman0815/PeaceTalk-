import random
import sqlite3
import string
import smtplib
from email.message import EmailMessage
import config
import google.generativeai as genai
from flask import Flask, request, jsonify, flash,render_template, redirect, url_for, session
from twilio.rest import Client
from chat_db import init_db, log_chat, get_chat_history
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = 'your secret key'
# Initialize the database
init_db()

# Configure the Gemini API
genai.configure(api_key="AIzaSyAEarUJgZEjZT8S1O8CkxME3asf0gEDu1I")

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
    system_instruction="Develop an AI-powered chatbot designed to provide mental health and emotional support to students. The chatbot should leverage natural language understanding (NLU) to detect and respond to the emotional needs of users in a polite, friendly, and caring tone. The chatbot must be able to communicate across all Indian languages, allowing students to engage in their preferred language.Talk in a friendly manner to the students .The chatbot must be empathetic and supportive, especially when it identifies distressing or abnormal language in the conversation. When such words are detected (e.g., indicating emotional distress or a crisis), the chatbot should respond with care, gently guiding the user towards calming and positive actions. It should offer encouragement, emotional validation, always ensuring the student feels supported and understood.\n\n### **Government-Suggested Books and Resources for Mental Health:**\n\n1. **\"A Guide to Mental Health and Well-Being\"**  \n   - **Published by:** Ministry of Health and Family Welfare (MoHFW), India  \n   - **Description:** This guide offers a comprehensive understanding of mental health challenges and strategies to promote well-being. It includes coping mechanisms, stress management, and mental health care services in India.\n   - **Availability:** Can be found through MoHFW’s website.\n\n2. **\"Life Skills: A Facilitator’s Manual\"**  \n   - **Published by:** National Institute of Mental Health and Neurosciences (NIMHANS)  \n   - **Description:** This manual provides guidance on developing emotional resilience, coping with stress, and improving mental health through life skills education. It focuses on adolescents and young adults, making it suitable for students.\n   - **Availability:** Available on NIMHANS’ official website.\n\n3. **\"MindSpace: A Resource Manual for Adolescents\"**  \n   - **Published by:** National Institute of Mental Health and Neurosciences (NIMHANS)  \n   - **Description:** This resource manual offers valuable advice on emotional well-being, mental health, and coping strategies for adolescents. It includes exercises and practices that promote self-awareness and mental resilience.\n   - **Availability:** Available through NIMHANS and the Ministry of Health websites.\n\n4. **\"Counseling Techniques and Approaches: Handbook for Mental Health Practitioners\"**  \n   - **Published by:** Indian Council of Medical Research (ICMR)  \n   - **Description:** A guide for counselors and mental health practitioners, this book offers various counseling techniques, including cognitive-behavioral therapy (CBT) and solution-focused approaches. It can help in providing accurate counseling approaches via the chatbot.\n   - **Availability:** Available on the ICMR website and through affiliated institutes.\n\n5. **\"Student Stress and Well-being: A Resource Handbook\"**  \n   - **Published by:** Ministry of Education, India (Under the Manodarpan Initiative)  \n   - **Description:** A resource aimed at supporting students in managing stress and promoting mental well-being, particularly in academic environments.\n   - **Availability:** Available through the Ministry of Education’s Manodarpan portal.\n\n6. **\"Mental Health in School Settings: Guidelines for Teachers\"**  \n   - **Published by:** Central Board of Secondary Education (CBSE) and Ministry of Education  \n   - **Description:** This guide is designed for teachers to understand and promote mental health in schools, but it can also be beneficial for students who want to understand mental health and emotional regulation.\n   - **Availability:** Available via CBSE and Manodarpan websites.\n\nBy incorporating knowledge from these government-approved resources into the chatbot, it can provide credible and effective mental health support to students.\n\n\nTrain using this prompt and act as a student mental health psychiatrist. ",
)

# Initialize chat session
chat_session = model.start_chat(history=[])

# Twilio credentials
account_sid = "AC529680e9d4f6a6b2f84fc2b5ae235f93"
auth_token = "2f75963aab25d632ab3d6bf8e4367e46"
twilio_number = "+14128306050"
doctor_number = "+919344779755"

client = Client(account_sid, auth_token)

# Define abnormal words
abnormal_words = [
    "kill","killing", "die", "suicide", "self-harm", "self-injury", "overdose", "harm",
    "depression","end my life", "take my life", "commit suicide", 
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

    :param user_id: The user ID who triggered the word.
    :param triggered_word: The word that triggered the alert.
    :param user_input: The user's full input that contained the sensitive word.
    """
    # Get user details from user.db
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
    # Generate a user_id of 4 digits followed by 2 random letters
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
        msg['From'] = config.SMTP_EMAIL
        msg['To'] = recipient

        # Connect to the SMTP server
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(config.SMTP_EMAIL, config.SMTP_APP_PASSWORD)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

@app.route('/otp_fun', methods=['GET', 'POST'])
def otp_fun():
    # If OTP is in session, we are in OTP verification stage
    if 'otp_sent' in session:
        if request.method == 'POST':
            entered_otp = request.form.get('otp')

            # Check if the entered OTP matches the one in the session
            if entered_otp == session.get('otp'):
                flash('OTP verified successfully!', 'success')
                session.pop('otp', None)  # Clear the session after success
                session.pop('otp_sent', None)
                return render_template('register.html')  # Redirect to refresh the page
            else:
                flash('Invalid OTP. Please try again.', 'error')

        return render_template('combined_form.html', otp_sent=True)

    # Initial stage - email submission
    if request.method == 'POST':
        recipient_email = request.form.get('email')

        # Generate and store OTP in the session
        otp = generate_otp()
        session['otp'] = otp
        session['otp_sent'] = True
        session['email'] = recipient_email

        # Send OTP to the provided email
        subject = "Your OTP for Email Verification"
        content = f"Your One-Time Password (OTP) is: {otp}"

        if send_email(recipient_email, subject, content):
            flash('OTP sent to your email. Please check your inbox.', 'success')
            return render_template('combined_form.html', otp_sent=True)  # Render OTP form
        else:
            flash('Failed to send OTP. Try again.', 'error')

    return render_template('combined_form.html', otp_sent=False)
@app.route('/reenter_email', methods=['POST'])
def reenter_email():
    # Clear OTP and email session data
    session.pop('otp', None)
    session.pop('otp_sent', None)
    session.pop('email', None)

    # Redirect back to the email submission form
    return redirect(url_for('otp_fun'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email_id = request.form['email_id'].strip()
        phone_number = request.form['phone_number'].strip()
        password = request.form['password'].strip()

        # Check if all fields are filled
        if not name or not email_id or not phone_number or not password:
            return render_template('register.html', error="Please provide all the required information.")

        conn = sqlite3.connect('users.db')
        c = conn.cursor()

        # Generate user_id automatically
        user_id = generate_user_id()

        # Try to insert new user into the database
        try:
            c.execute('''INSERT INTO users (user_id, name, email_id, phone_number, password) 
                         VALUES (?, ?, ?, ?, ?)''', (user_id, name, email_id, phone_number, password))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('register.html', error="Email or phone number already exists.")
        conn.close()
        return redirect(url_for('login'))

    return render_template('register.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email_id = request.form['email_id'].strip()  # Changed from user_id to email_id
        password = request.form['password'].strip()

        conn = sqlite3.connect('users.db')
        c = conn.cursor()

        # Query using email_id instead of user_id
        c.execute("SELECT * FROM users WHERE email_id = ? AND password = ?", (email_id, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]  # Store the user_id in session (user[0] is user_id)
            return render_template('index.html')
        else:
            return render_template('login.html', error="Invalid email or password.")

    return render_template('login.html')


@app.route("/", methods=['GET'])
def index():
    if 'user_id' in session:
        return render_template('index.html')  # Render the chatbot interface
    else:
        return render_template('login.html')

@app.route("/chat", methods=["POST"])
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        user_input = request.json.get("message")
        if user_input is None:
            return jsonify({"error": "Invalid request"}), 400
        user_id = session['user_id']
        print(f"Received user input: {user_input} from user_id: {user_id}")
        input_lower = user_input.lower()
        # Check for abnormal words in user input
        for word in abnormal_words:  # Iterate over each word in abnormal_words
            if word in user_input.lower():  # Check if the word is in the user's input
                print(f"Abnormal word '{word}' detected. Logging trigger for user_id: {user_id}")
                # Log sensitive trigger to sense.db
                trigger_call(user_id) # Existing function to alert via call
                log_sensitive_trigger(user_id, word, user_input)  # Pass the detected word
        response = chat_session.send_message(user_input)
        model_response = response.text

        print(f"Model response: {model_response}")

        # Log chat to the database
        log_chat(user_id, user_input, model_response)

        return jsonify({"response": model_response})

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route("/chat_history", methods=["GET"])
def chat_history():
    try:
        user_id = request.args.get("user_id")

        if user_id is None:
            return jsonify({"error": "Invalid request"}), 400

        history = get_chat_history(user_id)

        return jsonify({"history": history})

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True)
