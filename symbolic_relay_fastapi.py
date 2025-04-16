from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
from datetime import datetime
import json

app = FastAPI()
vector_store: Dict[str, Dict[str, Dict[str, Any]]] = {}
ttl_tracker: Dict[str, Dict[str, float]] = {}
TTL_SECONDS = 90

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    except Exception as e:
        print(f"❌ JSON decode error: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    vector_store.setdefault(session, {})[vector_id] = data
    ttl_tracker.setdefault(session, {})[vector_id] = now() + TTL_SECONDS
    print(f"📥 Stored vector {session}/{vector_id}")
    return {"status": "ok"}

@app.get("/sessions/{session}")
async def get_vectors(session: str):
    expire_old_vectors()
    result = vector_store.get(session, {})
    print(f"📤 GET {session} → {len(result)} vectors")
    return result

@app.delete("/sessions/{session}/{vector_id}")
async def delete_vector(session: str, vector_id: str):
    if session in vector_store and vector_id in vector_store[session]:
        del vector_store[session][vector_id]
        ttl_tracker[session].pop(vector_id, None)
        print(f"❌ Deleted vector {session}/{vector_id}")
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Vector not found")

@app.websocket("/ws/{session}")
async def websocket_endpoint(websocket: WebSocket, session: str):
    await websocket.accept()
    print(f"📡 WebSocket accepted: {session}")
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                items = json.loads(raw)
                if isinstance(items, dict):
                    items = [items]
                for data in items:
                    vector_id = f"v{data['msg_index']}_{data['timestamp']}"
                    vector_store.setdefault(session, {})[vector_id] = data
                    ttl_tracker.setdefault(session, {})[vector_id] = now() + TTL_SECONDS
                    print(f"📡 WebSocket received vector in {session}/{vector_id}")
            except Exception as e:
                print(f"⚠️ Parse/store error: {e}")
    except WebSocketDisconnect:
        print(f"❌ WebSocket disconnected: {session}")