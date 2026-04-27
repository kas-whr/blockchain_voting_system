#!/usr/bin/env python3
"""
Blockchain Voting System - Test Suite
Tests consensus, immutability, and vote integrity
"""

import socket
import json
import threading
import time
import hashlib
from collections import defaultdict


class AdminTester:
    def __init__(self, server_host, server_port):
        self.host = server_host
        self.port = server_port
        self.results = {}
        self.lock = threading.Lock()
        self.test_log = []
        self.candidates = []

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

    def test_1_basic_voting(self, num_votes=5):
        """Test 1: Basic voting - submit multiple votes sequentially"""
        self.log("\n" + "="*60)
        self.log("TEST 1: BASIC VOTING")
        self.log("="*60)

        if not self.candidates:
            candidates_response = self.send_request({"action": "candidates"})
            self.candidates = candidates_response.get("candidates", [])

        if not self.candidates:
            self.log("✗ No candidates available!")
            return

        for i in range(num_votes):
            voter_name = f"Test_Voter_{i}"
            response = self.send_request({
                "action": "register",
                "first_name": voter_name,
                "last_name": "Admin"
            })

            if response.get("status") == "success":
                voter_id = response["voter_id"]
                candidate = self.candidates[i % len(self.candidates)]

                vote_response = self.send_request({
                    "action": "vote",
                    "voter_id": voter_id,
                    "candidate": candidate
                })

                if vote_response.get("status") == "success":
                    self.log(f"✓ Vote {i+1}: {voter_name} voted for {candidate}")
                    with self.lock:
                        self.results[voter_id] = vote_response.get("receipt")
                else:
                    self.log(f"✗ Vote {i+1} FAILED: {vote_response.get('message')}")
            else:
                self.log(f"✗ Registration {i+1} FAILED: {response.get('message')}")

        self.log(f"\nTotal successful votes: {len(self.results)}")

    def test_2_double_voting_prevention(self):
        """Test 2: Prevent double voting by same person"""
        self.log("\n" + "="*60)
        self.log("TEST 2: DOUBLE VOTING PREVENTION")
        self.log("="*60)

        if not self.candidates:
            self.log("✗ No candidates available!")
            return

        voter_name = "Double_Voter"

        response1 = self.send_request({
            "action": "register",
            "first_name": voter_name,
            "last_name": "Test"
        })

        if response1.get("status") == "success":
            voter_id = response1["voter_id"]
            self.log(f"✓ First registration: {voter_name}")

            candidate1 = self.candidates[0]
            candidate2 = self.candidates[1] if len(self.candidates) > 1 else self.candidates[0]

            vote1 = self.send_request({
                "action": "vote",
                "voter_id": voter_id,
                "candidate": candidate1
            })

            if vote1.get("status") == "success":
                self.log(f"✓ First vote submitted for {candidate1}")

            vote2 = self.send_request({
                "action": "vote",
                "voter_id": voter_id,
                "candidate": candidate2
            })

            if vote2.get("status") == "error":
                self.log(f"✓ Double vote BLOCKED: {vote2.get('message')}")
            else:
                self.log(f"✗ SECURITY ISSUE: Double vote was allowed!")

        response2 = self.send_request({
            "action": "register",
            "first_name": voter_name,
            "last_name": "Test"
        })

        if response2.get("status") == "error":
            self.log(f"✓ Re-registration BLOCKED: {response2.get('message')}")
        else:
            self.log(f"✗ SECURITY ISSUE: Re-registration was allowed!")

    def test_3_concurrent_voting(self, num_clients=3, votes_per_client=5):
        """Test 3: Concurrent voting from multiple clients"""
        self.log("\n" + "="*60)
        self.log(f"TEST 3: CONCURRENT VOTING ({num_clients} clients, {votes_per_client} votes each)")
        self.log("="*60)

        if not self.candidates:
            candidates_response = self.send_request({"action": "candidates"})
            self.candidates = candidates_response.get("candidates", [])

        if not self.candidates:
            self.log("✗ No candidates available!")
            return

        threads = []
        start_time = time.time()

        for client_id in range(num_clients):
            t = threading.Thread(
                target=self._concurrent_voter,
                args=(client_id, votes_per_client)
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        elapsed = time.time() - start_time
        self.log(f"\n✓ Concurrent voting completed in {elapsed:.2f} seconds")
        self.log(f"  Total votes: {len(self.results)}")
        self.log(f"  Expected: {num_clients * votes_per_client}")

    def _concurrent_voter(self, client_id, num_votes):
        """Worker thread for concurrent voting"""
        if not self.candidates:
            return

        for i in range(num_votes):
            voter_name = f"Client_{client_id}_Voter_{i}"
            response = self.send_request({
                "action": "register",
                "first_name": voter_name,
                "last_name": "ConcurrentTest"
            })

            if response.get("status") == "success":
                voter_id = response["voter_id"]
                candidate = self.candidates[i % len(self.candidates)]

                vote_response = self.send_request({
                    "action": "vote",
                    "voter_id": voter_id,
                    "candidate": candidate
                })

                if vote_response.get("status") == "success":
                    with self.lock:
                        self.results[voter_id] = vote_response.get("receipt")
                    self.log(f"  [Client {client_id}] Vote {i+1}: {candidate}")

    def test_4_chain_integrity(self):
        """Test 4: Verify chain integrity"""
        self.log("\n" + "="*60)
        self.log("TEST 4: CHAIN INTEGRITY")
        self.log("="*60)

        response = self.send_request({"action": "validate"})

        if response.get("valid"):
            self.log("✓ Blockchain is VALID")
        else:
            self.log("✗ Blockchain is INVALID - Chain broken!")

        chain_response = self.send_request({"action": "chain"})
        chain = chain_response.get("chain", [])

        if len(chain) == 0:
            self.log("\n✗ WARNING: Blockchain is empty (0 blocks)")
            return

        self.log(f"\nChain Statistics:")
        self.log(f"  Total blocks: {len(chain)}")
        self.log(f"  Genesis block: ✓ (index 0, candidate: {chain[0].get('candidate')})")
        vote_blocks = len(chain) - 1
        self.log(f"  Vote blocks: {vote_blocks}")

        if vote_blocks == 0:
            self.log("\n  ℹ No votes recorded yet (only genesis block)")
            return

        self.log(f"\n  Verifying block hashes...")
        all_valid = True
        for i in range(1, len(chain)):
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
                self.log(f"  ✗ Block {i} hash mismatch!")
                all_valid = False
            else:
                candidate = block["candidate"][:20]
                self.log(f"  ✓ Block {i:3d}: {candidate:20s} - Hash valid")

        if all_valid:
            self.log("\n✓ All block hashes verified")
        else:
            self.log("\n✗ Some blocks have invalid hashes")

    def test_5_vote_deduplication(self):
        """Test 5: Verify each vote appears exactly once"""
        self.log("\n" + "="*60)
        self.log("TEST 5: VOTE DEDUPLICATION")
        self.log("="*60)

        response = self.send_request({"action": "chain"})
        chain = response.get("chain", [])

        if len(chain) <= 1:
            self.log("  ℹ No votes recorded (only genesis or empty chain)")
            return

        voter_hashes = [block["voter_id_hash"] for block in chain[1:]]

        unique_voters = len(set(voter_hashes))
        total_votes = len(voter_hashes)

        self.log(f"Total votes: {total_votes}")
        self.log(f"Unique voters: {unique_voters}")

        if unique_voters == total_votes:
            self.log("✓ NO DUPLICATES - Each voter voted exactly once")
        else:
            duplicates = total_votes - unique_voters
            self.log(f"✗ DUPLICATES FOUND: {duplicates} duplicate votes detected!")

            voter_counts = defaultdict(int)
            for voter_hash in voter_hashes:
                voter_counts[voter_hash] += 1

            for voter_hash, count in voter_counts.items():
                if count > 1:
                    self.log(f"  Voter {voter_hash[:8]}... voted {count} times")

    def test_6_results_accuracy(self):
        """Test 6: Verify voting results accuracy"""
        self.log("\n" + "="*60)
        self.log("TEST 6: RESULTS ACCURACY")
        self.log("="*60)

        results_response = self.send_request({"action": "results"})
        server_results = results_response.get("results", {})

        chain_response = self.send_request({"action": "chain"})
        chain = chain_response.get("chain", [])

        if len(chain) <= 1:
            self.log("  ℹ No votes recorded (only genesis or empty chain)")
            return

        manual_counts = defaultdict(int)
        for block in chain[1:]:
            candidate = block["candidate"]
            if candidate != "GENESIS":
                manual_counts[candidate] += 1

        self.log("Vote Counts (Server):")
        for candidate, count in sorted(server_results.items()):
            self.log(f"  {candidate}: {count} votes")

        self.log("\nVote Counts (Manual Count):")
        for candidate, count in sorted(manual_counts.items()):
            self.log(f"  {candidate}: {count} votes")

        if dict(manual_counts) == server_results:
            self.log("\n✓ Results match - Data integrity confirmed")
        else:
            self.log("\n✗ Results MISMATCH - Data integrity issue!")

    def test_7_vote_verification(self):
        """Test 7: Verify individual votes using receipts"""
        self.log("\n" + "="*60)
        self.log("TEST 7: INDIVIDUAL VOTE VERIFICATION")
        self.log("="*60)

        if not self.results:
            self.log("No votes to verify. Run other tests first.")
            return

        receipts_to_check = list(self.results.values())[:3]

        for i, receipt in enumerate(receipts_to_check):
            response = self.send_request({
                "action": "verify",
                "receipt": receipt
            })

            if response.get("valid"):
                block = response.get("block", {})
                self.log(f"✓ Vote {i+1} verified: {block.get('candidate')}")
            else:
                self.log(f"✗ Vote {i+1} NOT FOUND in blockchain")

    def run_all_tests(self):
        """Run all tests in sequence"""
        self.log("\n\n")
        self.log("╔" + "="*58 + "╗")
        self.log("║" + " BLOCKCHAIN VOTING SYSTEM - ADMIN TEST SUITE ".center(58) + "║")
        self.log("╚" + "="*58 + "╝")

        try:
            test_conn = self.send_request({"action": "candidates"})
            if test_conn.get("status") != "success":
                self.log("\n✗ FATAL: Cannot connect to server!")
                self.log(f"  Error: {test_conn.get('message')}")
                return

            self.candidates = test_conn.get("candidates", [])

            self.log("\n✓ Connected to server")
            self.log(f"  Server: {self.host}:{self.port}")
            self.log(f"  Available candidates: {len(self.candidates)}")
            for i, candidate in enumerate(self.candidates, 1):
                self.log(f"    {i}. {candidate}")

            self.test_1_basic_voting(num_votes=100)
            self.test_2_double_voting_prevention()
            self.test_3_concurrent_voting(num_clients=10, votes_per_client=20)
            self.test_4_chain_integrity()
            self.test_5_vote_deduplication()
            self.test_6_results_accuracy()
            self.test_7_vote_verification()

            self.log("\n\n" + "="*60)
            self.log("TEST SUMMARY")
            self.log("="*60)
            self.log("✓ All tests completed successfully!")
            self.log(f"  Total votes recorded: {len(self.results)}")
            self.log("="*60 + "\n")

        except Exception as e:
            self.log(f"\n✗ ERROR: {str(e)}")

    def save_test_log(self, filename="admin_test_log.txt"):
        """Save test log to file"""
        with open(filename, 'w') as f:
            f.write("\n".join(self.test_log))
        self.log(f"\n✓ Test log saved to {filename}")


if __name__ == "__main__":
    import sys

    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000

    admin = AdminTester(host, port)
    admin.run_all_tests()
    admin.save_test_log()
