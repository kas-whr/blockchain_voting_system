"""
Secure Voting Client with Blind Signature Support

Implements token-based anonymous voting with:
- Voting token input
- Nonce generation (client-side, for anonymity)
- Vote blinding (prevents server from knowing vote)
- Blind signature submission
- Receipt generation and verification
"""

import socket
import json
import sys
import os
import time
import hashlib
from pathlib import Path
from crypto_client import RSAPublicKeyClient, CryptoClient, DigitalReceipt

HOST = None
PORT = None

current_voter_name = None
current_voter_token = None
has_voted = False


def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title):
    """Print formatted header."""
    clear_screen()
    print("=" * 60)
    print(f"  {title.center(56)}")
    print("=" * 60)
    print()


def print_menu(options):
    """Print menu options."""
    for key, value in options.items():
        print(f"  {key}. {value}")
    print()


def send_request(request):
    """Send request to server."""
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(10)
        client_socket.connect((HOST, PORT))

        client_socket.send(json.dumps(request).encode('utf-8'))

        # Receive response
        response_data = b""
        while True:
            try:
                chunk = client_socket.recv(8192)
                if not chunk:
                    break
                response_data += chunk
            except socket.timeout:
                break

        client_socket.close()

        if not response_data:
            return {"status": "error", "message": "No response from server"}

        return json.loads(response_data.decode('utf-8'))

    except socket.timeout:
        return {"status": "error", "message": "Connection timeout"}
    except ConnectionRefusedError:
        return {"status": "error", "message": "Connection refused"}
    except json.JSONDecodeError as e:
        return {"status": "error", "message": f"Invalid JSON response: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def save_receipt(receipt):
    """Save digital receipt to file."""
    try:
        os.makedirs("receipts", exist_ok=True)
        timestamp = int(time.time())
        filename = f"receipts/receipt_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(receipt, f, indent=2)

        print(f"  ✓ Receipt saved to {filename}")
        return filename
    except Exception as e:
        print(f"  ✗ Error saving receipt: {e}")
        return None


def connect_to_server():
    """Initial connection menu."""
    global HOST, PORT

    print_header("BLOCKCHAIN VOTING SYSTEM - SECURE")
    print()
    print("  1. Connect to Server")
    print("  0. Exit")
    print()

    choice = input("  Choose option: ").strip()

    if choice == "1":
        print_header("CONNECT TO SERVER")

        host = input("  Enter server IP (default: localhost): ").strip()
        HOST = host if host else "localhost"

        port_str = input("  Enter server PORT (default: 5000): ").strip()
        try:
            PORT = int(port_str) if port_str else 5000
        except ValueError:
            print("  Error: Invalid port number")
            input("  Press Enter to try again...")
            return connect_to_server()

        # Test connection
        test_request = {"action": "candidates"}
        response = send_request(test_request)

        if response.get("status") == "success":
            print_header("CONNECTED")
            print(f"  ✓ Connected to {HOST}:{PORT}")
            print()
            print(f"  Available candidates:")
            for candidate in response.get("candidates", []):
                print(f"    - {candidate}")
            print()
            input("  Press Enter to continue...")
            return True
        else:
            print_header("CONNECTION FAILED")
            print(f"  ✗ Error: {response.get('message')}")
            print()
            input("  Press Enter to try again...")
            return connect_to_server()

    elif choice == "0":
        print("  Goodbye!")
        sys.exit(0)
    else:
        print("  Invalid option")
        input("  Press Enter to try again...")
        return connect_to_server()


def submit_vote():
    """Submit vote with blind signature protocol."""
    global current_voter_token, has_voted

    if has_voted:
        print_header("ERROR")
        print("  ✗ You have already voted")
        print()
        input("  Press Enter to continue...")
        return

    print_header("SECURE VOTING - BLIND SIGNATURE PROTOCOL")
    print()

    # Step 1: Get voting token
    print("  Step 1: Authenticate with voting token")
    token = input("  Enter your voting token: ").strip()

    if not token:
        print("  ✗ Token required")
        input("  Press Enter to continue...")
        return

    # Step 2: Get server's public key for blinding
    print()
    print("  Step 2: Getting server public key...")
    key_response = send_request({"action": "public_key"})
    if key_response.get("status") != "success":
        print(f"  ✗ Error: {key_response.get('message')}")
        input("  Press Enter to continue...")
        return

    try:
        key_data = key_response.get("public_key", {})
        server_pubkey = RSAPublicKeyClient(
            N=int(key_data["N"]),
            e=int(key_data["e"])
        )
    except Exception as e:
        print(f"  ✗ Invalid public key from server: {e}")
        input("  Press Enter to continue...")
        return

    # Step 3: Get candidates
    print("  Step 3: Selecting candidate...")
    candidates_response = send_request({"action": "candidates"})

    if candidates_response.get("status") != "success":
        print(f"  ✗ Error: {candidates_response.get('message')}")
        input("  Press Enter to continue...")
        return

    candidates = candidates_response.get("candidates", [])

    print()
    print("  Available candidates:")
    for i, candidate in enumerate(candidates, 1):
        print(f"    {i}. {candidate}")

    print()
    candidate_choice = input("  Enter candidate number or name: ").strip()

    try:
        candidate_idx = int(candidate_choice) - 1
        if 0 <= candidate_idx < len(candidates):
            vote_choice = candidates[candidate_idx]
        else:
            vote_choice = candidate_choice
    except ValueError:
        vote_choice = candidate_choice

    if vote_choice not in candidates:
        print(f"  ✗ Invalid candidate")
        input("  Press Enter to continue...")
        return

    # Step 4: Generate nonce (client-side)
    print()
    print("  Step 4: Generating nonce (client-side for anonymity)...")
    nonce = os.urandom(32)  # 256-bit random nonce
    print(f"  ✓ Nonce generated (32 bytes)")

    # Step 5: Create payload and blind
    print()
    print("  Step 5: Blinding vote (preventing server from seeing choice)...")

    # Create payload: vote_choice + nonce
    vote_bytes = vote_choice.encode('utf-8')
    payload = len(vote_bytes).to_bytes(2, 'big') + vote_bytes + nonce

    try:
        # Use server public key from Step 2 for the full blind-sign flow
        crypto_client = CryptoClient(server_pubkey)

        blinded_data, blinding_factor = crypto_client.blind(payload)
        print(f"  ✓ Vote blinded")

    except Exception as e:
        print(f"  ✗ Error blinding vote: {e}")
        input("  Press Enter to continue...")
        return

    # Step 6: Request blind signature from server
    print()
    print("  Step 6: Requesting blind signature from server...")
    print("  (Server will sign without knowing your vote)")

    sig_response = send_request({
        "action": "get_blind_signature",
        "token": token,
        "blinded_data": blinded_data.hex()
    })

    if sig_response.get("status") != "success":
        print(f"  ✗ Error: {sig_response.get('message')}")
        input("  Press Enter to continue...")
        return

    blinded_signature = bytes.fromhex(sig_response.get("blinded_signature"))
    pubkey_dict = sig_response.get("public_key")

    print(f"  ✓ Received blinded signature from server")

    # Sanity-check returned key matches key used to blind payload.
    if str(server_pubkey.N) != str(pubkey_dict.get("N")) or server_pubkey.e != int(pubkey_dict.get("e")):
        print("  ✗ Server public key changed during protocol")
        input("  Press Enter to continue...")
        return

    # Step 7: Unblind signature (client-side)
    print()
    print("  Step 7: Unblinding signature (client-side)...")

    try:
        crypto_client.blinding_factor = blinding_factor
        signature = crypto_client.unblind(blinded_signature)
        print(f"  ✓ Signature unblinded")
    except Exception as e:
        print(f"  ✗ Error unblinding: {e}")
        input("  Press Enter to continue...")
        return

    # Step 8: Verify signature locally
    print()
    print("  Step 8: Verifying signature locally...")

    if not crypto_client.verify_signature(payload, signature):
        print(f"  ✗ Signature verification failed!")
        input("  Press Enter to continue...")
        return

    print(f"  ✓ Signature verified")

    # Step 9: Submit vote to blockchain
    print()
    print("  Step 9: Submitting vote to blockchain...")

    vote_response = send_request({
        "action": "vote_secured",
        "vote": vote_choice,
        "nonce": nonce.hex(),
        "signature": signature.hex()
    })

    if vote_response.get("status") != "success":
        print(f"  ✗ Error: {vote_response.get('message')}")
        input("  Press Enter to continue...")
        return

    # Step 10: Display and save receipt
    print()
    print_header("VOTE SUBMITTED SUCCESSFULLY")

    receipt = vote_response.get("receipt")
    block_index = vote_response.get("block_index")

    print(f"  ✓ Your vote has been recorded in the blockchain")
    print()
    print(f"  Digital Receipt:")
    print(f"  ─" * 40)
    print(f"  Vote Hash:     {receipt['vote_hash'][:16]}...")
    print(f"  Block Index:   {block_index}")
    print(f"  Timestamp:     {receipt['timestamp']}")
    print()
    print(f"  This receipt proves your vote was included in the blockchain")
    print(f"  without revealing who you voted for.")
    print()

    # Save receipt
    save_receipt(receipt)

    has_voted = True
    current_voter_token = token

    input("  Press Enter to continue...")


def verify_receipt():
    """Verify a saved receipt."""
    print_header("VERIFY VOTE RECEIPT")
    print()

    # Fast path: load receipt JSON and verify automatically.
    load_file = input("  Load receipt from JSON file? (y/n): ").strip().lower()
    if load_file == "y":
        receipt_path = input("  Enter receipt file path: ").strip()
        if not receipt_path:
            print("  ✗ Receipt file path is required")
            input("  Press Enter to continue...")
            return
        try:
            with open(receipt_path, "r") as f:
                saved_receipt = json.load(f)
            request = {"action": "verify_receipt"}
            if saved_receipt.get("receipt_hash"):
                request["receipt_hash"] = saved_receipt.get("receipt_hash")
            elif saved_receipt.get("vote_hash") and (saved_receipt.get("nonce_hex") or saved_receipt.get("nonce")):
                request["vote_hash"] = saved_receipt.get("vote_hash")
                request["nonce_hex"] = saved_receipt.get("nonce_hex", saved_receipt.get("nonce"))
            else:
                print("  ✗ Receipt file missing required fields")
                input("  Press Enter to continue...")
                return
            response = send_request(request)
            print_header("VERIFICATION RESULT")
            print()
            if response.get("valid"):
                block = response.get("block", {})
                print(f"  ✓ Vote found in blockchain!")
                print()
                print(f"  Block Index:   {block.get('block_index')}")
                print(f"  Block Hash:    {block.get('block_hash')[:16]}...")
                print(f"  Timestamp:     {block.get('timestamp')}")
            else:
                print(f"  ✗ Vote not found in blockchain")
                print(f"  Message: {response.get('message')}")
            print()
            input("  Press Enter to continue...")
            return
        except Exception as e:
            print(f"  ✗ Failed to read receipt file: {e}")
            input("  Press Enter to continue...")
            return

    print("  Preferred: enter one receipt hash string (receipt_hash / block_hash).")
    print("  Legacy: leave blank and use vote_hash + nonce.")
    print()
    receipt_hash = input("  Enter receipt hash: ").strip()

    request = {"action": "verify_receipt"}
    if receipt_hash:
        request["receipt_hash"] = receipt_hash
    else:
        vote_hash = input("  Enter vote hash (from receipt): ").strip()
        nonce_hex = input("  Enter nonce_hex (from receipt): ").strip()
        if not vote_hash or not nonce_hex:
            print("  ✗ Receipt hash or vote_hash+nonce required")
            input("  Press Enter to continue...")
            return
        request["vote_hash"] = vote_hash
        # Send both keys for compatibility with old/new server handlers.
        request["nonce"] = nonce_hex
        request["nonce_hex"] = nonce_hex

    response = send_request(request)

    print_header("VERIFICATION RESULT")
    print()

    if response.get("valid"):
        block = response.get("block", {})
        print(f"  ✓ Vote found in blockchain!")
        print()
        print(f"  Block Index:   {block.get('block_index')}")
        print(f"  Block Hash:    {block.get('block_hash')[:16]}...")
        print(f"  Timestamp:     {block.get('timestamp')}")
    else:
        print(f"  ✗ Vote not found in blockchain")
        print(f"  Message: {response.get('message')}")

    print()
    input("  Press Enter to continue...")


def show_blockchain():
    """Display blockchain and optionally save to file."""
    print_header("BLOCKCHAIN VIEW")
    print()

    response = send_request({"action": "blockchain"})
    if response.get("status") != "success":
        print(f"  ✗ Error: {response.get('message')}")
        print()
        input("  Press Enter to continue...")
        return

    chain = response.get("blockchain", [])
    print(f"  Total blocks: {len(chain)}")
    if len(chain) <= 1:
        print("  No vote blocks yet (only genesis).")
    else:
        print(f"  Vote blocks: {len(chain) - 1}")
        print()
        print("  Last 5 blocks:")
        for block in chain[-5:]:
            print(f"    idx={block.get('index')} cand={block.get('candidate')} hash={str(block.get('hash', ''))[:16]}...")

    print()
    save = input("  Save full blockchain to file? (y/n): ").strip().lower()
    if save == "y":
        try:
            os.makedirs("exports", exist_ok=True)
            timestamp = int(time.time())
            filename = f"exports/blockchain_{timestamp}.json"
            with open(filename, "w") as f:
                json.dump({
                    "saved_at": timestamp,
                    "length": len(chain),
                    "blockchain": chain
                }, f, indent=2)
            print(f"  ✓ Blockchain saved to {filename}")
        except Exception as e:
            print(f"  ✗ Failed to save blockchain: {e}")

    print()
    input("  Press Enter to continue...")


def show_results():
    """Display voting results."""
    print_header("VOTING RESULTS")
    print()

    response = send_request({"action": "results"})

    if response.get("status") != "success":
        print(f"  ✗ Error: {response.get('message')}")
        print()
        input("  Press Enter to continue...")
        return

    results = response.get("results", {})
    total_votes = response.get("total_votes", 0)

    if not results:
        print("  No votes yet")
    else:
        print(f"  Total votes: {total_votes}")
        print()

        for candidate, count in sorted(results.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total_votes * 100) if total_votes > 0 else 0
            bar = "█" * int(pct / 5)
            print(f"  {candidate:20} {count:3} votes [{bar:20}] {pct:5.1f}%")

    print()
    input("  Press Enter to continue...")


def validate_blockchain():
    """Validate blockchain integrity."""
    print_header("BLOCKCHAIN VALIDATION")
    print()

    response = send_request({"action": "validate"})

    if response.get("status") != "success":
        print(f"  ✗ Error: {response.get('message')}")
        print()
        input("  Press Enter to continue...")
        return

    valid = response.get("valid", False)
    errors = response.get("errors", [])

    if valid:
        print(f"  ✓ BLOCKCHAIN IS VALID")
        print()
        print(f"  ✓ All blocks are properly linked")
        print(f"  ✓ All signatures are valid")
        print(f"  ✓ No tampering detected")
    else:
        print(f"  ✗ BLOCKCHAIN IS INVALID")
        print()
        print(f"  Errors found:")
        for error in errors:
            print(f"    - {error}")

    print()
    input("  Press Enter to continue...")


def show_main_menu():
    """Main voting menu loop."""
    while True:
        print_header("BLOCKCHAIN VOTING SYSTEM - SECURE")
        print(f"  Connected to: {HOST}:{PORT}")

        if has_voted:
            print(f"  Status: ✓ VOTED")
        else:
            print(f"  Status: Ready to vote")

        print()

        options = {
            "1": "Submit Vote (Blind Signature)",
            "2": "Verify Receipt",
            "3": "See Blockchain (and export)",
            "4": "View Results",
            "5": "Validate Blockchain",
            "0": "Disconnect & Exit"
        }

        print_menu(options)

        choice = input("  Choose option: ").strip()

        if choice == "1":
            submit_vote()
        elif choice == "2":
            verify_receipt()
        elif choice == "3":
            show_blockchain()
        elif choice == "4":
            show_results()
        elif choice == "5":
            validate_blockchain()
        elif choice == "0":
            print_header("GOODBYE")
            print()
            print("  Thank you for voting!")
            print()
            break
        else:
            print("  Invalid option")
            input("  Press Enter to try again...")


def main():
    """Main entry point."""
    if connect_to_server():
        show_main_menu()


if __name__ == "__main__":
    main()
