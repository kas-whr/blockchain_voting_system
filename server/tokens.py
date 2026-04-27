"""
Token Service for Anonymous Voting

Manages one-time voting tokens:
- Token generation (admin-only)
- Token validation (one-time use enforcement)
- Token tracking and audit logs
- Email-to-token mapping (temporary, deleted after voting)
"""

import secrets
import hashlib
import time
from datetime import datetime


class TokenManager:
    """
    Manages voting tokens for the secured voting mode.

    Properties:
    - Each token can be used exactly once
    - Tokens are not tied to voter identity in the system
    - Token consumption is tracked but history is deleted after voting
    """

    def __init__(self):
        """Initialize token manager with empty state."""
        self.active_tokens = set()  # Unused tokens
        self.used_tokens = set()    # Consumed tokens
        self.token_history = []     # Audit log (deleted after voting)

    def generate_tokens(self, count, prefix="VOTE"):
        """
        Generate N random voting tokens.

        Tokens are 64-character hex strings (256 bits of entropy).
        Admin operation only - called before voting starts.

        Args:
            count: Number of tokens to generate
            prefix: Optional prefix (e.g., "VOTE")

        Returns:
            list: Generated tokens (list of strings)
        """
        tokens = []
        for _ in range(count):
            # Generate 32 random bytes = 256 bits of entropy
            random_bytes = secrets.token_bytes(32)
            token = random_bytes.hex()
            tokens.append(token)
            self.active_tokens.add(token)

        # Log generation
        self.token_history.append({
            "event": "tokens_generated",
            "count": count,
            "timestamp": datetime.now().isoformat()
        })

        return tokens

    def validate_and_consume(self, token):
        """
        Check if token is valid (unused) and mark as used.

        This is the critical one-person-one-vote enforcement point.

        Args:
            token: Token string to validate

        Returns:
            bool: True if token was valid and consumed

        Raises:
            ValueError: If token is invalid or already used
        """
        if token not in self.active_tokens:
            if token in self.used_tokens:
                raise ValueError("Token already used")
            else:
                raise ValueError("Invalid token")

        # Consume token
        self.active_tokens.remove(token)
        self.used_tokens.add(token)

        # Log consumption (token hash only, not full token)
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        self.token_history.append({
            "event": "token_consumed",
            "token_hash": token_hash,
            "timestamp": datetime.now().isoformat()
        })

        return True

    def get_token_stats(self):
        """
        Get current token usage statistics.

        Returns:
            dict: {
                "total_generated": int,
                "active": int,
                "used": int
            }
        """
        total = len(self.active_tokens) + len(self.used_tokens)
        return {
            "total_generated": total,
            "active": len(self.active_tokens),
            "used": len(self.used_tokens)
        }

    def is_token_used(self, token):
        """
        Check if a token has been used.

        Args:
            token: Token string to check

        Returns:
            bool: True if token has been used
        """
        return token in self.used_tokens

    def clear_history(self):
        """
        Clear token history (called after voting ends).

        This irreversibly deletes the audit log.
        After this point, there is no way to trace tokens.

        Returns:
            int: Number of history entries deleted
        """
        count = len(self.token_history)
        self.token_history = []
        return count

    def get_history(self):
        """
        Get token audit history.

        Returns:
            list: History entries (dict)
        """
        return self.token_history.copy()


class EmailTokenMapper:
    """
    Temporary mapping between voter emails and voting tokens.

    This mapping is created at the start of voting and deleted
    after voting ends. No permanent record is kept.

    Critical property: Never store this mapping on disk permanently.
    """

    def __init__(self):
        """Initialize mapper with empty state."""
        self.email_to_token = {}  # {email: token_hash}
        self.token_sent_log = []   # Log of sent emails

    def add_mapping(self, email, token):
        """
        Create temporary email-to-token mapping.

        Called during token distribution phase.

        Args:
            email: Voter email address
            token: Voting token for that email

        Returns:
            str: Token hash (for logging without exposing token)
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        self.email_to_token[email] = token_hash

        # Log that email was sent (token hash only, not token itself)
        self.token_sent_log.append({
            "email": email,
            "token_hash": token_hash,
            "sent_at": datetime.now().isoformat()
        })

        return token_hash

    def verify_email_has_token(self, email):
        """
        Check if an email has been assigned a token.

        Args:
            email: Email address to check

        Returns:
            bool: True if email has a token
        """
        return email in self.email_to_token

    def get_email_count(self):
        """
        Get number of emails with tokens.

        Returns:
            int: Number of email-token mappings
        """
        return len(self.email_to_token)

    def clear_mappings(self):
        """
        Clear all email-to-token mappings.

        This irreversibly deletes the mapping. After this point,
        it's impossible to link emails to tokens.

        Returns:
            int: Number of mappings deleted
        """
        count = len(self.email_to_token)
        self.email_to_token = {}
        self.token_sent_log = []
        return count

    def get_send_log(self):
        """
        Get log of sent emails (for administrative review only).

        Returns:
            list: Log entries
        """
        return self.token_sent_log.copy()
