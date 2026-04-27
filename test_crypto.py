#!/usr/bin/env python3
"""
Quick verification test for blind signature implementation.
Tests core crypto operations without database dependency.
"""

import sys
sys.path.insert(0, '/home/stefan/DNP/blockchain_voting_system/server')
sys.path.insert(0, '/home/stefan/DNP/blockchain_voting_system/client')

from crypto_utils import BlindSignatureScheme, generate_nonce, hash_vote_with_nonce
from crypto_client import RSAPublicKeyClient, CryptoClient

def test_blind_signatures():
    """Test RSA blind signature implementation."""
    print("=" * 60)
    print("TESTING RSA BLIND SIGNATURES")
    print("=" * 60)
    print()

    # Initialize server's blind signature scheme
    print("1. Initializing RSA blind signature scheme...")
    try:
        server = BlindSignatureScheme(key_size=2048)
        print("   ✓ RSA keypair generated (2048-bit)")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False

    # Initialize client
    print()
    print("2. Initializing client crypto...")
    try:
        pubkey = RSAPublicKeyClient(N=server.N, e=server.e)
        client = CryptoClient(pubkey)
        print("   ✓ Client initialized with server's public key")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False

    # Generate nonce
    print()
    print("3. Generating nonce (client-side)...")
    try:
        nonce = generate_nonce(32)
        print(f"   ✓ Nonce generated ({len(nonce)} bytes)")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False

    # Create vote payload
    print()
    print("4. Creating vote payload...")
    try:
        vote_choice = "Alice"
        payload = client.create_vote_payload(vote_choice, nonce)
        print(f"   ✓ Payload created ({len(payload)} bytes)")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False

    # Blind payload
    print()
    print("5. Blinding payload (client-side)...")
    try:
        blinded_data, blinding_factor = client.blind(payload)
        print(f"   ✓ Payload blinded ({len(blinded_data)} bytes)")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False

    # Server signs blinded data
    print()
    print("6. Server signing blinded data (doesn't see content!)...")
    try:
        blinded_signature = server.sign_blinded(blinded_data)
        print(f"   ✓ Blinded signature created ({len(blinded_signature)} bytes)")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False

    # Client unblinds signature
    print()
    print("7. Unblinding signature (client-side)...")
    try:
        signature = client.unblind(blinded_signature, blinding_factor)
        print(f"   ✓ Signature unblinded ({len(signature)} bytes)")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False

    # Verify signature
    print()
    print("8. Verifying signature (local verification)...")
    try:
        if client.verify_signature(payload, signature):
            print(f"   ✓ Signature verified successfully!")
        else:
            print(f"   ✗ Signature verification failed!")
            return False
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False

    # Compute vote hash for receipt
    print()
    print("9. Computing vote hash for receipt...")
    try:
        vote_hash = client.compute_vote_hash(vote_choice, nonce)
        print(f"   ✓ Vote hash: {vote_hash}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False

    # Server-side verification (also works)
    print()
    print("10. Verifying signature with server's public key...")
    try:
        if server.verify(payload, signature):
            print(f"   ✓ Signature verified by server too!")
        else:
            print(f"   ✗ Server verification failed!")
            return False
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False

    print()
    print("=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    print()
    print("Key properties verified:")
    print("  ✓ Server signed blinded data without knowing content")
    print("  ✓ Client unblinded signature successfully")
    print("  ✓ Signature is valid for original payload")
    print("  ✓ Vote hash provides cryptographic proof")
    print()

    return True


if __name__ == "__main__":
    success = test_blind_signatures()
    sys.exit(0 if success else 1)
