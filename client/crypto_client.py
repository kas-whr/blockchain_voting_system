"""
Client-Side Cryptographic Operations for Anonymous Voting

Handles blinding/unblinding and signature verification on the client side.
"""

import secrets
import hashlib


class RSAPublicKeyClient:
    """
    RSA Public Key representation for client-side operations.

    Contains only public components (N, e) - no private key.
    """

    def __init__(self, N, e):
        """
        Initialize with RSA public key components.

        Args:
            N: RSA modulus (int)
            e: RSA public exponent (int, typically 65537)
        """
        self.N = N
        self.e = e
        self.key_size_bytes = (N.bit_length() + 7) // 8

    @classmethod
    def from_dict(cls, key_dict):
        """Create from dict with 'N' and 'e' keys."""
        return cls(int(key_dict['N']), int(key_dict['e']))


class CryptoClient:
    """
    Client-side cryptographic operations for blind signature voting.

    Flow:
    1. Generate nonce
    2. Create vote payload
    3. Blind payload with random factor
    4. Send token + blinded payload to server
    5. Receive blinded signature
    6. Unblind signature
    7. Verify signature locally
    8. Submit vote + nonce + signature
    """

    def __init__(self, server_pubkey):
        """
        Initialize crypto client.

        Args:
            server_pubkey: RSAPublicKeyClient instance
        """
        self.pubkey = server_pubkey

    def generate_nonce(self, length=32):
        """
        Generate random nonce for vote freshness.

        Args:
            length: Nonce length in bytes (default 32 = 256 bits)

        Returns:
            bytes: Random nonce
        """
        return secrets.token_bytes(length)

    def create_vote_payload(self, vote_choice, nonce):
        """
        Create vote payload for blinding.

        Payload format: [vote_length:2][vote_bytes][nonce_bytes]
        This format prevents ambiguity during verification.

        Args:
            vote_choice: Candidate name (str)
            nonce: Random nonce (bytes)

        Returns:
            bytes: Vote payload
        """
        vote_bytes = vote_choice.encode('utf-8')
        vote_len = len(vote_bytes).to_bytes(2, 'big')
        payload = vote_len + vote_bytes + nonce
        return payload

    def blind(self, payload_bytes, blinding_factor=None):
        """
        Blind a payload for signing.

        Blinding prevents server from knowing what it's signing.
        Formula: blinded = (payload * r^e) mod N

        Args:
            payload_bytes: Vote payload to blind (bytes)
            blinding_factor: Optional random factor (generated if not provided)

        Returns:
            tuple: (blinded_data: bytes, blinding_factor: int)
        """
        if blinding_factor is None:
            blinding_factor = secrets.randbelow(self.pubkey.N)

        # Convert payload to integer
        payload_int = int.from_bytes(payload_bytes, 'big')

        # Check payload is within valid range
        if payload_int >= self.pubkey.N:
            raise ValueError("Payload too large for RSA key size")

        # Compute r^e mod N
        r_e = pow(blinding_factor, self.pubkey.e, self.pubkey.N)

        # Blind: blinded = (payload * r^e) mod N
        blinded_int = (payload_int * r_e) % self.pubkey.N

        # Convert to bytes (padded)
        blinded_bytes = blinded_int.to_bytes(self.pubkey.key_size_bytes, 'big')

        return blinded_bytes, blinding_factor

    def unblind(self, blinded_signature, blinding_factor):
        """
        Unblind a signature received from server.

        Converts blinded signature to valid signature over original payload.
        Formula: signature = (blinded_sig * r^-1) mod N

        Args:
            blinded_signature: Signature from server (bytes)
            blinding_factor: Blinding factor used in blind() call

        Returns:
            bytes: Valid signature over original payload
        """
        # Convert blinded signature to integer
        sig_int = int.from_bytes(blinded_signature, 'big')

        # Compute modular inverse of blinding factor
        r_inv = pow(blinding_factor, -1, self.pubkey.N)

        # Unblind: signature = (blinded_sig * r^-1) mod N
        signature_int = (sig_int * r_inv) % self.pubkey.N

        # Convert to bytes (padded)
        signature_bytes = signature_int.to_bytes(self.pubkey.key_size_bytes, 'big')

        return signature_bytes

    def verify_signature(self, payload_bytes, signature):
        """
        Verify a blind signature locally.

        Verifies that signature is valid for the original payload.
        Formula: payload == signature^e mod N

        Args:
            payload_bytes: Original vote payload (bytes)
            signature: Signature to verify (bytes)

        Returns:
            bool: True if signature is valid
        """
        try:
            # Convert signature to integer
            sig_int = int.from_bytes(signature, 'big')

            # Recover payload: recovered = signature^e mod N
            recovered_int = pow(sig_int, self.pubkey.e, self.pubkey.N)

            # Convert payload to integer
            payload_int = int.from_bytes(payload_bytes, 'big')

            # Pad both for comparison (handle leading zeros)
            recovered_padded = recovered_int.to_bytes(self.pubkey.key_size_bytes, 'big')
            payload_padded = payload_int.to_bytes(self.pubkey.key_size_bytes, 'big')

            return recovered_padded == payload_padded
        except:
            return False

    def compute_vote_hash(self, vote_choice, nonce):
        """
        Compute vote hash for receipt.

        vote_hash = SHA256(vote_choice + nonce)

        Only the client knows the nonce, so only the client can
        compute and verify the vote_hash.

        Args:
            vote_choice: Candidate name (str)
            nonce: Random nonce (bytes)

        Returns:
            str: Hex-encoded SHA256 hash
        """
        vote_bytes = vote_choice.encode('utf-8')
        combined = vote_bytes + nonce
        vote_hash = hashlib.sha256(combined).hexdigest()
        return vote_hash


class DigitalReceipt:
    """Represents a digital receipt for a vote."""

    def __init__(self, vote_choice, nonce, signature, timestamp, mode="secured"):
        """
        Initialize digital receipt.

        Args:
            vote_choice: Candidate name (str)
            nonce: Random nonce used in vote (bytes)
            signature: RSA blind signature (bytes)
            timestamp: Vote timestamp (float)
            mode: Voting mode (str, default "secured")
        """
        self.vote_choice = vote_choice
        self.nonce = nonce
        self.signature = signature
        self.timestamp = timestamp
        self.mode = mode

    def compute_vote_hash(self):
        """Compute vote hash from nonce."""
        vote_bytes = self.vote_choice.encode('utf-8')
        combined = vote_bytes + self.nonce
        return hashlib.sha256(combined).hexdigest()

    def to_dict(self):
        """Convert receipt to dictionary."""
        return {
            "vote_choice": self.vote_choice,
            "vote_hash": self.compute_vote_hash(),
            "nonce_hex": self.nonce.hex(),
            "signature_hex": self.signature.hex(),
            "timestamp": self.timestamp,
            "mode": self.mode
        }

    def to_json(self):
        """Convert receipt to JSON string."""
        import json
        return json.dumps(self.to_dict(), indent=2)
