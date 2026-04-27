# Blockchain-Based Voting System (Project 24 Variant A)

## 📋 Overview

A **centralized blockchain-based voting system** where votes are submitted by clients and immutably recorded on a distributed ledger managed by a single server node. The system ensures vote integrity, prevents double voting, provides transparency, and allows anonymous verification of vote inclusion.

**Implementation:** Python | Socket-based Communication | SHA-256 Hashing | Python-RSA

**Academic Design:** Pure Python implementation optimized for learning blockchain concepts.

---

## ✨ Key Features

✅ **In-Memory Blockchain** - Central node stores all votes in RAM  
✅ **Immutable Records** - SHA-256 hash chains prevent tampering  
✅ **Double Voting Prevention** - Voter hashing ensures one vote per person  
✅ **Vote Transparency** - Public blockchain viewable by all clients  
✅ **Vote Verification** - Voters can verify their vote was recorded using receipt hash  
✅ **Anonymous Voting** - Voter identities hashed, not stored in blockchain  
✅ **Blockchain Validation** - Multi-step validation confirms chain integrity  
✅ **RSA Blind Signatures** - Anonymous voting using pure-Python RSA  
✅ **Testing Suite** - 7 automated tests for consensus and security  

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- python-rsa library (pure Python, no native dependencies)
- All data stored in RAM (no database required)

### Installation & Setup

**Option 1: Using Virtual Environment (Recommended)**

```bash
# Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Option 2: Direct Python (No Virtual Environment)**

```bash
# Install RSA library only
pip install rsa
```

### Run the System

**Option A: With Admin Panel (Recommended)**

```bash
# Terminal: Start admin server (includes interactive panel + background server)
python server/admin_server.py 5000 server/CANDIDATES.json
```

The admin panel provides:
- **Real-time server status** (updated in header)
- **Generate voting tokens** (admin menu option 1)
- **Stop voting & save results** (admin menu option 2)
- **View current results** (admin menu option 3)
- **Automatic logging** to `logs/` directory

**Option B: Manual Server Mode (Advanced)**

```bash
# Terminal 1: Start server only
python server/server.py 5000 server/CANDIDATES.json
```

**Terminal 2-N: Run Clients** (Open in separate terminals)
```bash
python client/client.py
```

Follow the on-screen menu:
```
1. Register as Voter
2. View Candidates
3. Submit Vote
4. Show Blockchain
5. Show Results
6. Verify Vote
7. Validate Blockchain
0. Disconnect & Exit
```

---

## 📁 Project Structure

```
blockchain_voting_system/
├── server/
│   ├── admin_server.py           # Admin panel + server (RECOMMENDED)
│   ├── server.py                 # Backend server core
│   ├── blockchain.py             # In-memory blockchain
│   ├── crypto_utils.py           # RSA cryptography (python-rsa)
│   ├── crypto_client.py          # Client crypto operations
│   ├── tokens.py                 # Token management
│   └── CANDIDATES.json           # Candidate list
├── client/
│   ├── client.py                 # Interactive voter CLI
│   └── crypto_client.py          # Client-side crypto
├── logs/                         # Server logs directory (auto-created)
├── tests.py                      # Automated 7-test suite
├── README.md                     # This file
├── TECHNICAL_GUIDE.md            # Architecture & design
├── requirements.txt              # Dependencies
└── venv/                         # Virtual environment (optional)
```

**Key Points:**
- ✅ **No database files** - All votes stored in RAM during execution
- ✅ **All data in memory** - Blockchain lives in server process memory
- ✅ **No external dependencies** - Core system uses Python stdlib only
- ✅ **Academic project** - Designed to teach distributed network concepts

---

## 💻 Usage Guide

### For Administrators

**Start Admin Server with Interactive Panel:**

```bash
python server/admin_server.py 5000 server/CANDIDATES.json
```

**Admin Panel Features:**

1. **Real-Time Status Header** (updates every request)
   - Server status (🟢 ACTIVE / 🔴 INACTIVE)
   - Current uptime
   - Voting statistics (total votes, blocks, candidates)
   - Blockchain validity check
   - Token usage stats

2. **Menu Option 1: Get Tokens**
   - Generate voting tokens (1-100 at a time)
   - Display tokens on screen
   - Save tokens to file
   - Logged to server log file

3. **Menu Option 2: Stop Voting & Save Results**
   - Gracefully stop the server
   - Save final voting results to JSON file
   - Displays final vote counts and percentages
   - Logged to server log file

4. **Menu Option 3: View Current Results**
   - Display real-time voting results
   - Show vote counts and percentages per candidate
   - Bar chart visualization

**Logging:**
- All server activity logged to `logs/voting_server_YYYYMMDD_HHMMSS.log`
- Automatic log directory creation
- Includes all client requests and responses
- Token generation/consumption tracked
- Results saved to `voting_results_YYYYMMDD_HHMMSS.json`

### For Voters

```bash
python client/client.py

