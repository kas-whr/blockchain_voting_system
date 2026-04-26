import requests

SERVER_URL = "http://127.0.0.1:5000"

session = requests.Session()
session.trust_env = False

current_voter_id = None
has_voted = False


def print_response(response):
    print("STATUS:", response.status_code)

    try:
        print(response.json())
    except requests.exceptions.JSONDecodeError:
        print("Server returned non-JSON response:")
        print(response.text)


def register():
    global current_voter_id

    name = input("Enter your name: ")
    age = input("Enter your age: ")

    response = session.post(
        f"{SERVER_URL}/register",
        json={
            "name": name,
            "age": age
        }
    )

    data = response.json()

    if response.status_code == 200:
        current_voter_id = data["voter_id"]
        print("Registration successful!")
        print("Your terminal voter ID:", current_voter_id)
        print("Available candidates:", data["candidates"])
    else:
        print(data)


def submit_vote():
    global has_voted

    if current_voter_id is None:
        print("You must register first.")
        return

    if has_voted:
        print("This terminal has already voted.")
        return

    candidates_response = session.get(f"{SERVER_URL}/candidates")
    candidates = candidates_response.json()

    print("Available candidates:")
    for candidate in candidates:
        print("-", candidate)

    candidate = input("Enter candidate name: ")

    response = session.post(
        f"{SERVER_URL}/vote",
        json={
            "voter_id": current_voter_id,
            "candidate": candidate
        }
    )

    if response.status_code == 200:
        has_voted = True

    print_response(response)


def show_chain():
    response = session.get(f"{SERVER_URL}/chain")
    print_response(response)


def show_results():
    response = session.get(f"{SERVER_URL}/results")
    print_response(response)


def verify_vote():
    receipt = input("Enter receipt hash: ")
    response = session.get(f"{SERVER_URL}/verify/{receipt}")
    print_response(response)


def validate_chain():
    response = session.get(f"{SERVER_URL}/validate")
    print_response(response)


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