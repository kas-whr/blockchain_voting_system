# Blockchain Voting System (Variant A) - User Guide

This project is a blockchain-based voting system with anonymous voting via RSA blind signatures.

It includes:
- an **admin server** for election setup and control,
- a **voter client** for secure voting,
- receipt-based vote verification and blockchain integrity checks.

## 1) Prerequisites

- Python `3.9+` (recommended `3.10+`)
- `pip`
- Terminal access on Linux/macOS/Windows

## 2) Project Structure

- `server/admin_server.py` - election administration panel + background socket server
- `server/server.py` - request handler logic
- `server/CANDIDATES.json` - candidates list loaded at startup
- `client/client.py` - voter-side interactive CLI
- `server/tests.py` - load/integration test suite (optional)

Generated during usage:
- `client/receipts/` - voter receipts (`receipt_*.json`)
- `client/exports/` - exported blockchain snapshots
- `logs/` - server logs
- `voting_results_*.zip` - final packaged results produced by admin panel

## 3) Installation

Run from repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt
```

If you use Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r server/requirements.txt
```

## 4) Start the Election (Admin Side)

From repository root:

```bash
python3 server/admin_server.py 5000 server/CANDIDATES.json
```

Parameters:
- `5000` - port
- `server/CANDIDATES.json` - candidate file path

Inside the admin panel:
- Use option **1** to generate voting tokens and distribute them to voters.
- Use option **3** to monitor live results.
- Use option **2** to stop voting and create final artifacts (`results.json`, `blockchain.json`, `winner.txt` in a `.zip` file).

## 5) Vote as a User (Client Side)

In another terminal (same machine or remote machine that can reach server):

```bash
cd client
python3 client.py
```

Then follow the menu:
1. Connect to server (`host`, `port`)
2. Submit Vote (Blind Signature)
3. Provide your one-time token
4. Select candidate
5. Client completes blind-signature flow automatically
6. Receive and save digital receipt

The receipt is saved as JSON in `client/receipts/`.

## 6) Verify Your Vote

In client menu, choose **Verify Receipt**:
- Recommended: load your saved receipt JSON file
- Alternative: paste `receipt_hash` manually

The client asks server to confirm that the receipt exists in blockchain and returns block metadata if valid.

## 7) Useful Runtime Actions

From client:
- **See Blockchain (and export)** - view latest blocks and optionally export full chain to `client/exports/`
- **View Results** - current vote counts
- **Validate Blockchain** - integrity check (hash links + duplicate-vote detection)

From admin panel:
- Generate tokens in batches before/while voting
- Stop and archive election outputs at the end

## 8) Optional: Run Test Suite

Start admin server first, then from repository root:

```bash
python3 server/tests.py localhost 5000 150
```

Arguments:
- host (default `localhost`)
- port (default `5000`)
- number of votes to simulate (default `150`)

## 9) Troubleshooting

- `Connection refused` on client:
  - Ensure admin server is running and listening on selected port.
- `Invalid token` / `Token already used`:
  - Tokens are one-time only; request a new unused token from admin.
- `Invalid signature`:
  - Retry vote flow from start; ensure stable connection and correct server target.
- No candidates shown:
  - Verify `server/CANDIDATES.json` exists and contains valid JSON array.

## 10) Security Notes

- Vote anonymity is achieved with blind signatures: server signs a blinded payload and cannot see the vote at signing stage.
- One-person-one-vote is enforced by one-time token consumption and hashed nonce-based deduplication in blockchain.
- Blockchain in this project is **single-node, in-memory** (academic prototype). Data persistence is provided through export/result packages rather than continuous database storage.
