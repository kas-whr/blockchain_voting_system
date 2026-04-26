# Blockchain-Based Voting System (Variant A)

## Description

This project implements a blockchain-based voting system with a centralized architecture.

Votes are submitted by clients and stored immutably in a blockchain managed by a single server node. The system ensures:

* prevention of double voting
* transparency of vote storage
* ability to verify vote inclusion using a receipt (hash)

---

## Architecture

* **Client** → sends vote requests
* **Server (Single Node)** → validates and stores votes
* **Blockchain Ledger** → maintains immutable vote records

---

## Blockchain Structure


---

## Features

* Submit a vote
* Prevent double voting
* View full blockchain
* View voting results
* Verify vote using receipt
* Validate blockchain integrity

---

## API Endpoints (Server)

| Method | Endpoint            | Description                   |
| ------ | ------------------- | ----------------------------- |
| POST   | `/vote`             | Submit a vote                 |
| GET    | `/chain`            | Get full blockchain           |
| GET    | `/results`          | Get vote counts               |
| GET    | `/verify/<receipt>` | Verify vote inclusion         |
| GET    | `/validate`         | Validate blockchain integrity |

---

## How to Run

### 1. Start Server

```bash
cd server
pip install -r requirements.txt
python app.py
```

Server runs at:

```
http://127.0.0.1:5000
```

---

### 2. Run Client

```bash
cd client
pip install -r requirements.txt
python client.py
```

---

## Verification Flow

1. Submit vote → receive **receipt (hash)**
2. Use `/verify/<receipt>` to confirm vote exists
3. System returns block containing the vote

---

## Security & Limitations

### Implemented

* Hashing of voter IDs
* Immutable block structure
* Double voting prevention

### Limitations

* Centralized server (not fully decentralized)
* No real authentication system
* No cryptographic signatures
* Not production-ready

---

## Technologies Used

* Python
* Flask
* Requests
* Hashing (SHA-256)

---

## Project Goals (Checklist)

* [] Log votes with timestamp and hash
* [] Prevent duplicate voting
* [] Store votes in blockchain
* [] Provide verification mechanism
* [] Validate blockchain integrity

---

## Author

Student Project — Blockchain Voting System
