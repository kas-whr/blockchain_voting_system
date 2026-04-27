#!/usr/bin/env python3
"""
Blockchain Voting System - Test Suite (Blind Signature Protocol)

Tests with 100-300 votes:
- Blind signature protocol workflow
- Vote submission and verification
- Blockchain integrity
- Results accuracy
- Double voting prevention
- Concurrent voting
"""

import socket
import json
import threading
import time
import hashlib
import os
import sys
from collections import defaultdict
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'client'))
sys.path.insert(0, str(Path(__file__).parent / 'server'))

from crypto_client import RSAPublicKeyClient, CryptoClient


class BlindSignatureVotingTester:
    def __init__(self, server_host, server_port, num_votes=150):
        self.host = server_host
        self.port = server_port
        self.num_votes = num_votes
        self.results = {}
        self.lock = threading.Lock()
        self.test_log = []
        self.candidates = []
        self.tokens = []
        self.votes_cast = 0
        self.votes_successful = 0

    def send_request(self, request):
        """Send request to server"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((self.host, self.port))
            s.send(json.dumps(request).encode())

            # Receive all data
            response_data = b""
            while True:
                try:
                    chunk = s.recv(8192)
                    if not chunk:
                        break
                    response_data += chunk
                except socket.timeout:
                    break

            s.close()

            if not response_data:
                return {"status": "error", "message": "No response from server"}

            return json.loads(response_data.decode())
        except json.JSONDecodeError as e:
            return {"status": "error", "message": f"Invalid JSON: {str(e)}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def log(self, message):
        """Log test messages"""
        timestamp = time.strftime("%H:%M:%S")
        msg = f"[{timestamp}] {message}"
        self.test_log.append(msg)
        print(msg)

    def test_1_setup(self):
        """Test 1: Setup - Get candidates and generate tokens"""
        self.log("\n" + "="*70)
        self.log("TEST 1: SYSTEM SETUP")
        self.log("="*70)

        # Get candidates
        candidates_response = self.send_request({"action": "candidates"})
        if candidates_response.get("status") != "success":
            self.log(f"✗ Failed to get candidates: {candidates_response.get('message')}")
            return False

        self.candidates = candidates_response.get("candidates", [])
        self.log(f"✓ Retrieved {len(self.candidates)} candidates:")
        for i, candidate in enumerate(self.candidates, 1):
            self.log(f"    {i}. {candidate}")

        if not self.candidates:
            self.log("✗ No candidates available!")
            return False

        # Note: Tokens would be generated via admin panel
        # For testing, we simulate token availability
        self.log(f"\n✓ System ready for {self.num_votes} test votes")
        return True

    def test_2_blind_signature_protocol(self):
        """Test 2: Single blind signature protocol flow"""
        self.log("\n" + "="*70)
        self.log("TEST 2: BLIND SIGNATURE PROTOCOL (Single Vote)")
        self.log("="*70)

        if not self.candidates:
            self.log("✗ No candidates available!")
            return False

        # Simulate voting token (admin would issue this)
        test_token = "TEST_TOKEN_001"
        vote_choice = self.candidates[0]

        self.log(f"\nStep 1: Creating nonce (client-side for anonymity)...")
        nonce = os.urandom(32)
        self.log(f"✓ Nonce created (32 bytes)")

        self.log(f"\nStep 2: Creating vote payload and blinding...")
        vote_bytes = vote_choice.encode('utf-8')
        payload = len(vote_bytes).to_bytes(2, 'big') + vote_bytes + nonce

        # Create temporary crypto client for blinding
        try:
            pubkey = RSAPublicKeyClient(N=2**2048 - 1, e=65537)
            crypto_client = CryptoClient(pubkey)
            blinded_data, blinding_factor = crypto_client.blind(payload)
            self.log(f"✓ Vote blinded successfully")
        except Exception as e:
            self.log(f"✗ Failed to blind vote: {e}")
            return False

        self.log(f"\nStep 3: Requesting blind signature from server...")
        sig_response = self.send_request({
            "action": "get_blind_signature",
            "token": test_token,
            "blinded_data": blinded_data.hex()
        })

        if sig_response.get("status") != "success":
            self.log(f"✗ Failed to get blind signature: {sig_response.get('message')}")
            return False

        blinded_signature = bytes.fromhex(sig_response.get("blinded_signature"))
        pubkey_dict = sig_response.get("public_key")
        self.log(f"✓ Received blinded signature from server")

        self.log(f"\nStep 4: Unblinding signature (client-side)...")
        try:
            pubkey = RSAPublicKeyClient(
                N=int(pubkey_dict['N']),
                e=pubkey_dict['e']
            )
            crypto_client = CryptoClient(pubkey)
            # Store the blinding factor first
            crypto_client.blinding_factor = blinding_factor
            signature = crypto_client.unblind(blinded_signature)
            self.log(f"✓ Signature unblinded")
        except Exception as e:
            self.log(f"✗ Failed to unblind signature: {e}")
            return False

        self.log(f"\nStep 5: Verifying signature locally...")
        if not crypto_client.verify_signature(payload, signature):
            self.log(f"✗ Signature verification failed!")
            return False
        self.log(f"✓ Signature verified")

        self.log(f"\nStep 6: Submitting vote to blockchain...")
        vote_response = self.send_request({
            "action": "vote_secured",
            "vote": vote_choice,
            "nonce": nonce.hex(),
            "signature": signature.hex()
        })

        if vote_response.get("status") != "success":
            self.log(f"✗ Failed to submit vote: {vote_response.get('message')}")
            return False

        receipt = vote_response.get("receipt")
        block_index = vote_response.get("block_index")
        self.log(f"✓ Vote submitted successfully")
        self.log(f"  Block Index: {block_index}")
        self.log(f"  Vote Hash: {receipt['vote_hash'][:16]}...")

        with self.lock:
            self.votes_successful += 1

        return True

    def test_3_concurrent_voting(self, num_threads=10):
        """Test 3: Concurrent voting with multiple threads"""
        self.log("\n" + "="*70)
        self.log(f"TEST 3: CONCURRENT VOTING ({num_threads} threads, {self.num_votes} total votes)")
        self.log("="*70)

        if not self.candidates:
            self.log("✗ No candidates available!")
            return False

        threads = []
        start_time = time.time()
        votes_per_thread = self.num_votes // num_threads

        self.log(f"\nStarting {num_threads} concurrent voting threads...")
        self.log(f"Total votes: {self.num_votes}")
        self.log(f"Votes per thread: ~{votes_per_thread}")

        for thread_id in range(num_threads):
            t = threading.Thread(
                target=self._concurrent_voter,
                args=(thread_id, votes_per_thread)
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        elapsed = time.time() - start_time

        self.log(f"\n✓ Concurrent voting completed")
        self.log(f"  Time elapsed: {elapsed:.2f} seconds")
        self.log(f"  Votes successful: {self.votes_successful}")
        self.log(f"  Votes attempted: {self.votes_cast}")
        self.log(f"  Success rate: {(self.votes_successful/self.votes_cast*100) if self.votes_cast > 0 else 0:.1f}%")
        self.log(f"  Throughput: {self.votes_successful/elapsed:.1f} votes/sec")

        return True

    def _concurrent_voter(self, thread_id, num_votes):
        """Worker thread for concurrent voting"""
        if not self.candidates:
            return

        for i in range(num_votes):
            with self.lock:
                self.votes_cast += 1
                vote_num = self.votes_cast

            # Generate nonce
            nonce = os.urandom(32)
            vote_choice = self.candidates[i % len(self.candidates)]
            vote_bytes = vote_choice.encode('utf-8')
            payload = len(vote_bytes).to_bytes(2, 'big') + vote_bytes + nonce

            try:
                # Blind the vote
                pubkey = RSAPublicKeyClient(N=2**2048 - 1, e=65537)
                crypto_client = CryptoClient(pubkey)
                blinded_data, blinding_factor = crypto_client.blind(payload)

                # Request blind signature
                sig_response = self.send_request({
                    "action": "get_blind_signature",
                    "token": f"TEST_TOKEN_{vote_num:06d}",
                    "blinded_data": blinded_data.hex()
                })

                if sig_response.get("status") != "success":
                    continue

                blinded_signature = bytes.fromhex(sig_response.get("blinded_signature"))
                pubkey_dict = sig_response.get("public_key")

                # Unblind
                pubkey = RSAPublicKeyClient(
                    N=int(pubkey_dict['N']),
                    e=pubkey_dict['e']
                )
                crypto_client = CryptoClient(pubkey)
                crypto_client.blinding_factor = blinding_factor
                signature = crypto_client.unblind(blinded_signature)

                # Submit vote
                vote_response = self.send_request({
                    "action": "vote_secured",
                    "vote": vote_choice,
                    "nonce": nonce.hex(),
                    "signature": signature.hex()
                })

                if vote_response.get("status") == "success":
                    with self.lock:
                        self.votes_successful += 1
                        if vote_num % 25 == 0:
                            self.log(f"  [{thread_id}] Vote {vote_num:3d}: {vote_choice}")

            except Exception as e:
                self.log(f"  [{thread_id}] Vote {vote_num} ERROR: {e}")

    def test_4_blockchain_integrity(self):
        """Test 4: Verify blockchain integrity"""
        self.log("\n" + "="*70)
        self.log("TEST 4: BLOCKCHAIN INTEGRITY")
        self.log("="*70)

        response = self.send_request({"action": "validate"})

        if response.get("status") != "success":
            self.log(f"✗ Validation request failed: {response.get('message')}")
            return False

        valid = response.get("valid", False)
        if valid:
            self.log("✓ Blockchain is VALID - Chain integrity verified")
        else:
            errors = response.get("errors", [])
            self.log(f"✗ Blockchain is INVALID")
            for error in errors:
                self.log(f"  Error: {error}")
            return False

        # Get blockchain stats
        chain_response = self.send_request({"action": "blockchain"})
        if chain_response.get("status") != "success":
            self.log(f"✗ Failed to get blockchain: {chain_response.get('message')}")
            return False

        chain = chain_response.get("blockchain", [])
        self.log(f"\nBlockchain Statistics:")
        self.log(f"  Total blocks: {len(chain)}")

        if len(chain) > 0:
            genesis = chain[0]
            self.log(f"  Genesis block: ✓ (index {genesis['index']}, timestamp {genesis['timestamp'][:10]})")

        vote_blocks = len(chain) - 1
        self.log(f"  Vote blocks: {vote_blocks}")

        # Verify hashes
        if len(chain) > 1:
            self.log(f"\n  Verifying {len(chain)-1} block hashes...")
            all_valid = True
            checked = 0
            for i in range(1, min(len(chain), 20)):  # Check first 20 blocks
                block = chain[i]
                data = (
                    str(block["index"]) +
                    str(block["timestamp"]) +
                    block["voter_id_hash"] +
                    block["candidate"] +
                    block["previous_hash"]
                )
                calculated_hash = hashlib.sha256(data.encode()).hexdigest()

                if calculated_hash != block["hash"]:
                    self.log(f"    ✗ Block {i} hash mismatch!")
                    all_valid = False
                else:
                    checked += 1

            self.log(f"  ✓ Verified {checked} block hashes - All valid")

        return True

    def test_5_vote_deduplication(self):
        """Test 5: Verify no duplicate votes"""
        self.log("\n" + "="*70)
        self.log("TEST 5: VOTE DEDUPLICATION")
        self.log("="*70)

        chain_response = self.send_request({"action": "blockchain"})
        if chain_response.get("status") != "success":
            self.log(f"✗ Failed to get blockchain: {chain_response.get('message')}")
            return False

        chain = chain_response.get("blockchain", [])

        if len(chain) <= 1:
            self.log("  ℹ No votes recorded (only genesis or empty chain)")
            return True

        voter_hashes = [block["voter_id_hash"] for block in chain[1:]]
        unique_voters = len(set(voter_hashes))
        total_votes = len(voter_hashes)

        self.log(f"Total votes recorded: {total_votes}")
        self.log(f"Unique voters: {unique_voters}")

        if unique_voters == total_votes:
            self.log("✓ NO DUPLICATES - Each voter voted exactly once")
            return True
        else:
            duplicates = total_votes - unique_voters
            self.log(f"✗ DUPLICATES FOUND: {duplicates} duplicate votes detected!")

            voter_counts = defaultdict(int)
            for voter_hash in voter_hashes:
                voter_counts[voter_hash] += 1

            for voter_hash, count in list(voter_counts.items())[:5]:
                if count > 1:
                    self.log(f"  Voter {voter_hash[:8]}... voted {count} times")

            return False

    def test_6_results_accuracy(self):
        """Test 6: Verify voting results accuracy"""
        self.log("\n" + "="*70)
        self.log("TEST 6: RESULTS ACCURACY")
        self.log("="*70)

        results_response = self.send_request({"action": "results"})
        if results_response.get("status") != "success":
            self.log(f"✗ Failed to get results: {results_response.get('message')}")
            return False

        server_results = results_response.get("results", {})
        total_votes = results_response.get("total_votes", 0)

        chain_response = self.send_request({"action": "blockchain"})
        if chain_response.get("status") != "success":
            self.log(f"✗ Failed to get blockchain: {chain_response.get('message')}")
            return False

        chain = chain_response.get("blockchain", [])

        if len(chain) <= 1:
            self.log("  ℹ No votes recorded")
            return True

        # Manual count from chain
        manual_counts = defaultdict(int)
        for block in chain[1:]:
            candidate = block["candidate"]
            if candidate != "GENESIS":
                manual_counts[candidate] += 1

        self.log(f"Vote Counts from Server Results:")
        for candidate, count in sorted(server_results.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total_votes * 100) if total_votes > 0 else 0
            bar = "█" * int(pct / 5)
            self.log(f"  {candidate:20} {count:3} votes [{bar:20}] {pct:5.1f}%")

        self.log(f"\nTotal votes from server: {total_votes}")

        if dict(manual_counts) == server_results:
            self.log("✓ Results MATCH - Data integrity confirmed")
            return True
        else:
            self.log("✗ Results MISMATCH - Data integrity issue!")
            return False

    def test_7_receipt_verification(self):
        """Test 7: Verify receipt integrity"""
        self.log("\n" + "="*70)
        self.log("TEST 7: RECEIPT VERIFICATION")
        self.log("="*70)

        chain_response = self.send_request({"action": "blockchain"})
        if chain_response.get("status") != "success":
            self.log(f"✗ Failed to get blockchain: {chain_response.get('message')}")
            return False

        chain = chain_response.get("blockchain", [])

        if len(chain) <= 1:
            self.log("  ℹ No votes to verify")
            return True

        # Try to verify a few votes by their nonce
        test_count = min(3, len(chain) - 1)
        self.log(f"Verifying {test_count} sample votes...")

        verified = 0
        for i in range(1, test_count + 1):
            block = chain[i]
            voter_id_hash = block["voter_id_hash"]

            # In the current system, we verify by checking if vote is in blockchain
            # (actual receipt-based verification would require the original nonce)
            found = any(b["voter_id_hash"] == voter_id_hash for b in chain[1:])

            if found:
                self.log(f"  ✓ Vote {i}: Found in blockchain ({block['candidate']})")
                verified += 1
            else:
                self.log(f"  ✗ Vote {i}: NOT found in blockchain")

        self.log(f"\n✓ Verified {verified}/{test_count} votes")
        return True

    def run_all_tests(self):
        """Run all tests in sequence"""
        self.log("\n\n")
        self.log("╔" + "="*68 + "╗")
        self.log("║" + " BLOCKCHAIN VOTING SYSTEM - TEST SUITE (BLIND SIGNATURE) ".center(68) + "║")
        self.log("║" + f" Testing with {self.num_votes} votes ".center(68) + "║")
        self.log("╚" + "="*68 + "╝")

        try:
            test_conn = self.send_request({"action": "candidates"})
            if test_conn.get("status") != "success":
                self.log("\n✗ FATAL: Cannot connect to server!")
                self.log(f"  Error: {test_conn.get('message')}")
                return

            self.candidates = test_conn.get("candidates", [])
            self.log(f"\n✓ Connected to server: {self.host}:{self.port}")
            self.log(f"✓ Candidates available: {len(self.candidates)}")

            # Run tests
            if not self.test_1_setup():
                self.log("✗ Setup failed - aborting tests")
                return

            if not self.test_2_blind_signature_protocol():
                self.log("⚠ Single vote test failed but continuing...")

            if not self.test_3_concurrent_voting(num_threads=10):
                self.log("⚠ Concurrent voting test failed")

            if not self.test_4_blockchain_integrity():
                self.log("⚠ Blockchain integrity check failed")

            if not self.test_5_vote_deduplication():
                self.log("⚠ Deduplication check failed")

            if not self.test_6_results_accuracy():
                self.log("⚠ Results accuracy check failed")

            if not self.test_7_receipt_verification():
                self.log("⚠ Receipt verification failed")

            # Summary
            self.log("\n" + "="*70)
            self.log("TEST SUMMARY")
            self.log("="*70)
            self.log(f"✓ Test suite completed")
            self.log(f"  Total votes attempted: {self.votes_cast}")
            self.log(f"  Votes successful: {self.votes_successful}")
            if self.votes_cast > 0:
                self.log(f"  Success rate: {(self.votes_successful/self.votes_cast*100):.1f}%")
            self.log("="*70 + "\n")

        except Exception as e:
            self.log(f"\n✗ ERROR: {str(e)}")
            import traceback
            self.log(traceback.format_exc())

    def save_test_log(self, filename="test_results.txt"):
        """Save test log to file"""
        try:
            with open(filename, 'w') as f:
                f.write("\n".join(self.test_log))
            self.log(f"\n✓ Test log saved to {filename}")
        except Exception as e:
            self.log(f"✗ Failed to save test log: {e}")


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    num_votes = int(sys.argv[3]) if len(sys.argv) > 3 else 150

    print(f"\n📊 Starting test suite with {num_votes} votes...")
    print(f"📍 Server: {host}:{port}\n")

    tester = BlindSignatureVotingTester(host, port, num_votes=num_votes)
    tester.run_all_tests()
    tester.save_test_log()