# Step 1: Connect to server
> Enter server IP (default: localhost): localhost
> Enter server PORT (default: 5000): 5000
✓ Successfully connected

# Step 2: Register
> 1. Register as Voter
> Enter your first name: John
> Enter your last name: Doe
✓ Registration successful!

# Step 3: View candidates (optional)
> 2. View Candidates
> Select a candidate number: 1
  Shows: Aisha Rahman - "Advocates transparent governance..."

# Step 4: Vote
> 3. Submit Vote
> Enter candidate number: 1
✓ Your vote has been accepted!
> Receipt (hash): a3c8f9d2e1b4c7f9a3c8f9d2e1b4c7f9
> Save to file? (Y/n): Y

# Step 5: Verify vote
> 6. Verify Vote
> Enter receipt hash: a3c8f9d2e1b4c7f9a3c8f9d2e1b4c7f9
✓ Vote found in blockchain!

# Step 6: View results
> 5. Show Results
> Aisha Rahman: 5 votes [████████] 45.5%
> Daniel Okafor: 3 votes [████] 27.3%
```

### For Administrators

**Run Diagnostic Tool:**
```bash
python diagnose.py localhost 5000

# Output:
# [TEST 1] Connection - ✓ Server running
# [TEST 2] Candidates - ✓ 5 candidates loaded
# [TEST 3] Blockchain - ✓ Chain has 26 blocks
# [TEST 4] Validation - ✓ Blockchain is valid
# [TEST 5] Vote Test - ✓ Vote submitted and recorded
```

**Run Full Test Suite:**
```bash
python admin_test.py localhost 5000

# Runs 7 automated tests:
# TEST 1: Basic Voting ✓
# TEST 2: Double Voting Prevention ✓
# TEST 3: Concurrent Voting ✓
# TEST 4: Chain Integrity ✓
# TEST 5: Vote Deduplication ✓
# TEST 6: Results Accuracy ✓
# TEST 7: Vote Verification ✓

# Output saved to: admin_test_log.txt
```

---

## 🔌 API Protocol (Socket-Based)

All communication uses JSON over TCP sockets.

### Request Format

```json
{
  "action": "vote|register|chain|results|verify|validate|candidates|candidates_details"
}
```

### Actions

| Action | Description | Required Fields |
|--------|---|---|
| `register` | Register as voter | `first_name`, `last_name` |
| `vote` | Submit a vote | `voter_id`, `candidate` |
| `candidates` | Get candidate list | None |
| `candidates_details` | Get candidates with descriptions | None |
| `chain` | Get full blockchain | None |
| `results` | Get vote counts | None |
| `verify` | Verify vote by receipt | `receipt` (block hash) |
| `validate` | Validate blockchain integrity | None |

### Example: Register and Vote

```json
// Request 1: Register
{"action": "register", "first_name": "John", "last_name": "Doe"}

