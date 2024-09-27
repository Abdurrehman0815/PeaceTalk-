import sqlite3
from sqlite3 import Error
from encrypt import encrypt_message, decrypt_message

def init_db():
    """Initialize the database by creating the chat_logs table if it doesn't exist."""
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

def log_chat(user_id, user_input, chatbot_response):
    """Log chat to the database with encrypted messages."""
    try:
        conn = sqlite3.connect('chat_logs.db')
        c = conn.cursor()
        c.execute("INSERT INTO chat_logs (user_id, user_input, chatbot_response) VALUES (?, ?, ?)",
                  (user_id, encrypt_message(user_input), encrypt_message(chatbot_response)))
        conn.commit()
    except Error as e:
        print(f"Error logging chat: {e}")
    finally:
        if conn:
            conn.close()

def get_chat_history(user_id):
    """Retrieve the chat history for a given user ID."""
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
