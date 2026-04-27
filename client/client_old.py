import socket
import json
import sys
import os

HOST = None
PORT = None

current_voter_name = None
current_voter_id = None
has_voted = False


def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title):
    """Print a formatted header"""
    clear_screen()
    print("=" * 50)
    print(f"  {title.center(46)}")
    print("=" * 50)


def print_menu(options):
    """Print formatted menu options"""
    for key, value in options.items():
        print(f"  {key}. {value}")
    print()


def get_default_filename(option):
    """Generate default filename based on voter name and option"""
    if current_voter_name:
        name_formatted = current_voter_name.replace(" ", "_")
        return f"{name_formatted}_{option}.txt"
    return f"{option}.txt"


def save_to_file(content, option, default_yes=False):
    """Save content to file with user-provided or default filename

    Args:
        content: Data to save
        option: Type of data (blockchain, results, receipt, etc)
        default_yes: If True, default is Y; if False, default is N
    """
    # Ask to save with appropriate format: Y/n or y/N
    if default_yes:
        prompt = "  Save to file? (Y/n): "
    else:
        prompt = "  Save to file? (y/N): "

    save_choice = input(prompt).strip().upper()

    # Handle empty input (use default)
    if not save_choice:
        save_choice = 'Y' if default_yes else 'N'

    if save_choice != 'Y':
        print("  Cancelled.")
        return

    # Only ask for filename after confirming to save
    default_filename = get_default_filename(option)
    filename = input(f"  Enter filename (default: {default_filename}): ").strip()

    if not filename:
        filename = default_filename

    if not filename.endswith('.txt'):
        filename += '.txt'

    try:
        with open(filename, 'w') as f:
            if isinstance(content, dict):
                f.write(json.dumps(content, indent=2))
            else:
                f.write(str(content))
        print(f"  ✓ Saved to {filename}")
    except Exception as e:
        print(f"  ✗ Error saving file: {str(e)}")


