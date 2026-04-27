"""
Voting Server with RSA Blind Signature Support

Handles:
- Blind signature requests (sign without seeing vote)
- Secured vote submissions (with signature verification)
- Results and verification requests
- Blockchain integrity validation
"""

import socket
import json
import sys
import time
from blockchain import Blockchain
from crypto_utils import BlindSignatureScheme
from tokens import TokenManager
import hashlib


class VotingServer:
    """Main voting server."""

    def __init__(self, host="0.0.0.0", port=5000, candidates_file="server/CANDIDATES.json", test_mode=False):
        """Initialize voting server."""
        self.host = host
        self.port = port
        self.candidates_file = candidates_file
        self.test_mode = test_mode
        self.candidates = []
        self.blockchain = None
        self.crypto_scheme = None
        self.token_manager = TokenManager()
        self.voting_started = False

    def load_candidates(self):
        """Load candidates from JSON file."""
        import json
        try:
            with open(self.candidates_file, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    self.candidates = [c.get("FullName", c.get("name", str(c))) for c in data]
                    return True
                else:
                    print("Error: Invalid candidates file format")
                    return False
        except FileNotFoundError:
            print(f"Error: Candidates file '{self.candidates_file}' not found")
            return False
        except json.JSONDecodeError:
            print("Error: Invalid JSON in candidates file")
            return False

    def initialize(self):
        """Initialize server components."""
        # Initialize blockchain
        try:
            self.crypto_scheme = BlindSignatureScheme()
            self.blockchain = Blockchain(crypto_scheme=self.crypto_scheme)
            print("✓ Blockchain initialized")
        except Exception as e:
            print(f"✗ Blockchain error: {e}")
            return False

        # Load candidates
        if not self.load_candidates():
            return False

        print(f"✓ Candidates loaded: {', '.join(self.candidates)}")
        return True

    def handle_request(self, request_data):
        """Handle incoming client request."""
        try:
            request = json.loads(request_data)
        except json.JSONDecodeError:
            return {"status": "error", "message": "Invalid JSON"}

        action = request.get("action")

        # ========== BLIND SIGNATURE REQUEST (Secured Mode) ==========
        if action == "get_blind_signature":
            token = request.get("token")
            blinded_data = request.get("blinded_data")

            if not token or not blinded_data:
                return {"status": "error", "message": "Missing token or blinded_data"}

            try:
                # Validate and consume token
                self.token_manager.validate_and_consume(token)

                # Decode blinded_data from hex
                blinded_bytes = bytes.fromhex(blinded_data)

                # Sign blinded data (server doesn't know what it's signing!)
                blinded_signature = self.crypto_scheme.sign_blinded(blinded_bytes)

                # Get public key numbers for client
                pubkey_numbers = self.crypto_scheme.get_public_key_numbers()

                return {
                    "status": "success",
                    "blinded_signature": blinded_signature.hex(),
                    "public_key": {
                        "N": str(pubkey_numbers["N"]),
                        "e": pubkey_numbers["e"]
                    }
                }
            except ValueError as e:
                return {"status": "error", "message": str(e)}
            except Exception as e:
                return {"status": "error", "message": f"Signing error: {e}"}

        # ========== SECURED VOTE SUBMISSION ==========
        elif action == "vote_secured":
            vote_choice = request.get("vote")
            nonce_hex = request.get("nonce")
            signature_hex = request.get("signature")

            if not vote_choice or not nonce_hex or not signature_hex:
                return {"status": "error", "message": "Missing vote, nonce, or signature"}

            if vote_choice not in self.candidates:
                return {
                    "status": "error",
                    "message": "Invalid candidate",
                    "allowed_candidates": self.candidates
                }

            try:
                # Decode nonce and signature from hex
                nonce = bytes.fromhex(nonce_hex)
                signature = bytes.fromhex(signature_hex)

                # Rebuild signed payload and verify blind signature.
                # In secured mode, the server must reject votes with invalid signatures.
                vote_bytes = vote_choice.encode('utf-8')
                payload = len(vote_bytes).to_bytes(2, 'big') + vote_bytes + nonce
                if not self.crypto_scheme.verify(payload, signature):
                    return {"status": "error", "message": "Invalid signature"}

                # Create voter ID hash from nonce (anonymous but prevents double voting)
                voter_id_hash = hashlib.sha256(nonce).hexdigest()

                # Add to blockchain
                block = self.blockchain.add_vote(voter_id_hash, vote_choice)

                if block is None:
                    return {"status": "error", "message": "Double voting detected"}

                # Compute vote hash for receipt
                vote_hash = hashlib.sha256(vote_bytes + nonce).hexdigest()

                # Create receipt
                receipt = {
                    "receipt_hash": block["hash"],
                    "vote_hash": vote_hash,
                    "nonce_hex": nonce_hex,
                    "signature_hex": signature_hex,
                    "timestamp": block["timestamp"],
                    "block_index": block["index"],
                    "mode": "secured"
                }

                return {
                    "status": "success",
                    "message": "Vote accepted",
                    "receipt": receipt,
                    "block_index": block["index"]
                }
            except ValueError as e:
                return {"status": "error", "message": str(e)}
            except Exception as e:
                return {"status": "error", "message": f"Voting error: {e}"}

        # ========== GET CANDIDATES ==========
        elif action == "candidates":
            return {
                "status": "success",
                "candidates": self.candidates
            }

        # ========== GET BLIND SIGNATURE PUBLIC KEY ==========
        elif action == "public_key":
            try:
                pubkey_numbers = self.crypto_scheme.get_public_key_numbers()
                return {
                    "status": "success",
                    "public_key": {
                        "N": str(pubkey_numbers["N"]),
                        "e": pubkey_numbers["e"]
                    }
                }
            except Exception as e:
                return {"status": "error", "message": f"Public key error: {e}"}

        # ========== ISSUE TOKENS FOR AUTOMATED TESTS ==========
        elif action == "request_test_tokens":
            if not self.test_mode:
                return {
                    "status": "error",
                    "message": "request_test_tokens is disabled (start server with --test-mode)",
                    "code": "forbidden"
                }

            count = request.get("count", 1)

            try:
                count = int(count)
            except (TypeError, ValueError):
                return {"status": "error", "message": "count must be an integer"}

            if count < 1:
                return {"status": "error", "message": "count must be >= 1"}

            try:
                tokens = self.token_manager.generate_tokens(count)
                return {
                    "status": "success",
                    "tokens": tokens,
                    "count": len(tokens)
                }
            except Exception as e:
                return {"status": "error", "message": f"Token generation error: {e}"}

        # ========== GET VOTING RESULTS ==========
        elif action == "results":
            results = self.blockchain.results()
            return {
                "status": "success",
                "results": results,
                "total_votes": self.blockchain.get_vote_count()
            }

        # ========== VERIFY RECEIPT ==========
        elif action == "verify_receipt":
            receipt_hash = request.get("receipt_hash")
            vote_hash = request.get("vote_hash")
            nonce_hex = request.get("nonce") or request.get("nonce_hex")

            if not receipt_hash and (not vote_hash or not nonce_hex):
                return {"status": "error", "message": "Missing receipt_hash or vote_hash+nonce"}

            try:
                # Recommended flow: verify by one-string receipt hash.
                if receipt_hash:
                    block = self.blockchain.verify_vote(receipt_hash)
                    if not block:
                        return {
                            "status": "error",
                            "valid": False,
                            "message": "Receipt not found in blockchain"
                        }
                    return {
                        "status": "success",
                        "valid": True,
                        "message": "Receipt verified in blockchain",
                        "block": {
                            "block_index": block["index"],
                            "block_hash": block["hash"],
                            "timestamp": block["timestamp"],
                            "candidate": block["candidate"]
                        }
                    }

                # Backward-compatible flow: verify by vote_hash + nonce.
                nonce = bytes.fromhex(nonce_hex)
                # Keep hashing path consistent with vote insertion:
                # vote_secured computes sha256(nonce).hexdigest(), then
                # Blockchain.add_vote() hashes that string once more.
                voter_id = hashlib.sha256(nonce).hexdigest()
                voter_id_hash = hashlib.sha256(voter_id.encode()).hexdigest()

                # Find block by voter_id_hash
                block = None
                for b in self.blockchain.chain:
                    if b["voter_id_hash"] == voter_id_hash:
                        block = b
                        break

                if not block:
                    return {
                        "status": "error",
                        "valid": False,
                        "message": "Vote not found in blockchain"
                    }

                # Verify that receipt vote_hash matches chain data.
                block_vote = block.get("candidate", "")
                expected_vote_hash = hashlib.sha256(
                    block_vote.encode('utf-8') + nonce
                ).hexdigest()
                if expected_vote_hash != vote_hash:
                    return {
                        "status": "error",
                        "valid": False,
                        "message": "Receipt hash mismatch"
                    }

                return {
                    "status": "success",
                    "valid": True,
                    "message": "Vote verified in blockchain",
                    "block": {
                        "block_index": block["index"],
                        "block_hash": block["hash"],
                        "timestamp": block["timestamp"],
                        "candidate": block["candidate"]
                    }
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        # ========== GET BLOCKCHAIN ==========
        elif action == "blockchain":
            try:
                chain = self.blockchain.get_chain()
                return {
                    "status": "success",
                    "blockchain": chain,
                    "length": len(chain)
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        # ========== VALIDATE BLOCKCHAIN ==========
        elif action == "validate":
            try:
                validation_result = self.blockchain.validate_chain()
                return {
                    "status": "success",
                    "valid": validation_result.get("valid", False),
                    "errors": [validation_result.get("message", "")]
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        # ========== GET STATISTICS ==========
        elif action == "statistics":
            try:
                stats = self.blockchain.get_statistics()
                token_stats = self.token_manager.get_token_stats()

                return {
                    "status": "success",
                    "votes": stats,
                    "tokens": token_stats
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    def handle_client(self, client_socket, address):
        """Handle single client connection."""
        try:
            # Receive request
            data = client_socket.recv(4096).decode('utf-8')

            if not data:
                return

            # Process request
            response = self.handle_request(data)

            # Send response
            response_json = json.dumps(response)
            client_socket.sendall(response_json.encode('utf-8'))

        except Exception as e:
            error_response = {"status": "error", "message": str(e)}
            try:
                client_socket.sendall(json.dumps(error_response).encode('utf-8'))
            except:
                pass
        finally:
            client_socket.close()

    def start(self):
        """Start voting server."""
        if not self.initialize():
            sys.exit(1)

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)

        print(f"✓ Socket server listening on {self.host}:{self.port}")
        print(f"  Loaded {len(self.candidates)} candidates")
        print()

        try:
            while True:
                client_socket, address = server_socket.accept()
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Connected by {address[0]}:{address[1]}")

                try:
                    self.handle_client(client_socket, address)
                except Exception as e:
                    print(f"Error handling client: {e}")

        except KeyboardInterrupt:
            print("\n✓ Server stopped")
        finally:
            server_socket.close()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python server.py PORT [CANDIDATES_FILE] [--test-mode]")
        print("Example (normal): python server.py 5000 server/CANDIDATES.json")
        print("Example (tests):  python server.py 5000 server/CANDIDATES.json --test-mode")
        sys.exit(1)

    try:
        port = int(sys.argv[1])
    except ValueError:
        print("Error: PORT must be an integer")
        sys.exit(1)

    args = sys.argv[2:]
    test_mode = False
    filtered_args = []
    for arg in args:
        if arg == "--test-mode":
            test_mode = True
        else:
            filtered_args.append(arg)

    candidates_file = filtered_args[0] if filtered_args else "server/CANDIDATES.json"

    if test_mode:
        print("⚠ Server started in TEST MODE: request_test_tokens is enabled")

    server = VotingServer(port=port, candidates_file=candidates_file, test_mode=test_mode)
    server.start()


if __name__ == "__main__":
    main()
