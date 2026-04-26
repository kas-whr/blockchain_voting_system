import requests

SERVER_URL = "http://127.0.0.1:5000"

session = requests.Session()
session.trust_env = False

def print_response(response):
    print("STATUS:", response.status_code)

    try:
        print(response.json())
    except session.exceptions.JSONDecodeError:
        print("Server returned non-JSON response:")
        print(response.text)


def submit_vote():
    voter_id = input("Enter voter ID: ")
    candidate = input("Enter candidate name: ")

    response = session.post(
        f"{SERVER_URL}/vote",
        json={
            "voter_id": voter_id,
            "candidate": candidate
        }
    )

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
    print("\n1. Submit vote")
    print("2. Show blockchain")
    print("3. Show results")
    print("4. Verify vote")
    print("5. Validate blockchain")
    print("0. Exit")

    choice = input("Choose option: ")

    if choice == "1":
        submit_vote()
    elif choice == "2":
        show_chain()
    elif choice == "3":
        show_results()
    elif choice == "4":
        verify_vote()
    elif choice == "5":
        validate_chain()
    elif choice == "0":
        break
    else:
        print("Invalid option")