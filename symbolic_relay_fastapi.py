from fastapi import FastAPI, WebSocket, Request, HTTPException
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
ttl_tracker: Dict[str, Dict[str, float]] = {}
TTL_SECONDS = 90

def now():
    return datetime.utcnow().timestamp()

def store_vector(session, vector_id, data):
    if session not in vector_store:
        vector_store[session] = {}
        ttl_tracker[session] = {}
    vector_store[session][vector_id] = data
    ttl_tracker[session][vector_id] = now() + TTL_SECONDS

def expire_old_vectors():
    for session in list(vector_store):
        for vector_id in list(vector_store[session]):
            expiry = ttl_tracker.get(session, {}).get(vector_id)
            if expiry and expiry < now():
                del vector_store[session][vector_id]
                ttl_tracker[session].pop(vector_id, None)
                print(f"🧹 Expired vector {session}/{vector_id}")

@app.post("/sessions/{session}/{vector_id}")
async def post_vector(session: str, vector_id: str, request: Request):
    try:
        data = await request.json()
    except Exception as e:
        print(f"❌ JSON decode error in {session}/{vector_id}: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    store_vector(session, vector_id, data)
    print(f"📥 Stored vector {session}/{vector_id} → {data}")
    return {"status": "ok"}

@app.get("/sessions/{session}")
async def get_vectors(session: str):
    expire_old_vectors()
    result = vector_store.get(session, {})
    print(f"📤 GET session {session} → {len(result)} vectors")
    return result

@app.delete("/sessions/{session}/{vector_id}")
async def delete_vector(session: str, vector_id: str):
    if session in vector_store and vector_id in vector_store[session]:
        del vector_store[session][vector_id]
        ttl_tracker[session].pop(vector_id, None)
        print(f"❌ Deleted vector {session}/{vector_id}")
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Vector not found")

@app.websocket("/ws/{session_path}")
async def websocket_endpoint(websocket: WebSocket, session_path: str):
    await websocket.accept()
    print(f"📡 WebSocket /ws/{session_path} accepted")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except:
                print(f"❌ Invalid JSON in WebSocket message")
                continue

            if isinstance(data, list):
                for vec in data:
                    vector_id = f"v{vec['msg_index']}_{vec['timestamp']}"
                    store_vector(session_path, vector_id, vec)
                    print(f"📡 WebSocket received vector in {session_path}/{vector_id}")
            else:
                vector_id = f"v{data['msg_index']}_{data['timestamp']}"
                store_vector(session_path, vector_id, data)
                print(f"📡 WebSocket received vector in {session_path}/{vector_id}")
    except Exception as e:
        print(f"⚠️ WebSocket closed: {e}")
    finally:
        print("❌ WebSocket connection closed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)