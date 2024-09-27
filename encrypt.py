from cryptography.fernet import Fernet

# Replace the following key with the one you generated
key = b'ZYLqMQ3FvaNxI5y4hWtYxDRvsAyxZem-ObJdWVmJ1yQ='  # Ensure this is 32 URL-safe base64-encoded bytes
cipher_suite = Fernet(key)

def encrypt_message(message):
    """Encrypt a message."""
    return cipher_suite.encrypt(message.encode()).decode()

def decrypt_message(encrypted_message):
    """Decrypt a message."""
    try:
        return cipher_suite.decrypt(encrypted_message.encode()).decode()
    except Exception as e:
        print(f"Decryption error: {e}")
        raise
