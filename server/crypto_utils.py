"""
RSA Blind Signatures for Anonymous Voting

This module implements the cryptographic primitives for blind signature voting:
- RSA key generation and management
- Blinding/unblinding operations
- Blind signing
- Signature verification
- Nonce generation for vote freshness
"""

import secrets
import hashlib
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


class BlindSignatureScheme:
    """
    RSA Blind Signature implementation for anonymous voting.

    Flow:
    1. Client blinds vote: blinded = blind(vote)
    2. Server signs blinded data: sig = sign_blinded(blinded)
    3. Client unblinds: signature = unblind(sig)
    4. Client/Server verify: verify(vote, signature)

    Server never sees the actual vote.
    """

    def __init__(self, private_key=None, key_size=2048):
        """
        Initialize blind signature scheme.

        Args:
            private_key: Existing RSA private key (optional)
            key_size: RSA key size in bits (default 2048)
        """
        if private_key:
            self.private_key = private_key
        else:
            # Generate new keypair
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=default_backend()
            )

        self.public_key = self.private_key.public_key()

        # Extract RSA parameters for blind signature math
        self.N = self.public_key.public_numbers().n  # Modulus
        self.e = self.public_key.public_numbers().e  # Public exponent
        self.d = self.private_key.private_numbers().d  # Private exponent
        self.key_size_bytes = self.public_key.key_size // 8  # e.g., 256 bytes for 2048-bit

    def blind(self, message_bytes, blinding_factor=None):
        """
        Blind a message using RSA blinding.

        Blinding prevents the signer from knowing what they're signing.
        Formula: blinded = (message * r^e) mod N

        Args:
            message_bytes: Message to blind (bytes)
            blinding_factor: Random factor (optional, generated if not provided)

        Returns:
            (blinded_data: bytes, blinding_factor: int)
        """
        if blinding_factor is None:
            blinding_factor = secrets.randbelow(self.N)

        # Convert message to integer
        message_int = int.from_bytes(message_bytes, 'big')

        # Ensure message is within valid range
        if message_int >= self.N:
            raise ValueError("Message too large for RSA key size")

        # Blind: blinded = (message * r^e) mod N
        r_e = pow(blinding_factor, self.e, self.N)
        blinded_int = (message_int * r_e) % self.N

        # Convert back to bytes (pad to key size)
        blinded_bytes = blinded_int.to_bytes(self.key_size_bytes, 'big')

        return blinded_bytes, blinding_factor

    def sign_blinded(self, blinded_data):
        """
        Sign a blinded message (server-side operation).

        The server signs without knowing the actual message.
        Formula: signature = blinded^d mod N

        Args:
            blinded_data: Blinded message (bytes)

        Returns:
            blinded_signature: Signature over blinded data (bytes)
        """
        # Convert blinded data to integer
        blinded_int = int.from_bytes(blinded_data, 'big')

        # Sign: signature = blinded^d mod N
        signature_int = pow(blinded_int, self.d, self.N)

        # Convert back to bytes
        signature_bytes = signature_int.to_bytes(self.key_size_bytes, 'big')

        return signature_bytes

    def unblind(self, blinded_signature, blinding_factor):
        """
        Unblind a signature (client-side operation).

        Converts blinded signature to valid signature over original message.
        Formula: signature = (blinded_sig * r^-1) mod N

        Args:
            blinded_signature: Signature from server (bytes)
            blinding_factor: Same factor used in blind() operation

        Returns:
            signature: Valid signature over original message (bytes)
        """
        # Convert blinded signature to integer
        sig_int = int.from_bytes(blinded_signature, 'big')

        # Compute modular inverse of blinding factor
        # Python 3.8+ supports pow(a, -1, n) for modular inverse
        r_inv = pow(blinding_factor, -1, self.N)

        # Unblind: signature = (blinded_sig * r^-1) mod N
        signature_int = (sig_int * r_inv) % self.N

        # Convert back to bytes
        signature_bytes = signature_int.to_bytes(self.key_size_bytes, 'big')

        return signature_bytes

    def verify(self, message_bytes, signature):
        """
        Verify a blind signature (anyone can verify).

        Verifies that signature is valid for message.
        Formula: message == signature^e mod N

        Args:
            message_bytes: Original message (bytes)
            signature: Signature to verify (bytes)

        Returns:
            bool: True if signature is valid
        """
        try:
            # Convert signature to integer
            sig_int = int.from_bytes(signature, 'big')

            # Recover message: recovered = signature^e mod N
            recovered_int = pow(sig_int, self.e, self.N)

            # Convert message to integer
            message_int = int.from_bytes(message_bytes, 'big')

            # Compare (with padding to handle leading zeros)
            recovered_padded = recovered_int.to_bytes(self.key_size_bytes, 'big')
            message_padded = message_int.to_bytes(self.key_size_bytes, 'big')

            # For simple message recovery to work, pad the original message too
            # In production, use proper padding schemes like PKCS#1 v2.1
            return recovered_padded == message_padded
        except:
            return False

    def get_public_key_numbers(self):
        """
        Export public key numbers for transmission to client.

        Returns:
            dict: {"N": modulus, "e": exponent}
        """
        return {
            "N": self.N,
            "e": self.e
        }

    def export_public_key_pem(self):
        """
        Export public key in PEM format.

        Returns:
            bytes: PEM-encoded public key
        """
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )


