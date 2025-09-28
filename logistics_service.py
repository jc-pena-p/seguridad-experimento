from flask import Flask, request, jsonify
from sqlalchemy import create_engine
import os, requests, time
from common.logging_middleware import json_logger

DB_URL = os.getenv("LOG_DB", "sqlite:////data/logistics.db")
AUDIT_URL = os.getenv("AUDIT_URL", "http://audit:5003/audit")

engine = create_engine(DB_URL, future=True)
with engine.begin() as con:
    con.exec_driver_sql("""
    CREATE TABLE IF NOT EXISTS deliveries(
      order_id TEXT PRIMARY KEY,
      status TEXT NOT NULL,
      updated_at INTEGER NOT NULL
    )""")

app = Flask(__name__)
json_logger(app, "logistics")

@app.put("/orders/<order_id>/status")
def update_status(order_id):
    body = request.get_json(force=True)
    status = body.get("status", "unknown")
    ts = int(time.time()*1000)
    with engine.begin() as con:
        con.exec_driver_sql(
            "INSERT INTO deliveries(order_id,status,updated_at) VALUES(:id,:st,:ts) "
            "ON CONFLICT(order_id) DO UPDATE SET status=:st, updated_at=:ts",
            {"id": order_id, "st": status, "ts": ts}
        )
    try:
        requests.post(AUDIT_URL, json={"ts": ts, "event": "update_status", "order_id": order_id, "status": status})
    except Exception:
        pass
    return jsonify({"ok": True, "order_id": order_id, "status": status})

@app.get("/orders/<order_id>")
def get_order(order_id):
    r = engine.connect().exec_driver_sql("SELECT order_id,status,updated_at FROM deliveries WHERE order_id=:id", {"id": order_id}).first()
    if not r: return jsonify({"error":"not found"}), 404
    return jsonify({"order_id": r[0], "status": r[1], "updated_at": r[2]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
