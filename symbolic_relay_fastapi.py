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

def store_vector(session: str, vector_id: str, vector: dict):
    if session not in vector_store:
        vector_store[session] = {}
        ttl_store[session] = {}

    vector_store[session][vector_id] = vector
    ttl_store[session][vector_id] = now() + TTL_SECONDS
    print(f"📡 Stored: {session}/{vector_id}")

def expire_old_vectors():
    current = now()
    for session in list(ttl_store.keys()):
        for vector_id in list(ttl_store[session].keys()):
            if ttl_store[session][vector_id] < current:
                del ttl_store[session][vector_id]
                del vector_store[session][vector_id]
                print(f"🧹 Expired: {session}/{vector_id}")

@app.get("/")
async def root():
    return {"status": "ok", "message": "SYNC369 relay running"}

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

@app.websocket("/ws/{session}")
async def websocket_endpoint(websocket: WebSocket, session: str):
    await websocket.accept()
    print(f"🔗 WebSocket opened: {session}")
    try:
        while True:
            try:
                raw = await websocket.receive_text()
            except Exception:
                try:
                    raw = (await websocket.receive_bytes()).decode("utf-8")
                except:
                    print("⚠️ Failed to decode vector.")
                    continue

            try:
                vector = json.loads(raw)
                vector_id = f"v{vector['msg_index']}_{vector['timestamp']}"
                store_vector(session, vector_id, vector)
            except Exception as e:
                print(f"⚠️ General error while receiving vector:", e)

    except WebSocketDisconnect:
        print(f"❌ WebSocket disconnected: {session}")