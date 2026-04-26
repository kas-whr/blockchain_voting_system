#!/usr/bin/env python3
"""
Diagnostic script to debug blockchain initialization issues
"""

import socket
import json
import sys

def test_connection(host, port):
    """Test if server is running"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((host, port))
        s.close()
        return True
    except:
        return False

def send_request(host, port, request):
    """Send request to server"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect((host, port))
        s.send(json.dumps(request).encode())

        # Receive all data (handle large responses)
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

def diagnose(host, port):
    print("\n" + "="*60)
    print("BLOCKCHAIN DIAGNOSTIC TOOL")
    print("="*60)

    # Test 1: Connection
    print("\n[TEST 1] Server Connection")
    print("-" * 60)
    if test_connection(host, port):
        print(f"✓ Server is running at {host}:{port}")
    else:
        print(f"✗ FAILED: Cannot connect to {host}:{port}")
        print("  Action: Start server first")
        print(f"  Command: python server.py {port} CANDIDATES.json")
        return False

    # Test 2: Get candidates
    print("\n[TEST 2] Candidates Loaded")
    print("-" * 60)
    resp = send_request(host, port, {"action": "candidates"})
    if resp.get("status") == "success":
        candidates = resp.get("candidates", [])
        print(f"✓ Server loaded {len(candidates)} candidates")
        for i, c in enumerate(candidates[:3], 1):
            print(f"  {i}. {c}")
        if len(candidates) > 3:
            print(f"  ... and {len(candidates) - 3} more")
    else:
        print(f"✗ FAILED: {resp.get('message')}")
        return False

    # Test 3: Get blockchain chain
    print("\n[TEST 3] Blockchain Chain Status")
    print("-" * 60)
    resp = send_request(host, port, {"action": "chain"})
    if resp.get("status") == "success":
        chain = resp.get("chain", [])
        print(f"  Total blocks in chain: {len(chain)}")

        if len(chain) == 0:
            print("  ✗ ERROR: Chain is EMPTY (should have genesis block)")
            print("\n  DIAGNOSIS:")
            print("  ├─ Blockchain not initialized on server")
            print("  ├─ Possible causes:")
            print("  │  1. Server crashed during startup")
            print("  │  2. blockchain.py has an error")
            print("  │  3. Blockchain instance not created globally")
            print("  └─ ACTION: Restart server and check for errors")
            return False

        elif len(chain) == 1:
            print(f"  ✓ Genesis block exists")
            print(f"    Index: {chain[0]['index']}")
            print(f"    Candidate: {chain[0]['candidate']}")
            print(f"    Hash: {chain[0]['hash'][:16]}...")
            print("\n  ℹ No votes recorded yet (only genesis block)")
            print("  This is normal - votes will be added as clients submit them")
            return True

        else:
            print(f"  ✓ Chain has {len(chain)} blocks (1 genesis + {len(chain)-1} votes)")
            print(f"    Genesis: {chain[0]['candidate']} (index 0)")
            for i in range(1, min(4, len(chain))):
                print(f"    Block {i}: {chain[i]['candidate']}")
            if len(chain) > 4:
                print(f"    ... and {len(chain) - 4} more blocks")
            return True
    else:
        print(f"✗ FAILED: {resp.get('message')}")
        return False

    # Test 4: Validate chain
    print("\n[TEST 4] Chain Validation")
    print("-" * 60)
    resp = send_request(host, port, {"action": "validate"})
    if resp.get("status") == "success":
        valid = resp.get("valid")
        if valid:
            print("✓ Blockchain is VALID")
        else:
            print("✗ Blockchain is INVALID (corrupted)")
    else:
        print(f"✗ FAILED: {resp.get('message')}")

    # Test 5: Try submitting a vote
    print("\n[TEST 5] Vote Submission Test")
    print("-" * 60)

    # Register
    reg_resp = send_request(host, port, {
        "action": "register",
        "first_name": "Diagnostic",
        "last_name": "Test"
    })

    if reg_resp.get("status") == "success":
        voter_id = reg_resp["voter_id"]
        print(f"✓ Registration successful")
        print(f"  Voter ID: {voter_id}")

        # Vote
        vote_resp = send_request(host, port, {
            "action": "vote",
            "voter_id": voter_id,
            "candidate": candidates[0] if candidates else "Test"
        })

        if vote_resp.get("status") == "success":
            print(f"✓ Vote submitted successfully")
            print(f"  Receipt: {vote_resp['receipt'][:16]}...")

            # Check if vote was recorded
            chain_resp = send_request(host, port, {"action": "chain"})
            new_chain = chain_resp.get("chain", [])
            if len(new_chain) > len(chain):
                print(f"✓ Vote recorded in blockchain (chain now has {len(new_chain)} blocks)")
            else:
                print(f"✗ Vote NOT recorded (chain still has {len(new_chain)} blocks)")
        else:
            print(f"✗ Vote failed: {vote_resp.get('message')}")
    else:
        print(f"✗ Registration failed: {reg_resp.get('message')}")

    # Summary
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    print("\n✓ All systems operational")
    print("  - Server is running")
    print("  - Blockchain is initialized")
    print("  - Votes can be submitted")
    print("\nNote: Empty blockchain is normal on fresh server")
    print("      Votes will accumulate as clients submit them")

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000

    diagnose(host, port)
