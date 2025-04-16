# symbolic_relay_fastapi.py — Pure Symbolic Vector Relay

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
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
ttl_store: Dict[str, Dict[str, float]] = {}
TTL_SECONDS = 90

def now():
    return datetime.utcnow().timestamp()

def store_vector(session_path: str, vector_id: str, vector: dict):
    if session_path not in vector_store:
        vector_store[session_path] = {}
        ttl_store[session_path] = {}

    vector_store[session_path][vector_id] = vector
    ttl_store[session_path][vector_id] = now() + TTL_SECONDS
    print(f"📡 Vector stored in {session_path}/{vector_id}")

def expire_old_vectors():
    current = now()
    for session in list(ttl_store.keys()):
        for vector_id in list(ttl_store[session].keys()):
            if ttl_store[session][vector_id] < current:
                del ttl_store[session][vector_id]
                del vector_store[session][vector_id]
                print(f"🧹 Expired {session}/{vector_id}")

@app.get("/")
async def root():
    return {"status": "SYNC369 relay active."}

@app.get("/sessions/{session}")
async def get_vectors(session: str):
    expire_old_vectors()
    return vector_store.get(session, {})

@app.delete("/sessions/{session}/{vector_id}")
async def delete_vector(session: str, vector_id: str):
    if session in vector_store and vector_id in vector_store[session]:
        del vector_store[session][vector_id]
        ttl_store[session].pop(vector_id, None)
        return {"status": "deleted"}
    return {"status": "not_found"}

@app.websocket("/ws/{session_path}")
async def websocket_endpoint(websocket: WebSocket, session_path: str):
    await websocket.accept()
    print(f"🔗 WebSocket opened: {session_path}")
    try:
        while True:
            try:
                raw = await websocket.receive_text()
                payload = json.loads(raw)

                if isinstance(payload, dict):
                    vector_id = f"v{payload.get('msg_index', 0)}_{payload.get('timestamp', '0')}"
                    store_vector(session_path, vector_id, payload)
                else:
                    print(f"⚠️ Unknown data type: {type(payload)}")

            except json.JSONDecodeError as e:
                print(f"⚠️ JSON error: {e}")
            except Exception as e:
                print(f"⚠️ General error while receiving vector: {e}")

    except WebSocketDisconnect:
        print(f"❌ Disconnected: {session_path}")