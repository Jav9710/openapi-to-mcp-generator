"""
Spec Encryption Module for Enterprise Security.

Provides encryption/decryption for sensitive OpenAPI specifications:
- AES-256 encryption using Fernet (symmetric)
- Key derivation from master password using PBKDF2
- Per-spec encryption keys for isolation
- Secure key storage and rotation support
"""

import base64
import hashlib
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .database import db

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Base exception for encryption errors."""
    pass


class DecryptionError(Exception):
    """Exception raised when decryption fails."""
    pass


class KeyDerivationError(Exception):
    """Exception raised when key derivation fails."""
    pass


class EncryptedSpec(db.Model):
    """Encrypted specification storage."""
    __tablename__ = "encrypted_specs"

    id = db.Column(db.Integer, primary_key=True)
    spec_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspaces.id"), nullable=True)

    # Encryption metadata
    encrypted_content = db.Column(db.LargeBinary, nullable=False)
    encryption_salt = db.Column(db.LargeBinary, nullable=False)  # For key derivation
    content_hash = db.Column(db.String(64), nullable=False)  # SHA-256 of original

    # Metadata (not encrypted)
    original_filename = db.Column(db.String(255), nullable=True)
    spec_title = db.Column(db.String(255), nullable=True)
    spec_version = db.Column(db.String(50), nullable=True)

    # Timestamps
    encrypted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    encrypted_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_accessed = db.Column(db.DateTime, nullable=True)

    # Key rotation tracking
    key_version = db.Column(db.Integer, default=1)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "spec_id": self.spec_id,
            "workspace_id": self.workspace_id,
            "original_filename": self.original_filename,
            "spec_title": self.spec_title,
            "spec_version": self.spec_version,
            "encrypted_at": self.encrypted_at.isoformat() if self.encrypted_at else None,
            "encrypted_by": self.encrypted_by,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "key_version": self.key_version,
        }


class MasterKey(db.Model):
    """Master key storage for workspace encryption."""
    __tablename__ = "master_keys"

    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey("workspaces.id"), nullable=False, unique=True)

    # Encrypted master key (encrypted with password-derived key)
    encrypted_key = db.Column(db.LargeBinary, nullable=False)
    key_salt = db.Column(db.LargeBinary, nullable=False)
    key_hash = db.Column(db.String(64), nullable=False)  # For verification

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    rotated_at = db.Column(db.DateTime, nullable=True)
    version = db.Column(db.Integer, default=1)


def derive_key(password: str, salt: bytes) -> bytes:
    """
    Derive an encryption key from a password using PBKDF2.

    Args:
        password: The password to derive the key from
        salt: Random salt for key derivation

    Returns:
        32-byte key suitable for Fernet
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,  # OWASP recommended minimum
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key


def generate_salt() -> bytes:
    """Generate a cryptographically secure random salt."""
    return os.urandom(16)


def hash_content(content: str | bytes) -> str:
    """Generate SHA-256 hash of content."""
    if isinstance(content, str):
        content = content.encode('utf-8')
    return hashlib.sha256(content).hexdigest()


def encrypt_content(content: str | bytes, password: str) -> tuple[bytes, bytes, str]:
    """
    Encrypt content using a password.

    Args:
        content: The content to encrypt (string or bytes)
        password: Password for encryption

    Returns:
        Tuple of (encrypted_content, salt, content_hash)
    """
    if isinstance(content, str):
        content = content.encode('utf-8')

    # Generate salt and derive key
    salt = generate_salt()
    key = derive_key(password, salt)

    # Encrypt
    fernet = Fernet(key)
    encrypted = fernet.encrypt(content)

    # Hash original content for integrity verification
    content_hash = hash_content(content)

    return encrypted, salt, content_hash


def decrypt_content(encrypted_content: bytes, salt: bytes, password: str) -> bytes:
    """
    Decrypt content using a password.

    Args:
        encrypted_content: The encrypted content
        salt: Salt used during encryption
        password: Password for decryption

    Returns:
        Decrypted content as bytes

    Raises:
        DecryptionError: If decryption fails
    """
    try:
        key = derive_key(password, salt)
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_content)
    except InvalidToken:
        raise DecryptionError("Invalid password or corrupted data")
    except Exception as e:
        raise DecryptionError(f"Decryption failed: {str(e)}")


def encrypt_spec(
    spec_id: str,
    content: str | bytes,
    password: str,
    workspace_id: int | None = None,
    user_id: int | None = None,
    filename: str | None = None,
    title: str | None = None,
    version: str | None = None,
) -> EncryptedSpec:
    """
    Encrypt and store an OpenAPI specification.

    Args:
        spec_id: Unique identifier for the spec
        content: The spec content to encrypt
        password: Encryption password
        workspace_id: Associated workspace ID
        user_id: User performing the encryption
        filename: Original filename
        title: Spec title
        version: Spec version

    Returns:
        Created EncryptedSpec entry
    """
    # Check if spec already exists
    existing = EncryptedSpec.query.filter_by(spec_id=spec_id).first()
    if existing:
        # Update existing
        encrypted, salt, content_hash = encrypt_content(content, password)
        existing.encrypted_content = encrypted
        existing.encryption_salt = salt
        existing.content_hash = content_hash
        existing.encrypted_at = datetime.now(timezone.utc)
        existing.encrypted_by = user_id
        existing.key_version += 1
        if filename:
            existing.original_filename = filename
        if title:
            existing.spec_title = title
        if version:
            existing.spec_version = version
        db.session.commit()

        logger.info(f"Updated encrypted spec: {spec_id}")
        return existing

    # Create new
    encrypted, salt, content_hash = encrypt_content(content, password)

    encrypted_spec = EncryptedSpec(
        spec_id=spec_id,
        workspace_id=workspace_id,
        encrypted_content=encrypted,
        encryption_salt=salt,
        content_hash=content_hash,
        original_filename=filename,
        spec_title=title,
        spec_version=version,
        encrypted_by=user_id,
    )

    db.session.add(encrypted_spec)
    db.session.commit()

    logger.info(f"Created encrypted spec: {spec_id}")
    return encrypted_spec


