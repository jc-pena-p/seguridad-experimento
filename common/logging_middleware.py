import json, time
from flask import request

def json_logger(app, service_name: str):
    @app.before_request
    def _start():
        request._start_ts = time.time()

    @app.after_request
    def _end(resp):
        cid = request.headers.get("X-Correlation-Id", "-")
        log = {
            "ts": int(time.time()*1000),
            "service": service_name,
            "cid": cid,
            "method": request.method,
            "path": request.path,
            "status": resp.status_code,
            "ms": int((time.time() - getattr(request,"_start_ts",time.time()))*1000)
        }
        print(json.dumps(log), flush=True)
        return resp
