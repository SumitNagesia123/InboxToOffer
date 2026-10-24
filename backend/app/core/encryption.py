import base64
from cryptography.fernet import Fernet
from app.core.config import settings
from app.core.errors import AppException


def get_fernet_cipher() -> Fernet:
    """Returns a Fernet cipher instance initialized with the application key."""
    try:
        key = settings.OAUTH_ENCRYPTION_KEY.encode("utf-8")
        return Fernet(key)
    except Exception as e:
        raise AppException(
            message=f"Invalid OAUTH_ENCRYPTION_KEY configuration: {str(e)}",
            code="CONFIGURATION_ERROR",
        )


def encrypt_token(plain_token: str) -> str:
    """Encrypts a sensitive credential or token before persisting to database."""
    if not plain_token:
        return ""
    cipher = get_fernet_cipher()
    encrypted_bytes = cipher.encrypt(plain_token.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_token(encrypted_token: str) -> str:
    """Decrypts a persisted credential or token for runtime API consumption."""
    if not encrypted_token:
        return ""
    cipher = get_fernet_cipher()
    decrypted_bytes = cipher.decrypt(encrypted_token.encode("utf-8"))
    return decrypted_bytes.decode("utf-8")
