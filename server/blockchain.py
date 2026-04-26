import hashlib
import time


class Blockchain:
    def __init__(self):
        self.chain = []
        self.voted = set()
        self.create_block("GENESIS", "GENESIS")

    def hash_text(self, text):
        return hashlib.sha256(text.encode()).hexdigest()

    def calculate_hash(self, block):
        data = (
            str(block["index"])
            + str(block["timestamp"])
            + block["voter_id_hash"]
            + block["candidate"]
            + block["previous_hash"]
        )
        return hashlib.sha256(data.encode()).hexdigest()

    def create_block(self, voter_id_hash, candidate):
        block = {
            "index": len(self.chain),
            "timestamp": time.time(),
            "voter_id_hash": voter_id_hash,
            "candidate": candidate,
            "previous_hash": self.chain[-1]["hash"] if self.chain else "0",
        }
        block["hash"] = self.calculate_hash(block)
        self.chain.append(block)
        return block

    def add_vote(self, voter_id, candidate):
        voter_id_hash = self.hash_text(voter_id)

        if voter_id_hash in self.voted:
            return None, "This voter has already voted"

        block = self.create_block(voter_id_hash, candidate)
        self.voted.add(voter_id_hash)

        return block, "Vote accepted"

    def results(self):
        counts = {}

        for block in self.chain:
            if block["candidate"] == "GENESIS":
                continue

            candidate = block["candidate"]
            counts[candidate] = counts.get(candidate, 0) + 1

        return counts

    def verify_vote(self, receipt):
        for block in self.chain:
            if block["hash"] == receipt:
                return True, block

        return False, None

    def validate_chain(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            if current["previous_hash"] != previous["hash"]:
                return False

            if current["hash"] != self.calculate_hash(current):
                return False

        return True