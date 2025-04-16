# symbolic_relay_fastapi.py — SYNC369 Symbolic Relay with WebSocket Broadcast

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List
from datetime import datetime
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

vector_store: Dict[str, Dict[str, Dict[str, Any]]] = {}
ttl_tracker: Dict[str, Dict[str, float]] = {}
websocket_sessions: Dict[str, List[WebSocket]] = {}
TTL_SECONDS = 90

def now():
    return datetime.utcnow().timestamp()

def expire_old_vectors():
    for session in list(vector_store):
        for vector_id in list(vector_store[session]):
            expiry = ttl_tracker.get(session, {}).get(vector_id)
            if expiry and expiry < now():
                del vector_store[session][vector_id]
                ttl_tracker[session].pop(vector_id, None)

@app.post("/sessions/{session}/{vector_id}")
async def post_vector(session: str, vector_id: str, request: Request):
    try:
        data = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    vector_store.setdefault(session, {})[vector_id] = data
    ttl_tracker.setdefault(session, {})[vector_id] = now() + TTL_SECONDS
    return {"status": "ok"}

@app.get("/sessions/{session}")
async def get_vectors(session: str):
    expire_old_vectors()
    return vector_store.get(session, {})

@app.delete("/sessions/{session}/{vector_id}")
async def delete_vector(session: str, vector_id: str):
    if session in vector_store and vector_id in vector_store[session]:
        del vector_store[session][vector_id]
        ttl_tracker[session].pop(vector_id, None)
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Vector not found")

@app.websocket("/ws/{session}")
async def websocket_endpoint(websocket: WebSocket, session: str):
    await websocket.accept()
    websocket_sessions.setdefault(session, []).append(websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            data = json.loads(msg)
            vector_id = f"v{data['msg_index']}_{data['timestamp']}"
            vector_store.setdefault(session, {})[vector_id] = data
            ttl_tracker.setdefault(session, {})[vector_id] = now() + TTL_SECONDS

            for ws in websocket_sessions.get(session, []):
                if ws != websocket:
                    try:
                        await ws.send_text(json.dumps(data))
                    except:
                        continue
    except WebSocketDisconnect:
        pass
    finally:
        websocket_sessions[session].remove(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)