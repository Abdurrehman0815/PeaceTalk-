# Peace Talk

## Overview
Peace Talk is a mental health chatbot designed for students, utilizing official government and national mental health data through the Gemini API. It provides multi-language support, voice input, and detects harmful behavior, automatically notifying childcare services with the user ID for review. Encrypted chat data is summarized securely for healthcare professionals, facilitating timely intervention. Additionally, the chatbot offers simple word games to help users shift their focus in distressing moments, making it an interactive and accessible mental health support tool.


## Prototype Video

https://github.com/user-attachments/assets/c7045262-d021-43c0-8bef-116df41729b1



## Project Structure

- **`app.py`**: The main file to run the project.
- **`.env`** and **`config.py`**: Used for storing API credentials and SMTP mail credentials.
- **`encrypt.py`**: Handles encryption and decryption of user messages and chatbot responses using the AES algorithm.
- **`chat_db.py`** and **`chat_logs.db`**: Used for saving encrypted chat data.
- **`users.db`**: Stores user information such as username, email ID, and password.
- **`sense.db`**: Stores sensitive words used in chats (e.g., "killing," "suicide," "die").
- **`helpline.py`**: Allows helplines to access user input and chatbot responses when sensitive words are detected in the chats, using the unique user ID.
- **`static/`** and **`templates/`**: Directories used for storing HTML files used in the project.

## Features
- Multi-language support
- Voice input for accessibility
- Harmful behavior detection and automatic notifications
- Secure encrypted chat storage and healthcare summarization
- Interactive word games for distress relief

