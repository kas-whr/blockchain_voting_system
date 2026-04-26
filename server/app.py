from flask import Flask, request, jsonify
from flask_cors import CORS
from blockchain import Blockchain

app = Flask(__name__)
CORS(app)

blockchain = Blockchain()


@app.route("/vote", methods=["POST"])
def vote():
    data = request.get_json()

    voter_id = data.get("voter_id")
    candidate = data.get("candidate")

    if not voter_id or not candidate:
        return jsonify({"error": "voter_id and candidate are required"}), 400

    block, message = blockchain.add_vote(voter_id, candidate)

    if block is None:
        return jsonify({"error": message}), 400

    return jsonify({
        "message": message,
        "receipt": block["hash"],
        "block": block
    })


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