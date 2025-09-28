import os
from flask import Flask, request, jsonify
from common.utils import sign_jwt
from common.logging_middleware import json_logger

app = Flask(__name__)
json_logger(app, "auth")

JWT_SECRET = os.getenv("JWT_SECRET", "demo-super-secret")
TTL = int(os.getenv("JWT_TTL_SECONDS", "900"))

@app.post("/token")
def token():
    data = request.get_json(force=True, silent=True) or {}
    user = data.get("user", "guest")
    roles = data.get("roles", ["operator"])
    payload = {"sub": user, "roles": roles}
    token = sign_jwt(payload, JWT_SECRET, TTL)
    return jsonify({"access_token": token})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
