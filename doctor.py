from flask import Flask, render_template, request
import sqlite3
from sqlite3 import Error
import google.generativeai as genai
from encrypt import decrypt_message

app = Flask(__name__)

# Configure Google Generative AI
genai.configure(api_key="AIzaSyB2FQSMPcyY1wnk7YpLlCmu-CMmKTDVKEA")

# Generation config
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

# Create the model
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction="Summarize the conversation between the user and the bot into a short and crisp paragraph. First print the main points that are took place in the conversation as three doted points.",
)

def init_db():
    """
    Initialize the database by creating the chat_logs table if it doesn't exist.
    """
    try:
        conn = sqlite3.connect('chat_logs.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            user_input TEXT NOT NULL,
            chatbot_response TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.commit()
    except Error as e:
        print(f"Error initializing database: {e}")
    finally:
        if conn:
            conn.close()

def get_chat_history(user_id):
    """
    Retrieve the chat history for a given user ID.

    :param user_id: The unique identifier for the user.
    :return: A list of tuples containing user input, chatbot response, and timestamp.
    """
    try:
        conn = sqlite3.connect('chat_logs.db')
        c = conn.cursor()
        c.execute("SELECT user_input, chatbot_response, timestamp FROM chat_logs WHERE user_id = ? ORDER BY timestamp", (user_id,))
        encrypted_chat_history = c.fetchall()
        # Decrypt messages
        chat_history = [(decrypt_message(entry[0]), decrypt_message(entry[1]), entry[2]) for entry in encrypted_chat_history]
        return chat_history
    except Error as e:
        print(f"Error retrieving chat history: {e}")
        return []
    finally:
        if conn:
            conn.close()

def summarize_chat(chat_history):
    """
    Summarize the chat history using Google AI Python SDK.

    :param chat_history: A list of tuples containing user input and chatbot response.
    :return: A summarized paragraph of the chat history.
    """
    history = []
    for entry in chat_history:
        user_input, chatbot_response, _ = entry
        history.append({
            "role": "user",
            "parts": [f"user: {user_input}\nbot: {chatbot_response}"]
        })
    
    chat_session = model.start_chat(history=history)
    response = chat_session.send_message("Summarize this conversation.")
    return response.text

@app.route('/', methods=['GET', 'POST'])
def index():
    summary = ""
    if request.method == 'POST':
        user_id = request.form['user_id']
        chat_history = get_chat_history(user_id)
        if chat_history:
            summary = summarize_chat(chat_history)
        else:
            summary = "No chat history available for this user."
    
    return render_template('hist.html', summary=summary)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
