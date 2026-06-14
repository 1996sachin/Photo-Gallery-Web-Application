import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

def get_cipher():
    if not ENCRYPTION_KEY:
        return None
    # Ensure key is 32 bytes for AES-256
    key = ENCRYPTION_KEY.encode()
    if len(key) < 32:
        key = key.ljust(32, b'\0')
    elif len(key) > 32:
        key = key[:32]
    return AESGCM(key)

def encrypt_data(data: bytes) -> tuple[bytes, bytes]:
    """Encrypts data using AES-256 GCM. Returns (ciphertext, iv)."""
    cipher = get_cipher()
    if not cipher:
        return data, b''
    iv = os.urandom(12)
    ciphertext = cipher.encrypt(iv, data, None)
    return ciphertext, iv

def decrypt_data(ciphertext: bytes, iv: bytes) -> bytes:
    """Decrypts data using AES-256 GCM."""
    cipher = get_cipher()
    if not cipher or not iv:
        return ciphertext
    return cipher.decrypt(iv, ciphertext, None)
