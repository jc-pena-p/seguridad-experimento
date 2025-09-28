from flask import Flask, request, jsonify
from sqlalchemy import create_engine
import hashlib, json, os
from common.logging_middleware import json_logger

DB_URL = os.getenv("AUDIT_DB", "sqlite:////data/audit.db")
engine = create_engine(DB_URL, future=True)

# Esquema de la bitácora (append-only con hash encadenado)
with engine.begin() as con:
    con.exec_driver_sql("""
    CREATE TABLE IF NOT EXISTS audit_ledger(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts INTEGER NOT NULL,
      event TEXT NOT NULL,
      prev_hash TEXT,
      cur_hash TEXT NOT NULL
    )""")

def chain_hash(prev_hash: str, event: dict) -> str:
    m = hashlib.sha256()
    m.update((prev_hash or "").encode())
    m.update(json.dumps(event, sort_keys=True).encode())
    return m.hexdigest()

app = Flask(__name__)
json_logger(app, "audit")

@app.post("/audit")
def audit():
    event = request.get_json(force=True)
    with engine.begin() as con:
        prev = con.exec_driver_sql(
            "SELECT cur_hash FROM audit_ledger ORDER BY id DESC LIMIT 1"
        ).first()
        prev_hash = prev[0] if prev else None
        cur_hash = chain_hash(prev_hash, event)
        con.exec_driver_sql(
            "INSERT INTO audit_ledger(ts,event,prev_hash,cur_hash) VALUES(:ts,:ev,:ph,:ch)",
            {"ts": event.get("ts"), "ev": json.dumps(event), "ph": prev_hash, "ch": cur_hash}
        )
    return jsonify({"ok": True})

@app.get("/audit")
def list_events():
    rows = engine.connect().exec_driver_sql(
        "SELECT id, ts, event, prev_hash, cur_hash FROM audit_ledger ORDER BY id DESC"
    ).fetchall()
    out = []
    for (id_, ts, ev, prevh, curh) in rows:
        out.append({
            "id": id_,
            "ts": ts,
            "event": json.loads(ev),
            "prev_hash": prevh,
            "cur_hash": curh
        })
    return jsonify(out)

@app.get("/audit/verify")
def verify():
    rows = engine.connect().exec_driver_sql(
        "SELECT id,event,prev_hash,cur_hash FROM audit_ledger ORDER BY id"
    ).fetchall()
    prev = None
    ok = True
    for r in rows:
        ev = json.loads(r[1])
        expected = chain_hash(prev, ev)
        if expected != r[3]:
            ok = False
            break
        prev = r[3]
    return jsonify({"valid": ok, "entries": len(rows)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)
