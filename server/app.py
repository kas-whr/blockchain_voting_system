from flask import Flask, request, jsonify
from flask_cors import CORS
from blockchain import Blockchain
import uuid

app = Flask(__name__)
CORS(app)

blockchain = Blockchain()

registered_voters = {}

ALLOWED_CANDIDATES = ["Daria", "Ivan", "Alice"]


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    name = data.get("name")
    age = data.get("age")

    if not name or not age:
        return jsonify({"error": "name and age are required"}), 400

    voter_id = str(uuid.uuid4())

    registered_voters[voter_id] = {
        "name": name,
        "age": age
    }

    return jsonify({
        "message": "Registration successful",
        "voter_id": voter_id,
        "candidates": ALLOWED_CANDIDATES
    })


@app.route("/vote", methods=["POST"])
def vote():
    data = request.get_json()

    voter_id = data.get("voter_id")
    candidate = data.get("candidate")

    if not voter_id or not candidate:
        return jsonify({"error": "voter_id and candidate are required"}), 400

    if voter_id not in registered_voters:
        return jsonify({"error": "Voter is not registered"}), 403

    if candidate not in ALLOWED_CANDIDATES:
        return jsonify({
            "error": "Invalid candidate",
            "allowed_candidates": ALLOWED_CANDIDATES
        }), 400

    block, message = blockchain.add_vote(voter_id, candidate)

    if block is None:
        return jsonify({"error": message}), 400

    return jsonify({
        "message": message,
        "receipt": block["hash"],
        "block": block
    })


@app.route("/candidates", methods=["GET"])
def candidates():
    return jsonify(ALLOWED_CANDIDATES)


@app.route("/chain", methods=["GET"])
def chain():
    return jsonify(blockchain.chain)


@app.route("/results", methods=["GET"])
def results():
    return jsonify(blockchain.results())


@app.route("/verify/<receipt>", methods=["GET"])
def verify(receipt):
    found, block = blockchain.verify_vote(receipt)

    if not found:
        return jsonify({"valid": False, "message": "Vote not found"}), 404

    return jsonify({
        "valid": True,
        "message": "Vote exists in blockchain",
        "block": block
    })


@app.route("/validate", methods=["GET"])
def validate():
    return jsonify({
        "valid": blockchain.validate_chain()
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)