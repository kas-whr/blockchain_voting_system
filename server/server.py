import socket
import json
import sys
from blockchain import Blockchain

HOST = "0.0.0.0"
PORT = 5000

blockchain = Blockchain()

registered_voters = {}

CANDIDATES = []
CANDIDATES_DETAILS = []


def load_candidates(filename):
    """Load candidates from JSON file"""
    try:
        with open(filename, 'r') as f:
            candidates_data = json.load(f)
            if isinstance(candidates_data, list):
                names = [c.get("FullName") for c in candidates_data if "FullName" in c]
                return names, candidates_data
            else:
                print("Error: Invalid candidates file format")
                sys.exit(1)
    except FileNotFoundError:
        print(f"Error: Candidates file '{filename}' not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Error: Invalid JSON in candidates file")
        sys.exit(1)


def handle_request(request):
    action = request.get("action")

    if action == "register":
        first_name = request.get("first_name")
        last_name = request.get("last_name")

        if not first_name or not last_name:
            return {
                "status": "error",
                "message": "first_name and last_name are required"
            }

        voter_id = f"{first_name}_{last_name}"

        if voter_id in registered_voters:
            return {
                "status": "error",
                "message": f"{first_name} {last_name} is already registered"
            }

        registered_voters[voter_id] = {
            "first_name": first_name,
            "last_name": last_name
        }

        return {
            "status": "success",
            "message": "Registration successful",
            "voter_id": voter_id,
            "candidates": CANDIDATES
        }

    elif action == "vote":
        voter_id = request.get("voter_id")
        candidate = request.get("candidate")

        if not voter_id or not candidate:
            return {
                "status": "error",
                "message": "voter_id and candidate are required"
            }

        if voter_id not in registered_voters:
            return {
                "status": "error",
                "message": "Voter is not registered"
            }

        if candidate not in CANDIDATES:
            return {
                "status": "error",
                "message": "Invalid candidate",
                "allowed_candidates": CANDIDATES
            }

        block, message = blockchain.add_vote(voter_id, candidate)

        if block is None:
            return {
                "status": "error",
                "message": message
            }

        return {
            "status": "success",
            "message": message,
            "receipt": block["hash"],
            "block": block
        }

    elif action == "candidates":
        return {
            "status": "success",
            "candidates": CANDIDATES
        }

    elif action == "candidates_details":
        return {
            "status": "success",
            "candidates": CANDIDATES_DETAILS
        }

    elif action == "chain":
        return {
            "status": "success",
            "chain": blockchain.chain
        }

    elif action == "results":
        return {
            "status": "success",
            "results": blockchain.results()
        }

    elif action == "verify":
        receipt = request.get("receipt")

        if not receipt:
            return {
                "status": "error",
                "message": "receipt is required"
            }

        found, block = blockchain.verify_vote(receipt)

        if not found:
            return {
                "status": "error",
                "valid": False,
                "message": "Vote not found"
            }

        return {
            "status": "success",
            "valid": True,
            "message": "Vote exists in blockchain",
            "block": block
        }

    elif action == "validate":
        return {
            "status": "success",
            "valid": blockchain.validate_chain()
        }

    else:
        return {
            "status": "error",
            "message": "Unknown action"
        }


def start_server(port, candidates_file):
    global CANDIDATES, CANDIDATES_DETAILS

    CANDIDATES, CANDIDATES_DETAILS = load_candidates(candidates_file)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, port))
    server_socket.listen()

    print(f"Socket server is running on {HOST}:{port}")
    print(f"Loaded {len(CANDIDATES)} candidates: {', '.join(CANDIDATES)}")

    while True:
        client_socket, address = server_socket.accept()
        print(f"Connected by {address}")

        try:
            data = client_socket.recv(4096).decode()

            if not data:
                continue

            request = json.loads(data)
            response = handle_request(request)

        except json.JSONDecodeError:
            response = {
                "status": "error",
                "message": "Invalid JSON"
            }

        except Exception as error:
            response = {
                "status": "error",
                "message": str(error)
            }

        # Properly send response (handle large payloads)
        response_json = json.dumps(response)
        response_bytes = response_json.encode()

        # Send response size first, then data
        client_socket.sendall(response_bytes)
        client_socket.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python server.py PORT CANDIDATES_FILE.json")
        print("Example: python server.py 5000 CANDIDATES.json")
        sys.exit(1)

    try:
        port = int(sys.argv[1])
    except ValueError:
        print("Error: PORT must be an integer")
        sys.exit(1)

    candidates_file = sys.argv[2]

    start_server(port, candidates_file)
