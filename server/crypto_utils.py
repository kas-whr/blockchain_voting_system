"""
RSA Cryptography for Voting System

Simple, pure-Python RSA implementation using python-rsa library.
Perfect for academic understanding of:
- RSA key generation
- Blind signatures for anonymous voting
- Signature verification
"""

import secrets
import rsa


class BlindSignatureScheme:
    """
    RSA Blind Signature for anonymous voting.

    Academic implementation using python-rsa.
    Flow:
    1. Client blinds vote: blinded = blind(vote)
    2. Server signs blinded: sig = sign_blinded(blinded)
    3. Client unblinds: signature = unblind(sig)
    4. Anyone verifies: verify(vote, signature)

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
            self.public_key = private_key.publickey()
        else:
            # Generate new keypair
            self.public_key, self.private_key = rsa.newkeys(key_size)

    def blind(self, message_bytes, blinding_factor=None):
        """
        Blind a message using RSA blinding.

        Blinding prevents the signer from knowing what they're signing.

        Args:
            message_bytes: Message to blind (bytes)
            blinding_factor: Random factor (optional)

        Returns:
            (blinded_data: bytes, blinding_factor: int)
        """
        # Extract RSA parameters
        N = self.public_key.n
        e = self.public_key.e

        if blinding_factor is None:
            blinding_factor = secrets.randbelow(N)

        # Convert message to integer
        message_int = int.from_bytes(message_bytes, 'big')

        # Ensure message is within valid range
        if message_int >= N:
            raise ValueError("Message too large for RSA key size")

        # Blind: blinded = (message * r^e) mod N
        r_e = pow(blinding_factor, e, N)
        blinded_int = (message_int * r_e) % N

        # Convert back to bytes (pad to key size)
        key_size_bytes = self.public_key.n.bit_length() // 8 + 1
        blinded_bytes = blinded_int.to_bytes(key_size_bytes, 'big')

        return blinded_bytes, blinding_factor

    def sign_blinded(self, blinded_data):
        """
        Sign a blinded message (server-side operation).

        The server signs without knowing the actual message.

        Args:
            blinded_data: Blinded message (bytes)

        Returns:
            blinded_signature: Signature over blinded data (bytes)
        """
        # Convert blinded data to integer
        blinded_int = int.from_bytes(blinded_data, 'big')

        # Sign: signature = blinded^d mod N
        d = self.private_key.d
        N = self.private_key.n
        signature_int = pow(blinded_int, d, N)

        # Convert back to bytes
        key_size_bytes = self.private_key.n.bit_length() // 8 + 1
        signature_bytes = signature_int.to_bytes(key_size_bytes, 'big')

        return signature_bytes

    def unblind(self, blinded_signature, blinding_factor):
        """
        Unblind a signature (client-side operation).

        Converts blinded signature to valid signature over original message.

        Args:
            blinded_signature: Signature from server (bytes)
            blinding_factor: Same factor used in blind() operation

        Returns:
            signature: Valid signature over original message (bytes)
        """
        N = self.public_key.n

        # Convert blinded signature to integer
        sig_int = int.from_bytes(blinded_signature, 'big')

        # Compute modular inverse of blinding factor
        r_inv = pow(blinding_factor, -1, N)

        # Unblind: signature = (blinded_sig * r^-1) mod N
        signature_int = (sig_int * r_inv) % N

        # Convert back to bytes
        key_size_bytes = self.public_key.n.bit_length() // 8 + 1
        signature_bytes = signature_int.to_bytes(key_size_bytes, 'big')

        return signature_bytes

    def verify(self, message_bytes, signature):
        """
        Verify a blind signature.

        Anyone can verify using the public key.

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
            e = self.public_key.e
            N = self.public_key.n
            recovered_int = pow(sig_int, e, N)

            # Convert message to integer
            message_int = int.from_bytes(message_bytes, 'big')

            # Compare (with padding to handle leading zeros)
            key_size_bytes = self.public_key.n.bit_length() // 8 + 1
            recovered_padded = recovered_int.to_bytes(key_size_bytes, 'big')
            message_padded = message_int.to_bytes(key_size_bytes, 'big')

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
            "N": self.public_key.n,
            "e": self.public_key.e
        }

    def export_public_key_pem(self):
        """
        Export public key in PEM format.

        Returns:
            bytes: PEM-encoded public key
        """
        return self.public_key.save_pkcs1()
