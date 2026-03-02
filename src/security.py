import base64
import hashlib
import hmac

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from src.config import settings

# Derive separate keys for encryption and HMAC from the master key
_master_bytes = settings.master_key.encode()


def _derive_key(info: bytes) -> bytes:
    """Derive a key from the master key using HKDF."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=info,
    )
    return hkdf.derive(_master_bytes)


_encryption_key = base64.urlsafe_b64encode(_derive_key(b"airlock-encryption"))
_hmac_key = _derive_key(b"airlock-hmac")
_fernet = Fernet(_encryption_key)


def encrypt(plaintext: str) -> bytes:
    """Encrypt a string using Fernet symmetric encryption."""
    return _fernet.encrypt(plaintext.encode())


def decrypt(ciphertext: bytes) -> str:
    """Decrypt Fernet-encrypted bytes back to a string."""
    return _fernet.decrypt(ciphertext).decode()


def hmac_hash(value: str) -> str:
    """Produce a deterministic HMAC-SHA256 hex digest for lookup without decryption."""
    return hmac.new(_hmac_key, value.encode(), hashlib.sha256).hexdigest()


def generate_key_material() -> bytes:
    """Generate a new random Fernet key and return it Fernet-encrypted."""
    raw_key = Fernet.generate_key()
    return _fernet.encrypt(raw_key)


def decrypt_key_material(encrypted_key: bytes) -> str:
    """Decrypt stored key material back to the raw Fernet key string."""
    return _fernet.decrypt(encrypted_key).decode()


def generate_fernet_key() -> str:
    """Generate a new Fernet key as a URL-safe base64 string."""
    return Fernet.generate_key().decode()
