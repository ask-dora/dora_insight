"""
Utility functions for the Dora Insight application
Includes encryption/decryption for secure token storage
"""

import os
from cryptography.fernet import Fernet

# Encryption key for storing tokens securely
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

def generate_encryption_key() -> str:
    """Generate a new encryption key for token storage"""
    return Fernet.generate_key().decode()

def encrypt_token(token: str) -> str:
    """Encrypt a token for secure storage"""
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a token for use"""
    return fernet.decrypt(encrypted_token.encode()).decode()
