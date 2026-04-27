"""
Client-Side Cryptography Module

Provides client-side RSA operations for anonymous voting:
- Vote blinding (hides vote from server)
- Blind signature reception
- Signature unblinding (client gets final signature)
- Signature verification
"""

import hashlib


class RSAPublicKeyClient:
    """
    Client-side RSA public key holder.

    Stores RSA public key numbers (N, e) for blinding operations.
    Does not contain private key - safe to use on client side.
    """

    def __init__(self, N, e):
        """
        Initialize with RSA public key numbers.

        Args:
            N: RSA modulus
            e: RSA public exponent (typically 65537)
        """
        self.N = N
        self.e = e

    def blind(self, message_int, blinding_factor):
        """
        Blind a message using RSA blinding formula.

        Formula: blinded = (message * r^e) mod N

        Args:
            message_int: Message as integer
            blinding_factor: Random blinding factor

        Returns:
            int: Blinded message as integer
        """
        r_e = pow(blinding_factor, self.e, self.N)
        blinded_int = (message_int * r_e) % self.N
        return blinded_int

    def unblind(self, blinded_signature_int, blinding_factor):
        """
        Unblind a signature using modular inverse.

        Formula: signature = (blinded_sig * r^-1) mod N

        Args:
            blinded_signature_int: Signature from server (as integer)
            blinding_factor: Same factor used in blind()

        Returns:
            int: Unblinded signature as integer
        """
        r_inv = pow(blinding_factor, -1, self.N)
        signature_int = (blinded_signature_int * r_inv) % self.N
        return signature_int


class CryptoClient:
    """
    Client-side cryptographic operations for voting.

    Handles:
    - Vote blinding (prevents server from knowing vote)
    - Blind signature protocol
    - Message/signature conversion
    """

    def __init__(self, public_key):
        """
        Initialize with RSA public key.

        Args:
            public_key: RSAPublicKeyClient instance
        """
        self.public_key = public_key
        self.blinding_factor = None

    def blind(self, message_bytes):
        """
        Blind a message (vote) for anonymous signing.

        Args:
            message_bytes: Message to blind (bytes)

        Returns:
            (blinded_bytes, blinding_factor): Blinded data and factor
        """
        import secrets

        # Convert message to integer
        message_int = int.from_bytes(message_bytes, 'big')

        # Ensure message fits in RSA key
        if message_int >= self.public_key.N:
            raise ValueError("Message too large for RSA key")

        # Generate random blinding factor
        self.blinding_factor = secrets.randbelow(self.public_key.N)

        # Blind the message
        blinded_int = self.public_key.blind(message_int, self.blinding_factor)

        # Convert back to bytes
        key_size_bytes = self.public_key.N.bit_length() // 8 + 1
        blinded_bytes = blinded_int.to_bytes(key_size_bytes, 'big')

        return blinded_bytes, self.blinding_factor

    def unblind(self, blinded_signature_bytes):
        """
        Unblind a signature received from server.

        Args:
            blinded_signature_bytes: Signature from server (bytes)

        Returns:
            bytes: Final signature over original vote
        """
        if self.blinding_factor is None:
            raise ValueError("No blinding factor - call blind() first")

        # Convert signature to integer
        sig_int = int.from_bytes(blinded_signature_bytes, 'big')

        # Unblind
        signature_int = self.public_key.unblind(sig_int, self.blinding_factor)

        # Convert back to bytes
        key_size_bytes = self.public_key.N.bit_length() // 8 + 1
        signature_bytes = signature_int.to_bytes(key_size_bytes, 'big')

        return signature_bytes

    def verify_signature(self, message_bytes, signature_bytes):
        """
        Verify a blind signature over a message.

        Args:
            message_bytes: Original message (bytes)
            signature_bytes: Signature to verify (bytes)

        Returns:
            bool: True if signature is valid
        """
        try:
            # Convert to integers
            sig_int = int.from_bytes(signature_bytes, 'big')
            msg_int = int.from_bytes(message_bytes, 'big')

            # Recover message: recovered = signature^e mod N
            e = self.public_key.e
            N = self.public_key.N
            recovered_int = pow(sig_int, e, N)

            # Compare with padding to handle leading zeros
            key_size_bytes = N.bit_length() // 8 + 1
            recovered_padded = recovered_int.to_bytes(key_size_bytes, 'big')
            message_padded = msg_int.to_bytes(key_size_bytes, 'big')

            return recovered_padded == message_padded
        except:
            return False


class DigitalReceipt:
    """
    Vote receipt for verification.

    Provides:
    - Receipt generation from block hash
    - Receipt persistence (saving/loading)
    """

    def __init__(self, block_hash, voter_id=None, candidate=None, timestamp=None):
        """
        Initialize receipt.

        Args:
            block_hash: Hash of the block containing the vote
            voter_id: Voter identifier (optional, hashed for privacy)
            candidate: Candidate name (optional, shown in receipt)
            timestamp: Vote timestamp (optional)
        """
        self.block_hash = block_hash
        self.voter_id = voter_id
        self.candidate = candidate
        self.timestamp = timestamp

    def to_dict(self):
        """
        Convert receipt to dictionary.

        Returns:
            dict: Receipt data
        """
        return {
            "block_hash": self.block_hash,
            "candidate": self.candidate,
            "timestamp": self.timestamp
        }

    def save_to_file(self, filename=None):
        """
        Save receipt to file.

        Args:
            filename: Output filename (default: receipt_<hash>.txt)

        Returns:
            str: Filename where receipt was saved
        """
        if filename is None:
            filename = f"receipt_{self.block_hash[:12]}.txt"

        with open(filename, 'w') as f:
            f.write("=" * 60 + "\n")
            f.write("VOTE RECEIPT\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Block Hash (Receipt): {self.block_hash}\n")
            if self.candidate:
                f.write(f"Candidate: {self.candidate}\n")
            if self.timestamp:
                f.write(f"Timestamp: {self.timestamp}\n")
            f.write("\n" + "=" * 60 + "\n")
            f.write("Keep this receipt to verify your vote was counted.\n")
            f.write("You can verify by entering this hash in the verification menu.\n")
            f.write("=" * 60 + "\n")

        return filename
