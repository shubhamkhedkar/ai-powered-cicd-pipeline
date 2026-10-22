"""Sample Flask API."""

from flask import Flask, jsonify, request

app = Flask(__name__)
ITEMS: dict[int, dict] = {}


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.get("/items")
def list_items():
    return jsonify(list(ITEMS.values()))


@app.post("/items")
def create_item():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    if not name or not isinstance(name, str):
        return jsonify(error="name is required"), 400
    item_id = len(ITEMS) + 1
    ITEMS[item_id] = {"id": item_id, "name": name}
    return jsonify(ITEMS[item_id]), 201


@app.get("/items/<int:item_id>")
def get_item(item_id: int):
    item = ITEMS.get(item_id)
    if item is None:
        return jsonify(error="not found"), 404
    return jsonify(item)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
