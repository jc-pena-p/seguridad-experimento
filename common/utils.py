import hmac, hashlib, time, jwt

def hmac_signature(secret: str, body_bytes: bytes) -> str:
    return hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()

def verify_hmac(secret: str, body_bytes: bytes, given: str) -> bool:
    expect = hmac_signature(secret, body_bytes)
    return hmac.compare_digest(expect, given or "")

def now_ms() -> int:
    return int(time.time() * 1000)

def sign_jwt(payload: dict, secret: str, ttl_seconds: int) -> str:
    payload = payload.copy()
    payload["iat"] = int(time.time())
    payload["exp"] = int(time.time()) + int(ttl_seconds)
    return jwt.encode(payload, secret, algorithm="HS256")

def verify_jwt(token: str, secret: str) -> dict:
    return jwt.decode(token, secret, algorithms=["HS256"])
