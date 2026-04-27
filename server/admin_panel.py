"""
Admin Panel for Secure Voting System

Text-based interface for:
1. Loading candidates
2. Generating voting tokens
3. Sending tokens via email
4. Monitoring voting progress
5. Stopping voting and exporting results
6. Validating blockchain
"""

import json
import os
import sys
import time
from datetime import datetime
from server_config import DatabaseConfig, DatabaseConnection, init_database
from blockchain import Blockchain
from crypto_utils import BlindSignatureScheme, serialize_private_key
from tokens import TokenManager, EmailTokenMapper
from email_service import EmailService, EmailConfig


class AdminPanel:
    """Text-based admin interface for voting system."""

    def __init__(self):
        """Initialize admin panel."""
        self.candidates = []
        self.token_manager = TokenManager()
        self.email_mapper = EmailTokenMapper()
        self.email_service = None
        self.blockchain = None
        self.crypto_scheme = None
        self.voting_started = False
        self.candidates_file = None

    def clear_screen(self):
        """Clear terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self, title):
        """Print formatted header."""
        self.clear_screen()
        print("=" * 60)
        print(f"  {title.center(56)}")
        print("=" * 60)
        print()

    def print_menu(self, options):
        """Print menu options."""
        for key, value in options.items():
            print(f"  {key}. {value}")
        print()

    def load_candidates(self):
        """Load candidates from JSON file."""
        self.print_header("LOAD CANDIDATES")

        if not self.candidates_file:
            default_path = "server/CANDIDATES.json"
            file_path = input(f"  Enter candidates file path (default: {default_path}): ").strip()
            if not file_path:
                file_path = default_path
        else:
            file_path = self.candidates_file

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    self.candidates = [c.get("FullName", c.get("name", str(c))) for c in data]
                    print(f"  ✓ Loaded {len(self.candidates)} candidates:")
                    for i, candidate in enumerate(self.candidates, 1):
                        print(f"    {i}. {candidate}")
                    self.candidates_file = file_path
                else:
                    print("  ✗ Invalid candidates file format")
        except FileNotFoundError:
            print(f"  ✗ File not found: {file_path}")
        except json.JSONDecodeError:
            print("  ✗ Invalid JSON file")
        except Exception as e:
            print(f"  ✗ Error: {e}")

        input("\n  Press Enter to continue...")

    def generate_tokens(self):
        """Generate voting tokens."""
        self.print_header("GENERATE VOTING TOKENS")

        if not self.candidates:
            print("  ✗ Please load candidates first")
            input("  Press Enter to continue...")
            return

        try:
            num_voters = int(input("  Enter number of voters: ").strip())
            if num_voters <= 0:
                print("  ✗ Number must be positive")
                return

            print(f"\n  Generating {num_voters} tokens...")
            tokens = self.token_manager.generate_tokens(num_voters)

            print(f"  ✓ Generated {len(tokens)} tokens")

            # Ask to save tokens to file
            save_choice = input("  Save tokens to file? (y/N): ").strip().upper()
            if save_choice == 'Y':
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"voting_tokens_{timestamp}.txt"
                with open(filename, 'w') as f:
                    for token in tokens:
                        f.write(token + '\n')
                print(f"  ✓ Tokens saved to {filename}")

        except ValueError:
            print("  ✗ Invalid number")

        input("\n  Press Enter to continue...")

    def send_tokens_via_email(self):
        """Send tokens to voters via email."""
        self.print_header("SEND TOKENS VIA EMAIL")

        stats = self.token_manager.get_token_stats()
        if stats['active'] == 0:
            print("  ✗ No tokens available. Generate tokens first.")
            input("  Press Enter to continue...")
            return

        print(f"  Available tokens: {stats['active']}")
        print()

        # Get email list
        email_input = input("  Enter voter emails (comma-separated or file path): ").strip()

        emails = []
        if email_input.endswith('.txt') or email_input.endswith('.csv'):
            # Load from file
            try:
                with open(email_input, 'r') as f:
                    emails = [line.strip() for line in f if line.strip()]
            except FileNotFoundError:
                print(f"  ✗ File not found: {email_input}")
                input("  Press Enter to continue...")
                return
        else:
            # Parse comma-separated
            emails = [e.strip() for e in email_input.split(',') if e.strip()]

        if len(emails) > stats['active']:
            print(f"  ✗ Only {stats['active']} tokens available, but {len(emails)} emails provided")
            input("  Press Enter to continue...")
            return

        # Initialize email service
        smtp_host = input("  SMTP host (default: localhost): ").strip() or "localhost"
        smtp_port = input("  SMTP port (default: 1025): ").strip() or "1025"

        try:
            smtp_port = int(smtp_port)
        except ValueError:
            print("  ✗ Invalid port number")
            input("  Press Enter to continue...")
            return

        email_config = EmailConfig(smtp_host=smtp_host, smtp_port=smtp_port)
        email_service = EmailService(email_config)

        # Test mode confirmation
        print()
        test_mode_input = input("  Send emails? (y/N): ").strip().upper()
        test_mode = test_mode_input != 'Y'

        # Send tokens
        print()
        print("  Sending tokens...")

        active_tokens = list(self.token_manager.active_tokens)[:len(emails)]
        email_token_pairs = list(zip(emails, active_tokens))

        for email, token in email_token_pairs:
            try:
                email_service.send_voting_token(email, token, test_mode=test_mode)
                self.email_mapper.add_mapping(email, token)
                print(f"  ✓ Token sent to {email}")
            except Exception as e:
                print(f"  ✗ Failed to send to {email}: {e}")

        print(f"\n  ✓ Processed {len(email_token_pairs)} emails")

        input("\n  Press Enter to continue...")

    def start_voting(self):
        """Start voting."""
        self.print_header("START VOTING")

        if not self.candidates:
            print("  ✗ Please load candidates first")
            input("  Press Enter to continue...")
            return

        stats = self.token_manager.get_token_stats()
        if stats['total_generated'] == 0:
            print("  ✗ Please generate tokens first")
            input("  Press Enter to continue...")
            return

        print(f"  Voting configuration:")
        print(f"  - Candidates: {len(self.candidates)}")
        print(f"  - Total tokens: {stats['total_generated']}")
        print()

        confirm = input("  Start voting now? (y/N): ").strip().upper()
        if confirm != 'Y':
            print("  Cancelled.")
            input("  Press Enter to continue...")
            return

        self.voting_started = True
        print("  ✓ Voting started")
        print(f"  Voters can now connect and vote")

        input("\n  Press Enter to continue...")

    def monitor_voting(self):
        """Monitor voting progress."""
        while True:
            self.print_header("VOTING MONITOR (Press Ctrl+C to exit)")

            if not self.voting_started:
                print("  ✗ Voting not started")
                break

            stats = self.token_manager.get_token_stats()

            print(f"  Voting Status: ACTIVE")
            print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            print(f"  Token Statistics:")
            print(f"  - Total generated: {stats['total_generated']}")
            print(f"  - Used: {stats['used']}")
            print(f"  - Remaining: {stats['active']}")
            print()

            if self.blockchain:
                vote_count = self.blockchain.get_vote_count()
                results = self.blockchain.results()
                print(f"  Vote Statistics:")
                print(f"  - Total votes: {vote_count}")
                print(f"  - Candidates with votes: {len(results)}")
                print()

                if results:
                    print(f"  Results (so far):")
                    total = sum(results.values())
                    for candidate, count in sorted(results.items(), key=lambda x: x[1], reverse=True):
                        pct = (count / total * 100) if total > 0 else 0
                        bar = "█" * int(pct / 5)
                        print(f"    {candidate:20} {count:3} votes [{bar:20}] {pct:5.1f}%")

            print()
            print("  Options:")
            print("    1. Refresh")
            print("    2. Stop voting")
            print("    0. Exit monitor")
            print()

            choice = input("  Choose option: ").strip()

            if choice == '1':
                time.sleep(2)
                continue
            elif choice == '2':
                self.voting_started = False
                print("  ✓ Voting stopped")
                input("  Press Enter to continue...")
                break
            elif choice == '0':
                break
            else:
                print("  Invalid option")
                time.sleep(1)

    def export_results(self):
        """Export voting results."""
        self.print_header("EXPORT RESULTS")

        if not self.blockchain:
            print("  ✗ No blockchain data")
            input("  Press Enter to continue...")
            return

        results = self.blockchain.results()
        if not results:
            print("  ✗ No votes recorded")
            input("  Press Enter to continue...")
            return

        total_votes = sum(results.values())
        print(f"  Total votes: {total_votes}")
        print()

        # Display results
        print("  Results:")
        for candidate, count in sorted(results.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total_votes * 100) if total_votes > 0 else 0
            bar = "█" * int(pct / 5)
            print(f"    {candidate:20} {count:3} votes [{bar:20}] {pct:5.1f}%")

        # Export to CSV
        print()
        save_choice = input("  Save results to CSV? (y/N): ").strip().upper()
        if save_choice == 'Y':
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"voting_results_{timestamp}.csv"
            with open(filename, 'w') as f:
                f.write("Candidate,Votes,Percentage\n")
                for candidate, count in sorted(results.items(), key=lambda x: x[1], reverse=True):
                    pct = (count / total_votes * 100) if total_votes > 0 else 0
                    f.write(f"{candidate},{count},{pct:.2f}\n")
            print(f"  ✓ Results saved to {filename}")

        input("\n  Press Enter to continue...")

    def validate_blockchain(self):
        """Validate blockchain integrity."""
        self.print_header("BLOCKCHAIN VALIDATION")

        if not self.blockchain:
            print("  ✗ No blockchain data")
            input("  Press Enter to continue...")
            return

        print("  Validating blockchain...")
        valid, errors = self.blockchain.validate_chain()

        if valid:
            print("  ✓ BLOCKCHAIN VALID")
            stats = self.blockchain.get_statistics()
            print()
            print(f"  Statistics:")
            print(f"  - Total blocks: {stats['total_blocks']}")
            print(f"  - Total votes: {stats['total_votes']}")
            print(f"  - Unique candidates: {stats['unique_candidates']}")
        else:
            print("  ✗ BLOCKCHAIN INVALID")
            print()
            print("  Errors:")
            for error in errors:
                print(f"    - {error}")

        input("\n  Press Enter to continue...")

    def show_main_menu(self):
        """Main admin menu loop."""
        while True:
            self.print_header("BLOCKCHAIN VOTING SYSTEM - ADMIN PANEL")

            if self.voting_started:
                print("  Status: VOTING IN PROGRESS")
            else:
                print("  Status: READY")

            if self.candidates:
                print(f"  Candidates: {len(self.candidates)} loaded")
            else:
                print("  Candidates: NOT LOADED")

            stats = self.token_manager.get_token_stats()
            print(f"  Tokens: {stats['total_generated']} generated, {stats['used']} used")

            print()
            options = {
                "1": "Load Candidates",
                "2": "Generate Tokens",
                "3": "Send Tokens via Email",
                "4": "Start Voting",
                "5": "Monitor Voting",
                "6": "Export Results",
                "7": "Validate Blockchain",
                "0": "Exit"
            }

            self.print_menu(options)

            choice = input("  Choose option: ").strip()

            if choice == "1":
                self.load_candidates()
            elif choice == "2":
                self.generate_tokens()
            elif choice == "3":
                self.send_tokens_via_email()
            elif choice == "4":
                self.start_voting()
            elif choice == "5":
                self.monitor_voting()
            elif choice == "6":
                self.export_results()
            elif choice == "7":
                self.validate_blockchain()
            elif choice == "0":
                print("  Goodbye!")
                break
            else:
                print("  Invalid option")
                input("  Press Enter to try again...")


def main():
    """Main entry point for admin panel."""
    print("Initializing Admin Panel...")

    # Initialize database
    try:
        config = DatabaseConfig()
        DatabaseConnection.initialize(config)
        init_database(config)
        print("✓ Database initialized")
    except Exception as e:
        print(f"✗ Database error: {e}")
        print("Make sure PostgreSQL is running and configured correctly.")
        sys.exit(1)

    # Initialize blockchain
    try:
        from crypto_utils import BlindSignatureScheme
        crypto_scheme = BlindSignatureScheme()
        blockchain = Blockchain(crypto_scheme=crypto_scheme)
        print("✓ Blockchain initialized")
    except Exception as e:
        print(f"✗ Blockchain error: {e}")
        sys.exit(1)

    # Start admin panel
    admin = AdminPanel()
    admin.blockchain = blockchain
    admin.crypto_scheme = crypto_scheme

    print()
    admin.show_main_menu()


if __name__ == "__main__":
    main()
