# Blockchain Voting System with Blind Signatures

Cryptographically secure anonymous voting system using RSA blind signatures, one-time voting tokens, and PostgreSQL immutable blockchain.

## System Architecture

### Components

1. **Admin Panel** (`server/admin_panel.py`)
   - Load candidates
   - Generate voting tokens
   - Send tokens via email
   - Monitor voting progress
   - Export results and validate blockchain

2. **Voting Server** (`server/server.py`)
   - Handle blind signature requests
   - Process secured vote submissions
   - Validate signatures
   - Maintain blockchain
   - Provide vote verification

3. **Client Application** (`client/client.py`)
   - Connect to voting server
   - Input voting token
   - Perform blind signature protocol
   - Submit anonymous vote
   - Verify receipt

4. **Cryptographic Core** (`server/crypto_utils.py`, `client/crypto_client.py`)
   - RSA blind signatures
   - Nonce generation
   - Signature verification
   - Vote hashing

5. **Token Service** (`server/tokens.py`)
   - One-time token generation
   - Token validation & consumption
   - Email-to-token mapping (temporary)

6. **Database Layer** (`server/blockchain.py`, `server/db_setup.sql`)
   - PostgreSQL-backed immutable blockchain
   - Vote storage with signatures
   - Chain integrity validation
   - Audit logging

## Voting Flow

### Secured Mode (Token + Blind Signature)

#### Setup Phase (Admin)
```
Admin Panel:
1. Load candidates from JSON
2. Generate N one-time voting tokens
3. Distribute tokens to voters via email (out-of-system)
4. Start voting
```

#### Voting Phase (Client/Voter)
```
Client:
1. Enter voting token (from email)
2. Get server's public key
3. Select candidate
4. Generate random nonce (client-side)
5. Create payload: vote_choice + nonce
6. Blind payload: blinded = blind(payload)
7. Send: {token, blinded_payload}

Server:
8. Validate token (consume/mark as used)
9. Sign blinded data: sig = sign(blinded)
10. Return: {blinded_signature, public_key}

Client:
11. Unblind signature: sig = unblind(blinded_sig)
12. Verify signature: verify(payload, sig) ✓
13. Submit: {vote_choice, nonce, signature}

Server:
14. Verify signature: verify(vote_choice + nonce, sig) ✓
15. Store in blockchain
16. Return: receipt with vote_hash

Blockchain:
- Add immutable vote record
- Link to previous block
- Ensure chain integrity
```

#### Verification Phase (Voter)
```
Voter:
1. Use receipt to verify vote was recorded
2. Provides: vote_hash and nonce
3. Server confirms: vote_hash found in blockchain
4. Proof of inclusion without revealing identity
```

## Security Properties

### Voter Anonymity (Server Cannot Deanonymize)
✓ **Token → Vote Mapping:** Token consumed BEFORE server signs, so server never sees unblinded vote
✓ **Blinding Prevents Observation:** Server signs without knowing vote content
✓ **Nonce Unknown to Server:** Client-generated, never transmitted before vote submission
✓ **No Identity Storage:** Blockchain contains only vote, nonce, and signature (no voter ID)
✓ **Email → Vote Mapping:** Temporary, deleted after voting ends

Even if admin has PostgreSQL access:
- Cannot link email to vote (mapping deleted)
- Cannot link token to vote (consumed before submission)
- Cannot find vote in blockchain without nonce (only voter knows nonce)

### One-Person-One-Vote Enforcement
✓ **Token Uniqueness:** Each token used exactly once
✓ **Token Consumption:** Validated before blind signature step
✓ **Immutable Records:** PostgreSQL triggers prevent vote modification/deletion
✓ **Receipt Verification:** Only voter can verify (knows nonce)

### Vote Immutability
✓ **Append-Only Blockchain:** Votes only added, never removed
✓ **Hash Chain Integrity:** Previous hash validates linking
✓ **Signature Verification:** RSA signatures verify vote authenticity
✓ **Database Triggers:** PostgreSQL prevents tampering at database level

## Setup & Installation

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- Libraries: `cryptography`, `psycopg2-binary`

### Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up PostgreSQL:**
```bash
# Create database
createdb voting_system

# Load schema
psql voting_system < server/db_setup.sql
```

3. **Configure environment (optional):**
```bash
export VOTING_DB_HOST=localhost
export VOTING_DB_PORT=5432
export VOTING_DB_NAME=voting_system
export VOTING_DB_USER=postgres
```

## Running the System

### 1. Start Admin Panel
```bash
python3 server/admin_panel.py
```

Follow the menu to:
- Load candidates (from `server/CANDIDATES.json`)
- Generate tokens (e.g., 100 tokens for 100 voters)
- Send tokens via email (requires SMTP server)
- Monitor voting progress
- Export results

### 2. Start Voting Server
```bash
python3 server/server.py 5000 server/CANDIDATES.json
```