def generate_nonce(length=32):
    """
    Generate a cryptographically secure random nonce.

    The nonce is used to:
    - Ensure vote freshness
    - Prevent replay attacks
    - Prove ownership of receipt (only client knows nonce)

    Args:
        length: Nonce length in bytes (default 32 = 256 bits)

    Returns:
        bytes: Random nonce
    """
    return secrets.token_bytes(length)


def hash_vote_with_nonce(vote_choice, nonce):
    """
    Hash vote choice with nonce for receipt verification.

    Used to create vote_hash in receipt. Only client can verify because
    only client knows the nonce.

    Args:
        vote_choice: Candidate name (str)
        nonce: Random nonce (bytes)

    Returns:
        str: Hex-encoded SHA-256 hash
    """
    vote_bytes = vote_choice.encode('utf-8')
    combined = vote_bytes + nonce
    vote_hash = hashlib.sha256(combined).hexdigest()
    return vote_hash


def create_payload_for_blinding(vote_choice, nonce):
    """
    Create the payload that will be blinded and signed.

    Payload = vote_choice + nonce (as bytes)

    Args:
        vote_choice: Candidate name (str)
        nonce: Random nonce (bytes)

    Returns:
        bytes: Payload ready for blinding
    """
    vote_bytes = vote_choice.encode('utf-8')
    # Prefix with length to avoid ambiguity
    payload = len(vote_bytes).to_bytes(2, 'big') + vote_bytes + nonce
    return payload


def verify_payload(payload_bytes, vote_choice, nonce):
    """
    Verify that a payload contains the expected vote and nonce.

    Args:
        payload_bytes: Original payload (bytes)
        vote_choice: Expected candidate name (str)
        nonce: Expected nonce (bytes)

    Returns:
        bool: True if payload matches
    """
    vote_bytes = vote_choice.encode('utf-8')
    expected_payload = len(vote_bytes).to_bytes(2, 'big') + vote_bytes + nonce
    return payload_bytes == expected_payload


# Key persistence helper
def serialize_private_key(private_key, password=None):
    """
    Serialize RSA private key to PEM format (for database storage).

    Args:
        private_key: RSA private key
        password: Optional password for encryption (bytes)

    Returns:
        bytes: PEM-encoded private key
    """
    from cryptography.hazmat.primitives import serialization

    if password:
        encryption = serialization.BestAvailableEncryption(password)
    else:
        encryption = serialization.NoEncryption()

    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption
    )


def deserialize_private_key(pem_data, password=None):
    """
    Deserialize RSA private key from PEM format.

    Args:
        pem_data: PEM-encoded private key (bytes)
        password: Optional password for decryption (bytes)

    Returns:
        private_key: RSA private key object
    """
    from cryptography.hazmat.primitives import serialization

    return serialization.load_pem_private_key(
        pem_data,
        password=password,
        backend=default_backend()
    )
