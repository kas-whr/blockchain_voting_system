"""
Blockchain Module - In-Memory Vote Ledger

Implements an immutable blockchain for recording votes.
All data stored in RAM during server execution.
"""

import hashlib
import time
import threading
from collections import defaultdict


class Blockchain:
    """In-memory blockchain for vote recording."""

    def __init__(self, crypto_scheme=None):
        """
        Initialize blockchain with genesis block.

        Args:
            crypto_scheme: Optional crypto scheme (kept for compatibility)
        """
        self.chain = []
        self.voted_hashes = set()
        self.current_index = 0
        self.crypto_scheme = crypto_scheme
        self._lock = threading.Lock()
        self._create_genesis_block()

    def _create_genesis_block(self):
        """Create the first block (genesis block)."""
        genesis_block = {
            "index": 0,
            "timestamp": time.time(),
            "voter_id_hash": "GENESIS",
            "candidate": "GENESIS",
            "previous_hash": "0",
            "hash": self._calculate_hash(
                0, time.time(), "GENESIS", "GENESIS", "0"
            )
        }
        self.chain.append(genesis_block)
        self.current_index = 1

    def _calculate_hash(self, index, timestamp, voter_id_hash, candidate, previous_hash):
        """Calculate SHA-256 hash for a block."""
        data = (
            str(index) +
            str(timestamp) +
            voter_id_hash +
            candidate +
            previous_hash
        )
        return hashlib.sha256(data.encode()).hexdigest()

    def _get_previous_hash(self):
        """Get the hash of the last block in the chain."""
        if len(self.chain) > 0:
            return self.chain[-1]["hash"]
        return "0"

    def add_vote(self, voter_id, candidate, timestamp=None):
        """
        Add a vote to the blockchain.

        Args:
            voter_id: Voter identifier (e.g., "John_Doe")
            candidate: Selected candidate name
            timestamp: Optional timestamp (auto-generated if None)

        Returns:
            dict: The new block that was added, or None if vote rejected
        """
        if timestamp is None:
            timestamp = time.time()

        # Hash the voter ID for anonymity
        voter_id_hash = hashlib.sha256(voter_id.encode()).hexdigest()

        with self._lock:
            # Check for duplicate votes
            if voter_id_hash in self.voted_hashes:
                return None

            # Get the previous block's hash
            previous_hash = self._get_previous_hash()

            # Calculate this block's hash
            block_hash = self._calculate_hash(
                self.current_index,
                timestamp,
                voter_id_hash,
                candidate,
                previous_hash
            )

            # Create the block
            block = {
                "index": self.current_index,
                "timestamp": timestamp,
                "voter_id_hash": voter_id_hash,
                "candidate": candidate,
                "previous_hash": previous_hash,
                "hash": block_hash
            }

            # Add to blockchain
            self.chain.append(block)
            self.voted_hashes.add(voter_id_hash)
            self.current_index += 1

            return block

    def verify_vote(self, receipt_hash):
        """
        Verify a vote by its receipt hash.

        Args:
            receipt_hash: The block hash (receipt) provided to voter

        Returns:
            dict: The block if found, None otherwise
        """
        for block in self.chain:
            if block["hash"] == receipt_hash:
                return block
        return None

    def results(self):
        """
        Get vote count by candidate.

        Returns:
            dict: {candidate_name: vote_count}
        """
        counts = defaultdict(int)
        for block in self.chain[1:]:  # Skip genesis block
            if block["candidate"] != "GENESIS":
                counts[block["candidate"]] += 1
        return dict(counts)

    def get_chain(self):
        """
        Get the entire blockchain.

        Returns:
            list: All blocks in the chain
        """
        return self.chain

    def validate_chain(self):
        """
        Validate the integrity of the blockchain.

        Returns:
            dict: {
                "valid": bool,
                "message": str,
                "blocks_checked": int,
                "duplicates": int
            }
        """
        if len(self.chain) == 0:
            return {
                "valid": False,
                "message": "Blockchain is empty",
                "blocks_checked": 0,
                "duplicates": 0
            }

        # Check for duplicate votes
        voter_hashes = [block["voter_id_hash"] for block in self.chain[1:]]
        unique_voters = len(set(voter_hashes))
        total_votes = len(voter_hashes)
        duplicates = total_votes - unique_voters

        if duplicates > 0:
            return {
                "valid": False,
                "message": f"Found {duplicates} duplicate votes",
                "blocks_checked": len(self.chain),
                "duplicates": duplicates
            }

        # Verify hash chain integrity
        for i in range(1, len(self.chain)):
            block = self.chain[i]
            previous_block = self.chain[i - 1]

            # Check previous hash link
            if block["previous_hash"] != previous_block["hash"]:
                return {
                    "valid": False,
                    "message": f"Hash link broken at block {i}",
                    "blocks_checked": i,
                    "duplicates": 0
                }

            # Recalculate hash and verify
            calculated_hash = self._calculate_hash(
                block["index"],
                block["timestamp"],
                block["voter_id_hash"],
                block["candidate"],
                block["previous_hash"]
            )
        
            if calculated_hash != block["hash"]:
                return {
                    "valid": False,
                    "message": f"Hash mismatch at block {i}",
                    "blocks_checked": i,
                    "duplicates": 0
                }

        return {
            "valid": True,
            "message": "Blockchain is valid",
            "blocks_checked": len(self.chain),
            "duplicates": 0
        }

    def get_statistics(self):
        """
        Get blockchain statistics.

        Returns:
            dict: Statistics about the blockchain
        """
        total_votes = len(self.chain) - 1  # Exclude genesis
        candidates = set()
        for block in self.chain[1:]:
            if block["candidate"] != "GENESIS":
                candidates.add(block["candidate"])

        return {
            "total_blocks": len(self.chain),
            "total_votes": total_votes,
            "unique_candidates": len(candidates),
            "chain_valid": self.validate_chain()["valid"]
        }

    def get_vote_count(self):
        """Get total number of votes (excluding genesis)."""
        return len(self.chain) - 1