Server listens on `localhost:5000` (or specified port)

### 3. Run Voting Client
```bash
python3 client/client.py
```

Client connects to server and:
- Authenticates with voting token
- Performs blind signature protocol
- Submits anonymous vote
- Receives digital receipt
- Can verify receipt later

## File Structure

```
/home/stefan/DNP/blockchain_voting_system/
├── server/
│   ├── admin_panel.py           # Admin UI
│   ├── server.py                # Voting server
│   ├── blockchain.py            # PostgreSQL-backed blockchain
│   ├── crypto_utils.py          # RSA blind signatures
│   ├── tokens.py                # Token management
│   ├── email_service.py         # Email token distribution
│   ├── server_config.py         # DB configuration
│   ├── db_setup.sql             # PostgreSQL schema
│   ├── CANDIDATES.json          # Candidate list
│   └── admin_logs.txt           # Admin action logs
│
├── client/
│   ├── client.py                # Voting client
│   ├── crypto_client.py         # Client-side crypto
│   └── receipts/                # Stored receipts (auto-created)
│
├── test_crypto.py               # Quick crypto test
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Digital Receipt

Each voter receives a receipt:
```json
{
  "vote_hash": "a1b2c3d4...",     // SHA256(vote_choice + nonce)
  "nonce_hex": "3f2a5b...",       // Client-generated nonce (only voter knows)
  "signature_hex": "4f8e9a...",   // RSA blind signature
  "timestamp": 1705315523,
  "block_index": 42,
  "mode": "secured"
}
```

**Properties:**
- Vote hash alone doesn't reveal vote (need nonce)
- Only voter knows nonce (proves ownership)
- Signature verifiable with server's public key
- Proof of blockchain inclusion

## Testing

### Quick Crypto Test
```bash
python3 test_crypto.py
```

Tests:
- RSA keypair generation
- Blinding/unblinding operations
- Signature verification
- Vote hash computation

### Full System Test
1. Start database: `psql voting_system`
2. Start server: `python3 server/server.py 5000`
3. Start client: `python3 client/client.py`
4. Enter test token: `abcd1234...` (generated by admin)
5. Vote for a candidate
6. Verify receipt

## Security Considerations

### ✓ Implemented
- RSA-2048 blind signatures (server cannot deanonymize)
- One-time tokens (no vote reuse)
- PostgreSQL immutable blockchain (no tampering)
- Client-side nonce generation (anonymity)
- Temporary token-to-email mapping (deleted after voting)
- Signature verification on all votes

### ⚠️ Not Implemented (Future Enhancements)
- TLS/HTTPS for client-server communication
- Voter authentication (passwords, MFA)
- Distributed blockchain nodes (RAFT consensus)
- Zero-knowledge proofs (enhanced verification)
- Hardware security modules (HSM) for keys
- Audit trail anonymization
- Post-quantum cryptography

### ⚠️ Assumptions
- Server's RSA private key is secure
- Email distribution of tokens happens out-of-system
- Client device is trusted (no malware)
- Network communication is monitored (use VPN/Tor if privacy critical)

## Privacy Guarantees

### For Voting Officials
✓ Cannot link token to vote
✓ Cannot link email to vote
✓ Cannot link network request to identity
✓ Can only see vote counts and blockchain integrity

### For Voters
✓ Vote is anonymous (even from officials)
✓ Vote cannot be modified after submission
✓ Receipt proves vote was counted
✓ Can verify receipt later
✓ Nonce-based ownership proof (only voter can verify their own receipt)

## Legal & Compliance

This system demonstrates cryptographic voting principles suitable for:
- Educational research projects
- Proof-of-concept demonstrations
- Small-scale community decisions (not real elections)

For real elections, consider:
- Legal framework compliance (ballot integrity laws)
- Third-party audits (security certification)
- Voter authentication (national ID integration)
- Regulatory oversight (election commissions)
- Professional cryptographic review

## Troubleshooting

### PostgreSQL Connection Error
```
Error: could not connect to database
```
**Solution:** Ensure PostgreSQL is running and database is created
```bash
sudo systemctl start postgresql
createdb voting_system
psql voting_system < server/db_setup.sql
```

### Import Error: No module named 'cryptography'
```bash
pip install cryptography psycopg2-binary
```

### Email Send Failed
- Check SMTP host and port
- Test with local MailHog: `docker run -p 1025:1025 mailhog/mailhog`
- Use test mode in admin panel

### Token Validation Error
- Ensure token is valid (from admin-generated list)
- Token can only be used once
- Check if voting has started

## References

- [RSA Blind Signatures](https://en.wikipedia.org/wiki/Blind_signature)
- [Cryptography Library Docs](https://cryptography.io/)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/sql-syntax.html)
- [Anonymous Voting Protocols](https://en.wikipedia.org/wiki/Anonymous_voting)

## License

Educational project for cryptographic research.

## Contact

For questions or improvements, contact the development team.
