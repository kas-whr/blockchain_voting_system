"""
Enhanced Blockchain for Anonymous Voting

This blockchain stores votes in PostgreSQL with:
- Immutable voting records (database triggers prevent deletion/modification)
- Signature verification for secured votes
- Chain integrity validation
- Audit logging
"""

import hashlib
import time
from server_config import execute_query, execute_many
from crypto_utils import verify_payload, hash_vote_with_nonce


class Blockchain:
    """
    PostgreSQL-backed immutable blockchain for voting.

    Properties:
    - Append-only: votes can only be added, never deleted
    - Immutable: votes cannot be modified (database triggers enforce)
    - Verifiable: signatures and hashes can be verified
    - Auditable: all operations logged
    """

    def __init__(self, crypto_scheme=None):
        """
        Initialize blockchain.

        Args:
            crypto_scheme: BlindSignatureScheme instance (for verification)
        """
        self.crypto_scheme = crypto_scheme
        self.current_index = self._get_next_index()

    def _get_next_index(self):
        """Get next block index from database."""
        result = execute_query(
            "SELECT MAX(block_index) FROM blockchain_votes",
            fetch_one=True
        )
        max_index = result[0] if result and result[0] is not None else 0
        return max_index + 1

    def _calculate_block_hash(self, vote_choice, nonce, signature, previous_hash):
        """
        Calculate block hash (for chain integrity).

        Hash over: (block_index, vote_choice, nonce, signature, previous_hash)
        """
        data = (
            str(self.current_index) +
            vote_choice +
            nonce.hex() +
            signature.hex() +
            previous_hash
        )
        return hashlib.sha256(data.encode()).hexdigest()

    def _get_previous_hash(self):
        """Get hash of previous block."""
        result = execute_query(
            "SELECT block_hash FROM blockchain_votes WHERE block_index = %s",
            (self.current_index - 1,),
            fetch_one=True
        )
        if result:
            return result[0]
        return "GENESIS_HASH"  # For genesis block

    def add_vote(self, vote_choice, nonce, signature=None):
        """
        Add a vote to the blockchain.

        Args:
            vote_choice: Candidate name (str)
            nonce: Random nonce from client (bytes)
            signature: RSA signature over (vote_choice + nonce) (bytes, optional)

        Returns:
            dict: Block data

        Raises:
            ValueError: If vote is invalid
        """
        # Verify signature if provided (secured mode)
        if signature:
            if not self.crypto_scheme:
                raise ValueError("No crypto scheme configured")

            payload = vote_choice.encode() + nonce
            if not self.crypto_scheme.verify(payload, signature):
                raise ValueError("Invalid signature")

        # Calculate vote hash
        vote_hash = hash_vote_with_nonce(vote_choice, nonce)

        # Get previous hash
        previous_hash = self._get_previous_hash()

        # Calculate block hash
        block_hash = self._calculate_block_hash(
            vote_choice,
            nonce,
            signature or b'',
            previous_hash
        )

        # Insert into database
        query = """
            INSERT INTO blockchain_votes
            (vote_choice, nonce, signature, vote_hash, block_index, previous_hash, block_hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """
        params = (
            vote_choice,
            nonce,
            signature,
            vote_hash,
            self.current_index,
            previous_hash,
            block_hash
        )

        result = execute_query(query, params, fetch_one=True)

        # Increment index for next vote
        self.current_index += 1

        return {
            "id": result[0],
            "index": self.current_index - 1,
            "vote": vote_choice,
            "nonce": nonce,
            "signature": signature,
            "vote_hash": vote_hash,
            "previous_hash": previous_hash,
            "hash": block_hash,
            "timestamp": result[1].timestamp() if result[1] else time.time()
        }

    def verify_vote(self, vote_hash):
        """
        Verify that a vote exists in the blockchain.

        Args:
            vote_hash: SHA256(vote_choice + nonce) from receipt

        Returns:
            tuple: (found: bool, block: dict or None)
        """
        result = execute_query(
            """SELECT id, vote_choice, vote_hash, block_index, block_hash, created_at
               FROM blockchain_votes WHERE vote_hash = %s""",
            (vote_hash,),
            fetch_one=True
        )

        if result:
            return True, {
                "id": result[0],
                "vote": result[1],
                "vote_hash": result[2],
                "block_index": result[3],
                "block_hash": result[4],
                "timestamp": result[5]
            }

        return False, None

    def get_vote_by_block_hash(self, block_hash):
        """Get vote by block hash."""
        result = execute_query(
            """SELECT id, vote_choice, vote_hash, block_index, block_hash, created_at
               FROM blockchain_votes WHERE block_hash = %s""",
            (block_hash,),
            fetch_one=True
        )

        if result:
            return {
                "id": result[0],
                "vote": result[1],
                "vote_hash": result[2],
                "block_index": result[3],
                "block_hash": result[4],
                "timestamp": result[5]
            }

        return None

    def results(self):
        """
        Get vote counts by candidate.

        Returns:
            dict: {candidate: count, ...}
        """
        results_data = execute_query(
            """SELECT vote_choice, COUNT(*) as count
               FROM blockchain_votes
               WHERE block_index > 0
               GROUP BY vote_choice
               ORDER BY count DESC""",
            fetch_all=True
        )

        return {row[0]: row[1] for row in results_data} if results_data else {}

    def get_chain(self):
        """
        Get entire blockchain.

        Returns:
            list: All blocks in order
        """
        blocks = execute_query(
            """SELECT id, block_index, vote_choice, vote_hash, block_hash, previous_hash, created_at
               FROM blockchain_votes
               ORDER BY block_index ASC""",
            fetch_all=True
        )

        chain = []
        for block in blocks:
            chain.append({
                "id": block[0],
                "index": block[1],
                "vote": block[2],
                "vote_hash": block[3],
                "hash": block[4],
                "previous_hash": block[5],
                "timestamp": block[6]
            })

        return chain

    def validate_chain(self):
        """
        Validate entire blockchain integrity.

        Checks:
        1. Each block's hash is correct
        2. Each block links to previous block correctly
        3. No missing blocks
        4. No duplicate hashes

        Returns:
            tuple: (valid: bool, errors: list)
        """
        errors = []

        chain = self.get_chain()

        # Check 1: Genesis block
        if not chain or chain[0]["vote"] != "GENESIS":
            errors.append("Missing or invalid genesis block")
            return False, errors

        # Check 2: No gaps in block indices
        for i, block in enumerate(chain):
            if block["index"] != i:
                errors.append(f"Block index gap at position {i}: expected {i}, got {block['index']}")

        # Check 3: Hash links are valid
        for i in range(1, len(chain)):
            current = chain[i]
            previous = chain[i - 1]

            if current["previous_hash"] != previous["hash"]:
                errors.append(
                    f"Block {i} not linked to previous: "
                    f"previous_hash={current['previous_hash']}, "
                    f"previous.hash={previous['hash']}"
                )

        # Check 4: No duplicate hashes
        hashes = [block["hash"] for block in chain]
        if len(hashes) != len(set(hashes)):
            errors.append("Duplicate block hashes detected")

        return len(errors) == 0, errors

    def get_statistics(self):
        """Get blockchain statistics."""
        result = execute_query(
            """SELECT
                COUNT(*) as total_blocks,
                COUNT(DISTINCT vote_choice) as unique_candidates,
                MIN(created_at) as first_vote,
                MAX(created_at) as last_vote
               FROM blockchain_votes
               WHERE block_index > 0""",
            fetch_one=True
        )

        if result:
            return {
                "total_blocks": result[0],
                "total_votes": result[0] - 1,  # Exclude genesis
                "unique_candidates": result[1],
                "first_vote": result[2],
                "last_vote": result[3]
            }

        return {
            "total_blocks": 1,
            "total_votes": 0,
            "unique_candidates": 0,
            "first_vote": None,
            "last_vote": None
        }

    def get_vote_count(self):
        """Get total number of votes cast."""
        result = execute_query(
            "SELECT COUNT(*) FROM blockchain_votes WHERE block_index > 0",
            fetch_one=True
        )
        return result[0] if result else 0