def send_request(request):
    """Send request to server"""
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(10)
        client_socket.connect((HOST, PORT))

        client_socket.send(json.dumps(request).encode())

        # Receive all data (handle large responses)
        response_data = b""
        while True:
            try:
                chunk = client_socket.recv(8192)
                if not chunk:
                    break
                response_data += chunk
            except socket.timeout:
                break

        client_socket.close()

        if not response_data:
            return {"status": "error", "message": "No response from server"}

        return json.loads(response_data.decode())
    except socket.timeout:
        return {"status": "error", "message": "Connection timeout"}
    except ConnectionRefusedError:
        return {"status": "error", "message": "Connection refused"}
    except json.JSONDecodeError as e:
        return {"status": "error", "message": f"Invalid JSON response: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def connect_to_server():
    """Initial connection menu"""
    global HOST, PORT

    print_header("BLOCKCHAIN VOTING SYSTEM")
    print()
    print("  1. Connect to Server")
    print("  0. Exit")
    print()

    choice = input("  Choose option: ").strip()

    if choice == "1":
        print_header("CONNECT TO SERVER")

        host = input("  Enter server IP (default: localhost): ").strip()
        HOST = host if host else "localhost"

        port_str = input("  Enter server PORT (default: 5000): ").strip()
        try:
            PORT = int(port_str) if port_str else 5000
        except ValueError:
            print("  Error: Invalid port number")
            input("  Press Enter to try again...")
            return connect_to_server()

        test_request = {"action": "candidates"}
        response = send_request(test_request)

        if response.get("status") == "success":
            print_header("CONNECTED")
            print(f"  Successfully connected to {HOST}:{PORT}")
            print()
            print(f"  Available candidates:")
            for candidate in response.get("candidates", []):
                print(f"    - {candidate}")
            print()
            input("  Press Enter to continue...")
            return True
        else:
            print_header("CONNECTION FAILED")
            print(f"  Error: {response.get('message')}")
            print()
            input("  Press Enter to try again...")
            return connect_to_server()

    elif choice == "0":
        print("  Goodbye!")
        sys.exit(0)
    else:
        print("  Invalid option")
        input("  Press Enter to try again...")
        return connect_to_server()


def register():
    global current_voter_name, current_voter_id

    if current_voter_name is not None:
        print_header("ERROR")
        print()
        print("  You are already registered!")
        print(f"  Voter: {current_voter_name}")
        print()
        input("  Press Enter to continue...")
        return

    print_header("VOTER REGISTRATION")
    print()

    first_name = input("  Enter your first name: ").strip()
    if not first_name:
        print("  Error: First name cannot be empty")
        input("  Press Enter to try again...")
        return

    last_name = input("  Enter your last name: ").strip()
    if not last_name:
        print("  Error: Last name cannot be empty")
        input("  Press Enter to try again...")
        return

    response = send_request({
        "action": "register",
        "first_name": first_name,
        "last_name": last_name
    })

    print_header("REGISTRATION RESULT")
    print()

    if response["status"] == "success":
        current_voter_name = f"{first_name} {last_name}"
        current_voter_id = response["voter_id"]
        print(f"  Registration successful!")
        print(f"  Welcome, {current_voter_name}!")
        print()
        print("  Available candidates:")
        for candidate in response.get("candidates", []):
            print(f"    - {candidate}")
    else:
        print(f"  Error: {response.get('message')}")

    print()
    input("  Press Enter to continue...")


def view_candidates():
    """View candidates with descriptions - with loop"""
    while True:
        print_header("VIEW CANDIDATES")
        print()

        response = send_request({
            "action": "candidates_details"
        })

        if response.get("status") != "success":
            print(f"  Error: {response.get('message')}")
            print()
            input("  Press Enter to continue...")
            return

        candidates = response.get("candidates", [])

        print("  Select a candidate number to view details:")
        print()
        for i, candidate in enumerate(candidates, 1):
            print(f"    {i}. {candidate.get('FullName')}")

        print()
        print("  (Enter 0 to go back to main menu)")
        print()
        choice = input("  Enter candidate number: ").strip()

        try:
            choice_idx = int(choice) - 1
            if choice == "0":
                return
            if 0 <= choice_idx < len(candidates):
                candidate = candidates[choice_idx]
                print_header(f"CANDIDATE: {candidate.get('FullName')}")
                print()
                print(f"  {candidate.get('FullName')}")
                print()
                print(f"  {candidate.get('Description', 'No description available')}")
                print()
                input("  Press Enter to continue viewing candidates...")
            else:
                print("  Invalid candidate number")
                print()
                input("  Press Enter to try again...")
        except ValueError:
            print("  Invalid input")
            print()
            input("  Press Enter to try again...")


def submit_vote():
    global has_voted

    if current_voter_name is None:
        print_header("ERROR")
        print()
        print("  You must register first.")
        print()
        input("  Press Enter to continue...")
        return

    if has_voted:
        print_header("ERROR")
        print()
        print("  You have already voted.")
        print()
        input("  Press Enter to continue...")
        return

    print_header("SUBMIT YOUR VOTE")
    print()

    candidates_response = send_request({
        "action": "candidates"
    })

    if candidates_response.get("status") != "success":
        print(f"  Error: {candidates_response.get('message')}")
        print()
        input("  Press Enter to continue...")
        return

    candidates = candidates_response["candidates"]

    print("  Available candidates:")
    for i, candidate in enumerate(candidates, 1):
        print(f"    {i}. {candidate}")

    print()
    candidate_choice = input("  Enter candidate number or name: ").strip()

    try:
        candidate_idx = int(candidate_choice) - 1
        if 0 <= candidate_idx < len(candidates):
            candidate = candidates[candidate_idx]
        else:
            candidate = candidate_choice
    except ValueError:
        candidate = candidate_choice

    response = send_request({
        "action": "vote",
        "voter_id": current_voter_id,
        "candidate": candidate
    })

    print_header("VOTE SUBMISSION RESULT")
    print()

    if response["status"] == "success":
        has_voted = True
        receipt = response.get('receipt')
        print(f"  Your vote has been accepted!")
        print()
        print(f"  Receipt (hash):")
        print(f"  {receipt}")
        print()
        print(f"  Save this for vote verification.")
        print()

        save_to_file(receipt, "receipt", default_yes=True)
    else:
        print(f"  Error: {response.get('message')}")

    print()
    input("  Press Enter to continue...")


def show_chain():
    print_header("BLOCKCHAIN")
    print()

    response = send_request({
        "action": "chain"
    })

    if response["status"] == "success":
        chain = response["chain"]
        print(f"  Total blocks: {len(chain)}")
        print()
        for i, block in enumerate(chain):
            print(f"  Block {i}:")
            print(f"    Hash: {block['hash'][:16]}...")
            print(f"    Candidate: {block['candidate']}")
            print()

        save_to_file(response["chain"], "blockchain", default_yes=False)
    else:
        print(f"  Error: {response.get('message')}")

    print()
    input("  Press Enter to continue...")


def show_results():
    print_header("VOTING RESULTS")
    print()

    response = send_request({
        "action": "results"
    })

    if response["status"] == "success":
        results = response["results"]
        if not results:
            print("  No votes yet.")
        else:
            total_votes = sum(results.values())
            print(f"  Total votes: {total_votes}")
            print()
            for candidate, count in sorted(results.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_votes * 100) if total_votes > 0 else 0
                bar = "█" * int(percentage / 5)
                print(f"  {candidate:20} {count:3} votes [{bar:20}] {percentage:5.1f}%")

        print()
        save_to_file(response["results"], "results", default_yes=False)
    else:
        print(f"  Error: {response.get('message')}")

    print()
    input("  Press Enter to continue...")


def verify_vote():
    print_header("VERIFY VOTE")
    print()

    receipt = input("  Enter receipt hash: ").strip()

    if not receipt:
        print("  Error: Receipt cannot be empty")
        print()
        input("  Press Enter to continue...")
        return

    response = send_request({
        "action": "verify",
        "receipt": receipt
    })

    print_header("VERIFICATION RESULT")
    print()

    if response.get("valid"):
        block = response.get("block", {})
        print(f"  ✓ Vote found in blockchain!")
        print(f"  Candidate: {block.get('candidate')}")
        print(f"  Timestamp: {block.get('timestamp')}")
    else:
        print(f"  ✗ Vote not found in blockchain")

    print()
    input("  Press Enter to continue...")


def validate_chain():
    print_header("BLOCKCHAIN VALIDATION")
    print()

    # First, get the chain to show validation process
    chain_response = send_request({"action": "chain"})

    if chain_response.get("status") != "success":
        print(f"  Error: {chain_response.get('message')}")
        print()
        input("  Press Enter to continue...")
        return

    chain = chain_response.get("chain", [])

    print(f"  Validating blockchain with {len(chain)} blocks...")
    print()

    # Show validation steps
    print("  VALIDATION PROCESS:")
    print("  " + "-" * 50)

    all_valid = True

    # Step 1: Check chain length
    print(f"  ✓ Step 1: Chain loaded ({len(chain)} blocks)")

    # Step 2: Validate each block hash
    print(f"\n  ✓ Step 2: Validating block hashes...")
    for i in range(1, len(chain)):
        block = chain[i]
        index = block["index"]

        # Reconstruct hash to verify
        data = (
            str(block["index"]) +
            str(block["timestamp"]) +
            block["voter_id_hash"] +
            block["candidate"] +
            block["previous_hash"]
        )
        import hashlib
        calculated_hash = hashlib.sha256(data.encode()).hexdigest()

        if calculated_hash == block["hash"]:
            status = "✓"
        else:
            status = "✗"
            all_valid = False

        candidate_display = block["candidate"][:20].ljust(20)
        print(f"      {status} Block {i:3d} | {candidate_display} | Hash OK")

    # Step 3: Validate hash chain links
    print(f"\n  ✓ Step 3: Validating chain links (previous_hash references)...")
    chain_links_valid = True
    for i in range(1, len(chain)):
        current = chain[i]
        previous = chain[i - 1]

        if current["previous_hash"] == previous["hash"]:
            status = "✓"
        else:
            status = "✗"
            chain_links_valid = False
            all_valid = False

        print(f"      {status} Block {i:3d} → Block {i-1:3d} link verified")

    # Step 4: Check for duplicate voters (vote deduplication)
    print(f"\n  ✓ Step 4: Checking for duplicate voters...")
    voter_hashes = [block["voter_id_hash"] for block in chain[1:]]  # Skip genesis
    unique_voters = len(set(voter_hashes))
    total_votes = len(voter_hashes)

    if unique_voters == total_votes:
        print(f"      ✓ No duplicates found")
        print(f"        Total votes: {total_votes}")
        print(f"        Unique voters: {unique_voters}")
    else:
        duplicates = total_votes - unique_voters
        print(f"      ✗ Duplicates found!")
        print(f"        Total votes: {total_votes}")
        print(f"        Unique voters: {unique_voters}")
        print(f"        Duplicate count: {duplicates}")
        all_valid = False

    # Step 5: Server-side validation
    print(f"\n  ✓ Step 5: Server-side validation...")
    response = send_request({"action": "validate"})
    server_valid = response.get("valid")

    if server_valid:
        print(f"      ✓ Server confirms blockchain is valid")
    else:
        print(f"      ✗ Server reports blockchain is invalid")
        all_valid = False

    # Final Result
    print()
    print("  " + "="*50)
    if all_valid:
        print("  ✓ VALIDATION SUCCESSFUL")
        print("    Blockchain integrity confirmed!")
        print("    All blocks are valid and properly linked.")
    else:
        print("  ✗ VALIDATION FAILED")
        print("    Blockchain has integrity issues!")
    print("  " + "="*50)

    # Summary Statistics
    print()
    print("  SUMMARY STATISTICS:")
    print("  " + "-" * 50)
    print(f"  Total blocks: {len(chain)}")
    print(f"  Vote blocks: {len(chain) - 1}")  # Exclude genesis
    print(f"  Unique voters: {unique_voters}")
    print(f"  Genesis block: ✓ (index 0)")
    print()

    input("  Press Enter to continue...")


def show_main_menu():
    """Main menu loop"""
    while True:
        print_header("BLOCKCHAIN VOTING SYSTEM")
        print(f"  Connected to: {HOST}:{PORT}")
        if current_voter_name:
            print(f"  Voter: {current_voter_name}")
            print(f"  Voted: {'Yes' if has_voted else 'No'}")
        print()

        options = {
            "1": "Register as Voter",
            "2": "View Candidates",
            "3": "Submit Vote",
            "4": "Show Blockchain",
            "5": "Show Results",
            "6": "Verify Vote",
            "7": "Validate Blockchain",
            "0": "Disconnect & Exit"
        }

        print_menu(options)

        choice = input("  Choose option: ").strip()

        if choice == "1":
            register()
        elif choice == "2":
            view_candidates()
        elif choice == "3":
            submit_vote()
        elif choice == "4":
            show_chain()
        elif choice == "5":
            show_results()
        elif choice == "6":
            verify_vote()
        elif choice == "7":
            validate_chain()
        elif choice == "0":
            print_header("GOODBYE")
            print()
            print("  Thank you for voting!")
            print()
            break
        else:
            print("  Invalid option")
            input("  Press Enter to try again...")


if __name__ == "__main__":
    if connect_to_server():
        show_main_menu()