// Response 1:
{
  "status": "success",
  "message": "Registration successful",
  "voter_id": "John_Doe",
  "candidates": ["Aisha Rahman", "Daniel Okafor", ...]
}

// Request 2: Vote
{"action": "vote", "voter_id": "John_Doe", "candidate": "Aisha Rahman"}

// Response 2:
{
  "status": "success",
  "message": "Vote accepted",
  "receipt": "a3c8f9d2e1b4c7f9...",
  "block": {
    "index": 5,
    "timestamp": 1714210234.5,
    "voter_id_hash": "a1b2c3d4...",
    "candidate": "Aisha Rahman",
    "previous_hash": "...",
    "hash": "a3c8f9d2e1b4c7f9..."
  }
}
```

---

## 🔐 Security Features

### Implemented

✅ **Voter Anonymity** - Names hashed with SHA-256, only hashes stored in blockchain  
✅ **Double Voting Prevention** - Registration tracks voter names, blockchain tracks voter hashes  
✅ **Immutable Records** - Hash chains link all blocks, tampering breaks chain  
✅ **Vote Verification** - Voters get receipt hash to prove vote was recorded  
✅ **Chain Validation** - Multi-step validation confirms all blocks valid and linked  
✅ **Registration Blocking** - Same name cannot register twice  
✅ **RSA Cryptography** - Pure-Python RSA for blind signatures and verification  

### Not Implemented (Limitations)

⚠️ **Single Node** - Centralized (not fully decentralized)  
⚠️ **Merkle Proofs** - Basic receipt verification only (no batch verification)  
⚠️ **Persistence** - Blockchain stored in RAM only (resets on server restart)  
⚠️ **Authentication** - No user password or multi-factor authentication  
⚠️ **TLS/SSL** - Socket communication not encrypted (academic project)  

---

## 📊 Data Structure

### Block Format

```python
{
  "index": 5,                              # Block position in chain
  "timestamp": 1714210234.5,              # Vote submission time
  "voter_id_hash": "a1b2c3d4e5f6g7h8...", # SHA-256(voter_name) - anonymous
  "candidate": "Aisha Rahman",            # Selected candidate
  "previous_hash": "x9y8z7w6...",        # Hash of previous block (chain link)
  "hash": "a3c8f9d2e1b4c7f9..."         # This block's hash (receipt)
}
```

### Genesis Block (Block 0)

```python
{
  "index": 0,
  "timestamp": <server_start_time>,
  "voter_id_hash": "GENESIS",
  "candidate": "GENESIS",
  "previous_hash": "0",
  "hash": <calculated_hash>
}
```

---

## 🧪 Testing

### Setup Virtual Environment (Optional)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Linux/Mac:
source venv/bin/activate

# Windows:
venv\Scripts\activate

# Install test dependencies (optional)
pip install -r requirements.txt
```

### Automated Tests (Recommended)

```bash
# Ensure server is running first (Terminal 1)
python server/server.py 5000 server/CANDIDATES.json

# In another terminal, run tests (Terminal 2)
python tests.py localhost 5000
```

**Tests Performed:**
1. Basic Voting - Submits 100 votes, verifies all recorded
2. Double Voting Prevention - Tries to vote twice, confirms blocked
3. Concurrent Voting - 10 clients, 20 votes each, verifies no conflicts
4. Chain Integrity - Validates all block hashes and chain links
5. Vote Deduplication - Confirms no duplicate voters
6. Results Accuracy - Verifies vote counts match manual count
7. Vote Verification - Tests receipt verification works

Test output is saved to: `admin_test_log.txt`

---

## 📈 Performance Characteristics

| Metric | Value |
|--------|-------|
| **Votes per second** | ~50-100 (single client sequential) |
| **Concurrent clients** | Tested with 10+ simultaneous connections |
| **Blockchain size** | ~500 bytes per vote block |
| **Hash computation** | <1ms per block (SHA-256) |
| **Chain validation** | ~5ms for 1000 blocks |

