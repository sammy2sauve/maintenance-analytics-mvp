"""
Encryption utilities — AES-256-GCM with per-user random salt + HKDF key derivation.

Every call to encrypt() generates fresh random salt (32 bytes) and nonce (12 bytes),
so two users with identical keys produce completely different ciphertexts.

The master key is loaded from the TRUESIGNAL_MASTER_KEY environment variable.
In production, set this to a securely generated 32-byte random string.
Never commit it to source control.
"""

import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

_ENV_VAR = "TRUESIGNAL_MASTER_KEY"
_DEV_FALLBACK = "dev-only-insecure-key-change-now!"  # exactly 32 chars


def _master_key() -> bytes:
    raw = os.environ.get(_ENV_VAR, _DEV_FALLBACK)
    # Pad or truncate to exactly 32 bytes
    return raw.encode()[:32].ljust(32, b"\x00")


def _derive_key(salt: bytes) -> bytes:
    """Derive a unique 256-bit AES key from the master key + per-user random salt."""
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"truesignal-api-key-v1",
    ).derive(_master_key())


def encrypt(plaintext: str) -> tuple[bytes, bytes, bytes]:
    """
    Encrypt plaintext with AES-256-GCM.

    Returns (ciphertext, salt, nonce) — all unique per call.
    Store all three in the DB; discard the plaintext immediately after.
    """
    salt = os.urandom(32)
    nonce = os.urandom(12)
    key = _derive_key(salt)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode(), None)
    return ciphertext, salt, nonce


def decrypt(ciphertext: bytes, salt: bytes, nonce: bytes) -> str:
    """
    Decrypt and return original plaintext.
    Only called server-side when the sync worker needs to call an external API.
    Never called from any endpoint that returns data to the frontend.
    """
    key = _derive_key(salt)
    return AESGCM(key).decrypt(nonce, ciphertext, None).decode()
