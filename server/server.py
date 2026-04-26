import socket
import json
import uuid
from blockchain import Blockchain

HOST = "127.0.0.1"
PORT = 5000

blockchain = Blockchain()

registered_voters = {}

ALLOWED_CANDIDATES = ["Daria", "Ivan", "Alice"]


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

        voter_id = str(uuid.uuid4())

        registered_voters[voter_id] = {
            "first_name": first_name,
            "last_name": last_name
        }

        return {
            "status": "success",
            "message": "Registration successful",
            "voter_id": voter_id,
            "candidates": ALLOWED_CANDIDATES
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

        if candidate not in ALLOWED_CANDIDATES:
            return {
                "status": "error",
                "message": "Invalid candidate",
                "allowed_candidates": ALLOWED_CANDIDATES
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
            "candidates": ALLOWED_CANDIDATES
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


def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()

    print(f"Socket server is running on {HOST}:{PORT}")

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

        client_socket.send(json.dumps(response).encode())
        client_socket.close()


if __name__ == "__main__":
    start_server()