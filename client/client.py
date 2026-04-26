import socket
import json

HOST = "127.0.0.1"
PORT = 5000

current_voter_id = None
has_voted = False


def send_request(request):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))

    client_socket.send(json.dumps(request).encode())

    response = client_socket.recv(8192).decode()
    client_socket.close()

    return json.loads(response)


def register():
    global current_voter_id

    first_name = input("Enter your first name: ")
    last_name = input("Enter your last name: ")

    response = send_request({
        "action": "register",
        "first_name": first_name,
        "last_name": last_name
    })

    print(response)

    if response["status"] == "success":
        current_voter_id = response["voter_id"]
        print("Your terminal voter ID:", current_voter_id)


def submit_vote():
    global has_voted

    if current_voter_id is None:
        print("You must register first.")
        return

    if has_voted:
        print("This terminal has already voted.")
        return

    candidates_response = send_request({
        "action": "candidates"
    })

    candidates = candidates_response["candidates"]

    print("Available candidates:")
    for candidate in candidates:
        print("-", candidate)

    candidate = input("Enter candidate name: ")

    response = send_request({
        "action": "vote",
        "voter_id": current_voter_id,
        "candidate": candidate
    })

    print(response)

    if response["status"] == "success":
        has_voted = True


def show_chain():
    response = send_request({
        "action": "chain"
    })

    print(response)


def show_results():
    response = send_request({
        "action": "results"
    })

    print(response)


def verify_vote():
    receipt = input("Enter receipt hash: ")

    response = send_request({
        "action": "verify",
        "receipt": receipt
    })

    print(response)


def validate_chain():
    response = send_request({
        "action": "validate"
    })

    print(response)


while True:
    print("\n1. Register")
    print("2. Submit vote")
    print("3. Show blockchain")
    print("4. Show results")
    print("5. Verify vote")
    print("6. Validate blockchain")
    print("0. Exit")

    choice = input("Choose option: ")

    if choice == "1":
        register()
    elif choice == "2":
        submit_vote()
    elif choice == "3":
        show_chain()
    elif choice == "4":
        show_results()
    elif choice == "5":
        verify_vote()
    elif choice == "6":
        validate_chain()
    elif choice == "0":
        break
    else:
        print("Invalid option")