def decrypt_spec(spec_id: str, password: str, verify_hash: bool = True) -> str:
    """
    Decrypt a stored specification.

    Args:
        spec_id: Unique identifier for the spec
        password: Decryption password
        verify_hash: Whether to verify content hash after decryption

    Returns:
        Decrypted spec content as string

    Raises:
        DecryptionError: If decryption fails or spec not found
    """
    encrypted_spec = EncryptedSpec.query.filter_by(spec_id=spec_id).first()
    if not encrypted_spec:
        raise DecryptionError(f"Encrypted spec not found: {spec_id}")

    # Decrypt
    decrypted = decrypt_content(
        encrypted_spec.encrypted_content,
        encrypted_spec.encryption_salt,
        password
    )

    # Verify hash
    if verify_hash:
        decrypted_hash = hash_content(decrypted)
        if decrypted_hash != encrypted_spec.content_hash:
            raise DecryptionError("Content integrity check failed")

    # Update last accessed
    encrypted_spec.last_accessed = datetime.now(timezone.utc)
    db.session.commit()

    return decrypted.decode('utf-8')


def delete_encrypted_spec(spec_id: str) -> bool:
    """
    Delete an encrypted specification.

    Args:
        spec_id: Unique identifier for the spec

    Returns:
        True if deleted, False if not found
    """
    encrypted_spec = EncryptedSpec.query.filter_by(spec_id=spec_id).first()
    if not encrypted_spec:
        return False

    db.session.delete(encrypted_spec)
    db.session.commit()

    logger.info(f"Deleted encrypted spec: {spec_id}")
    return True


def list_encrypted_specs(
    workspace_id: int | None = None,
    user_id: int | None = None,
) -> list[EncryptedSpec]:
    """
    List encrypted specifications.

    Args:
        workspace_id: Filter by workspace
        user_id: Filter by user who encrypted

    Returns:
        List of EncryptedSpec entries (without decrypted content)
    """
    query = EncryptedSpec.query

    if workspace_id is not None:
        query = query.filter_by(workspace_id=workspace_id)

    if user_id is not None:
        query = query.filter_by(encrypted_by=user_id)

    return query.order_by(EncryptedSpec.encrypted_at.desc()).all()


def verify_encryption_password(spec_id: str, password: str) -> bool:
    """
    Verify if a password is correct for a spec without fully decrypting.

    Args:
        spec_id: Unique identifier for the spec
        password: Password to verify

    Returns:
        True if password is correct, False otherwise
    """
    try:
        encrypted_spec = EncryptedSpec.query.filter_by(spec_id=spec_id).first()
        if not encrypted_spec:
            return False

        # Try to decrypt - this will raise if password is wrong
        decrypt_content(
            encrypted_spec.encrypted_content,
            encrypted_spec.encryption_salt,
            password
        )
        return True
    except DecryptionError:
        return False
    except Exception:
        return False


def rotate_encryption_key(spec_id: str, old_password: str, new_password: str) -> bool:
    """
    Rotate the encryption key for a spec.

    Args:
        spec_id: Unique identifier for the spec
        old_password: Current password
        new_password: New password to use

    Returns:
        True if rotation successful, False otherwise
    """
    try:
        # Decrypt with old password
        content = decrypt_spec(spec_id, old_password)

        # Get existing record
        encrypted_spec = EncryptedSpec.query.filter_by(spec_id=spec_id).first()
        if not encrypted_spec:
            return False

        # Re-encrypt with new password
        encrypted, salt, content_hash = encrypt_content(content, new_password)

        encrypted_spec.encrypted_content = encrypted
        encrypted_spec.encryption_salt = salt
        encrypted_spec.content_hash = content_hash
        encrypted_spec.key_version += 1

        db.session.commit()

        logger.info(f"Rotated encryption key for spec: {spec_id}")
        return True

    except Exception as e:
        logger.error(f"Key rotation failed for {spec_id}: {e}")
        db.session.rollback()
        return False


def get_encryption_status(spec_id: str) -> dict | None:
    """
    Get encryption status for a spec.

    Args:
        spec_id: Unique identifier for the spec

    Returns:
        Dict with encryption status or None if not encrypted
    """
    encrypted_spec = EncryptedSpec.query.filter_by(spec_id=spec_id).first()
    if not encrypted_spec:
        return None

    return {
        "encrypted": True,
        "spec_id": spec_id,
        "encrypted_at": encrypted_spec.encrypted_at.isoformat() if encrypted_spec.encrypted_at else None,
        "key_version": encrypted_spec.key_version,
        "last_accessed": encrypted_spec.last_accessed.isoformat() if encrypted_spec.last_accessed else None,
    }
