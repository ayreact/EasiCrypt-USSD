import bcrypt
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
from Cryptodome.Random import get_random_bytes
import base64
import os

# Ensure AES key is loaded securely from environment
AES_KEY_BASE64 = os.getenv('AES_KEY')
if not AES_KEY_BASE64:
    raise ValueError("AES_KEY environment variable not set. Please add it to your .env file.")

try:
    AES_KEY = base64.b64decode(AES_KEY_BASE64)
except Exception as e:
    raise ValueError(f"Invalid Base64 encoding for AES_KEY: {e}")

if len(AES_KEY) != 32: # AES-256 requires a 32-byte key
    raise ValueError(f"AES_KEY must be 32 bytes long after decoding, but got {len(AES_KEY)} bytes. Please check your .env file.")

def hash_pin(pin):
    """Hashes a PIN using bcrypt."""
    return bcrypt.hashpw(pin.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_pin(pin, hashed_pin):
    """Checks if a given PIN matches a hashed PIN."""
    return bcrypt.checkpw(pin.encode('utf-8'), hashed_pin.encode('utf-8'))

def encrypt_data(data):
    """Encrypts data using AES-256 GCM mode."""
    cipher = AES.new(AES_KEY, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(pad(data.encode('utf-8'), AES.block_size))
    return base64.b64encode(cipher.nonce + tag + ciphertext).decode('utf-8')

def decrypt_data(encrypted_data):
    """Decrypts data encrypted with AES-256 GCM mode."""
    decoded_data = base64.b64decode(encrypted_data)
    nonce = decoded_data[:16]
    tag = decoded_data[16:32]
    ciphertext = decoded_data[32:]

    cipher = AES.new(AES_KEY, AES.MODE_GCM, nonce=nonce)
    decrypted_data = unpad(cipher.decrypt_and_verify(ciphertext, tag), AES.block_size)
    return decrypted_data.decode('utf-8')

def generate_random_code(length=6):
    """Generates a random numeric code."""
    import random
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])