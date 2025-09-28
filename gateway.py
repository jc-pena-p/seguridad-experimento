import redis
import os, time, uuid, requests, jwt, hmac, hashlib
from flask import Flask, request, jsonify

# Config
HMAC_SECRET = os.getenv("HMAC_SECRET", "demo-hmac-secret")
JWT_SECRET  = os.getenv("JWT_SECRET", "demo-jwt-secret")
AUDIT_URL   = os.getenv("AUDIT_URL", "http://audit:5003/audit")
REDIS_HOST  = os.getenv("REDIS_HOST", "redis")
BLOCK_THRESHOLD = int(os.getenv("BLOCK_THRESHOLD", 3))
BLOCK_TTL = int(os.getenv("BLOCK_TTL", 300))

rdb = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

app = Flask(__name__)

def audit(event: dict):
    try:
        ev = {"ts": int(time.time()*1000)} | event
        requests.post(AUDIT_URL, json=ev, timeout=3)
    except Exception:
        pass

def verify_hmac(secret: str, body: str, sig: str) -> bool:
    mac = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, sig or "")

def fail_attempt(client_id: str) -> int:
    cnt = rdb.incr(f"fail:{client_id}")
    rdb.expire(f"fail:{client_id}", BLOCK_TTL)
    return cnt

def blocked(client_id: str) -> bool:
    return rdb.exists(f"blk:{client_id}") == 1

@app.put("/orders/<order_id>/status")
def update_status(order_id):
    cid = request.headers.get("X-Correlation-Id", str(uuid.uuid4()))
    client_id = request.headers.get("X-Client-Id", "unknown")
    sig = request.headers.get("X-Body-Signature")
    body = request.data.decode()

    if blocked(client_id):
        audit({"event": "gateway_blocked", "client_id": client_id,
               "cid": cid, "order": order_id, "result": 403})
        return jsonify({"error": "client temporarily blocked"}), 403

    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    try:
        claims = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception as e:
        cnt = fail_attempt(client_id)
        audit({"event": "jwt_invalid", "client_id": client_id,
               "cid": cid, "order": order_id, "result": 401,
               "reason": str(e), "attempts": cnt})
        if cnt >= BLOCK_THRESHOLD:
            rdb.setex(f"blk:{client_id}", BLOCK_TTL, "1")
            audit({"event": "block_applied", "client_id": client_id,
                   "cid": cid, "order": order_id, "result": 403,
                   "reason": "threshold"})
        return jsonify({"error": "invalid token"}), 401

    if not verify_hmac(HMAC_SECRET, body, sig):
        cnt = fail_attempt(client_id)
        audit({"event": "hmac_invalid", "client_id": client_id,
               "cid": cid, "order": order_id, "result": 401,
               "attempts": cnt})
        if cnt >= BLOCK_THRESHOLD:
            rdb.setex(f"blk:{client_id}", BLOCK_TTL, "1")
            audit({"event": "block_applied", "client_id": client_id,
                   "cid": cid, "order": order_id, "result": 403,
                   "reason": "threshold"})
        return jsonify({"error": "invalid signature"}), 401

    # Reenviar a LogisticsService
    try:
        res = requests.put("http://logistics:5002/orders/%s/status" % order_id,
                           headers={"X-Correlation-Id": cid}, data=body, timeout=5)
        if res.status_code == 200:
            audit({"event": "status_update_forwarded", "client_id": client_id,
                   "cid": cid, "order": order_id, "user": claims.get("sub"),
                   "result": 200})
        else:
            audit({"event": "upstream_error", "client_id": client_id,
                   "cid": cid, "order": order_id, "result": res.status_code})
        return (res.text, res.status_code, res.headers.items())
    except Exception as e:
        audit({"event": "upstream_unreachable", "client_id": client_id,
               "cid": cid, "order": order_id, "result": 502,
               "reason": str(e)})
        return jsonify({"error": "logistics unavailable"}), 502

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, ssl_context=("certs/server.crt", "certs/server.key"))
