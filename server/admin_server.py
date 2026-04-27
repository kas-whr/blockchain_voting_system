"""
Blockchain Voting System - Admin Server with Interactive Panel

Combines:
- Socket server for client connections (runs in background thread)
- Interactive admin panel with real-time status monitoring
- File-based logging system
- Token management and results saving
"""

import socket
import json
import sys
import os
import time
import threading
import logging
from datetime import datetime
from pathlib import Path
from server import VotingServer


class AdminServerPanel:
    """Interactive admin panel for voting server management."""

    def __init__(self, host="0.0.0.0", port=5000, candidates_file="server/CANDIDATES.json"):
        """Initialize admin panel."""
        self.host = host
        self.port = port
        self.candidates_file = candidates_file
        self.voting_server = None
        self.server_thread = None
        self.voting_active = True
        self.last_status_update = 0

        # Setup logging
        self.setup_logging()
        self.logger.info("=" * 60)
        self.logger.info("BLOCKCHAIN VOTING SYSTEM - ADMIN SERVER STARTED")
        self.logger.info("=" * 60)

    def setup_logging(self):
        """Setup file-based logging."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"voting_server_{timestamp}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file)
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.log_file = log_file

    def initialize_server(self):
        """Initialize voting server."""
        print("\n🔧 Initializing Voting Server...")
        self.voting_server = VotingServer(self.host, self.port, self.candidates_file)

        if not self.voting_server.initialize():
            print("❌ Failed to initialize server")
            self.logger.error("Failed to initialize voting server")
            return False

        print("✅ Server initialized successfully")
        self.logger.info("Voting server initialized successfully")
        return True

    def start_server(self):
        """Start voting server in background thread."""
        if not self.initialize_server():
            return False

        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

        time.sleep(1)  # Give server time to start
        print("✅ Voting server started in background")
        self.logger.info("Voting server started (background thread)")
        return True

    def _run_server(self):
        """Run the voting server socket listener."""
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.host, self.port))
            server_socket.listen(5)

            self.voting_server.server_active = True
            self.logger.info(f"Socket server listening on {self.host}:{self.port}")

            while self.voting_active:
                try:
                    server_socket.settimeout(1.0)
                    client_socket, client_address = server_socket.accept()

                    # Handle client in thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    client_thread.start()

                except socket.timeout:
                    continue
                except Exception as e:
                    if self.voting_active:
                        self.logger.error(f"Client connection error: {e}")

        except Exception as e:
            self.logger.error(f"Server socket error: {e}")
        finally:
            try:
                server_socket.close()
            except:
                pass

    def _handle_client(self, client_socket, client_address):
        """Handle individual client connection."""
        try:
            data = client_socket.recv(4096).decode()
            if not data:
                return

            # Log request
            self.logger.info(f"Client {client_address}: {data[:100]}")

            # Handle request
            response = self.voting_server.handle_request(data)

            # Send response
            client_socket.send(json.dumps(response).encode())

            # Log response
            self.logger.info(f"Response: {response.get('status', 'unknown')}")

        except Exception as e:
            self.logger.error(f"Client error: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass

    def clear_screen(self):
        """Clear terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def get_server_status(self):
        """Get current server status."""
        status = {
            "running": self.voting_active,
            "host": self.host,
            "port": self.port,
            "total_votes": self.voting_server.blockchain.get_vote_count(),
            "total_blocks": len(self.voting_server.blockchain.chain),
            "candidates": len(self.voting_server.candidates),
            "chain_valid": self.voting_server.blockchain.validate_chain()["valid"],
            "uptime": datetime.now().strftime("%H:%M:%S"),
            "tokens_issued": self.voting_server.token_manager.total_tokens_issued,
            "tokens_used": self.voting_server.token_manager.tokens_used
        }
        return status

    def display_header(self):
        """Display admin panel header with server status."""
        status = self.get_server_status()

        self.clear_screen()
        print("=" * 70)
        print("  BLOCKCHAIN VOTING SYSTEM - ADMIN PANEL".center(70))
        print("=" * 70)
        print()

        # Status bar
        status_color = "🟢 ACTIVE" if status["running"] else "🔴 INACTIVE"
        print(f"  Server Status: {status_color}  |  Time: {status['uptime']}")
        print(f"  Host: {status['host']}:{status['port']}")
        print()

        # Statistics
        print("  📊 VOTING STATISTICS")
        print("  " + "-" * 66)
        print(f"    Total Votes:        {status['total_votes']}")
        print(f"    Total Blocks:       {status['total_blocks']}")
        print(f"    Candidates:         {status['candidates']}")
        print(f"    Chain Valid:        {'✓ YES' if status['chain_valid'] else '✗ NO'}")
        print(f"    Tokens Issued:      {status['tokens_issued']}")
        print(f"    Tokens Used:        {status['tokens_used']}")
        print()

    def display_results(self):
        """Display current voting results."""
        self.display_header()

        print("  📈 VOTING RESULTS")
        print("  " + "-" * 66)

        results = self.voting_server.blockchain.results()
        if not results:
            print("    No votes recorded yet")
        else:
            total = sum(results.values())
            for candidate, count in sorted(results.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total * 100) if total > 0 else 0
                bar_length = int(percentage / 5)
                bar = "█" * bar_length + "░" * (20 - bar_length)
                print(f"    {candidate:20} {count:3} votes [{bar}] {percentage:5.1f}%")

        print()

    def get_tokens(self):
        """Generate and display voting tokens."""
        self.display_header()

        print("  🎟️  TOKEN GENERATION")
        print("  " + "-" * 66)

        try:
            num_tokens = input("    How many tokens to generate? (1-100): ").strip()
            num_tokens = int(num_tokens)

            if num_tokens < 1 or num_tokens > 100:
                print("    ❌ Please enter a number between 1 and 100")
                input("    Press Enter to continue...")
                return

            tokens = self.voting_server.token_manager.generate_tokens(num_tokens)

            print()
            print("    ✅ Tokens generated successfully!")
            print()
            print("    TOKEN LIST:")
            print("    " + "-" * 62)

            for i, token in enumerate(tokens, 1):
                print(f"      {i:2}. {token}")

            print()

            # Option to save to file
            save = input("    Save tokens to file? (y/n): ").strip().lower()
            if save == 'y':
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                token_file = f"tokens_{timestamp}.txt"
                with open(token_file, 'w') as f:
                    f.write("VOTING TOKENS\n")
                    f.write("=" * 40 + "\n\n")
                    for i, token in enumerate(tokens, 1):
                        f.write(f"{i:2}. {token}\n")

                print(f"    ✅ Tokens saved to: {token_file}")
                self.logger.info(f"Tokens saved to file: {token_file} ({num_tokens} tokens)")

            self.logger.info(f"Generated {num_tokens} voting tokens")

        except ValueError:
            print("    ❌ Invalid input. Please enter a number.")

        input("    Press Enter to continue...")

    def stop_voting(self):
        """Stop voting and save results."""
        self.display_header()

        print("  🛑 STOP VOTING & SAVE RESULTS")
        print("  " + "-" * 66)
        print()

        confirm = input("    Are you sure? This will stop the server. (yes/no): ").strip().lower()

        if confirm != 'yes':
            print("    ❌ Cancelled")
            input("    Press Enter to continue...")
            return

        print()
        print("    ⏹️  Stopping server...")

        # Save results
        results = self.voting_server.blockchain.results()
        chain = self.voting_server.blockchain.chain

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"voting_results_{timestamp}.json"

        results_data = {
            "timestamp": timestamp,
            "total_votes": len(chain) - 1,
            "results": results,
            "blockchain_valid": self.voting_server.blockchain.validate_chain()["valid"],
            "candidates": self.voting_server.candidates
        }

        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2)

        print(f"    ✅ Results saved to: {results_file}")
        self.logger.info(f"Voting stopped. Results saved to {results_file}")

        # Display final results
        print()
        print("    📊 FINAL RESULTS:")
        print("    " + "-" * 62)

        total = sum(results.values()) if results else 0
        for candidate, count in sorted(results.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            print(f"      {candidate:20} {count:3} votes ({percentage:5.1f}%)")

        print()
        print(f"    📁 Log file: {self.log_file}")
        print()

        self.voting_active = False
        input("    Press Enter to exit...")

    def show_menu(self):
        """Display admin menu and get choice."""
        print()
        print("  MENU OPTIONS:")
        print("  " + "-" * 66)
        print("    1. Get tokens (generate voting tokens)")
        print("    2. Stop voting and save results")
        print("    3. View current results")
        print("    0. Exit without stopping server")
        print()

        choice = input("  Select option (0-3): ").strip()
        return choice

    def run_admin_loop(self):
        """Main admin panel loop."""
        while self.voting_active:
            self.display_header()

            choice = self.show_menu()

            if choice == '1':
                self.get_tokens()
            elif choice == '2':
                self.stop_voting()
            elif choice == '3':
                self.display_results()
                input("  Press Enter to continue...")
            elif choice == '0':
                print("\n  Exiting admin panel...")
                self.voting_active = False
            else:
                print("  ❌ Invalid option. Please try again.")
                time.sleep(1)

    def run(self):
        """Start admin server and panel."""
        if not self.start_server():
            return False

        print()
        input("🟢 Server is running. Press Enter to open admin panel...")

        try:
            self.run_admin_loop()
        except KeyboardInterrupt:
            print("\n\n⚠️  Keyboard interrupt detected")

        print("\n🛑 Shutting down server...")
        self.voting_active = False
        self.logger.info("Admin server shutdown")

        return True


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python admin_server.py PORT [CANDIDATES_FILE]")
        print("Example: python admin_server.py 5000 server/CANDIDATES.json")
        sys.exit(1)

    try:
        port = int(sys.argv[1])
        candidates_file = sys.argv[2] if len(sys.argv) > 2 else "server/CANDIDATES.json"
    except ValueError:
        print("❌ Invalid port number")
        sys.exit(1)

    admin = AdminServerPanel(port=port, candidates_file=candidates_file)
    admin.run()


if __name__ == "__main__":
    main()