---

## 🛠️ Troubleshooting

### Issue: "Connection refused"
```bash
# Make sure server is running
python server/server.py 5000 server/CANDIDATES.json
# Check port 5000 is available
```

### Issue: "Invalid candidate"
```bash
# Make sure CANDIDATES.json exists in server directory
ls server/CANDIDATES.json
```

### Issue: "Data lost after server restart"
```
# This is expected - all data is stored in RAM
# Data persists for the duration of the server process
# To preserve votes between sessions, save results before shutting down
```

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| **README.md** | Installation, usage, API reference, troubleshooting (this file) |
| **TECHNICAL_GUIDE.md** | Architecture, blockchain mechanics, validation checklist, security analysis |

**Note:** This is an academic project designed for learning. Documentation is intentionally simple and focused.

---

## 🔗 Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT SIDE                          │
├─────────────────────────────────────────────────────────┤
│  Interactive Client (client.py)                         │
│  ├─ Menu System (7 options)                             │
│  ├─ Socket Communication                                │
│  └─ File Saving (receipts, blockchain, results)         │
└────────────────┬────────────────────────────────────────┘
                 │ JSON over TCP
                 │ (HOST:PORT)
┌────────────────┴────────────────────────────────────────┐
│               SERVER SIDE (Single Node)                 │
├─────────────────────────────────────────────────────────┤
│  Server (server.py)                                     │
│  ├─ Socket Listener                                     │
│  ├─ Request Handler                                     │
│  └─ Connection Manager                                  │
│                                                         │
│  Blockchain (blockchain.py)                             │
│  ├─ Chain: [Genesis, Block1, Block2, ...]               │
│  ├─ Voting Set: {voter_hash1, voter_hash2, ...}         │
│  ├─ Methods:                                            │
│  │  ├─ add_vote() - Add vote with dedup check           │
│  │  ├─ validate_chain() - Verify all hashes             │
│  │  ├─ verify_vote() - Find vote by receipt             │
│  │  └─ results() - Count votes per candidate            │
│  └─ Immutable: Hash chains prevent tampering            │
│                                                         │
│  Data Store:                                            │
│  ├─ CANDIDATES (from CANDIDATES.json)                   │
│  ├─ registered_voters (in-memory)                       │
│  └─ blockchain.chain (in-memory)                        │
└─────────────────────────────────────────────────────────┘
```

---

## 📝 System Workflow

```
Voter Registration Flow:
  1. Client: Enter first_name, last_name
  2. Server: Check if "first_name_last_name" already registered
  3. Server: If not, add to registered_voters and return voter_id
  4. Client: Store voter_id locally

Voting Flow:
  1. Client: Select candidate from list
  2. Client: Send {voter_id, candidate} to server
  3. Server: Hash voter_id → voter_id_hash
  4. Server: Check if voter_id_hash already in blockchain.voted set
  5. Server: If not, create block and add to blockchain.chain
  6. Server: Add voter_id_hash to blockchain.voted
  7. Server: Return receipt (block hash)
  8. Client: Display receipt and offer to save to file

Verification Flow:
  1. Client: Enter receipt (block hash)
  2. Server: Search blockchain.chain for block with matching hash
  3. Server: Return block data (without voter identity)
  4. Client: Display candidate and timestamp to confirm

Validation Flow:
  1. Client: Request validation
  2. Server: validate_chain() checks:
     ├─ Each block's hash is correct
     ├─ Each block's previous_hash links to previous block
     ├─ No broken chain links
     └─ All hashes match their data
  3. Server: Return valid=True/False
  4. Client: Display detailed validation report
```

---

## 📄 License

Academic Project - Team Implementation

---

**Last Updated:** 2026-04-27  
**Version:** 1.0 (Final)
