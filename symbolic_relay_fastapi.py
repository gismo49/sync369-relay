# symbolic_relay_fastapi.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
from datetime import datetime
import asyncio
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

vector_store: Dict[str, Dict[str, Any]] = {}
ws_connections: Dict[str, list[WebSocket]] = {}
TTL = 90

@app.get("/")
async def root():
    return {"status": "symbolic-relay-online"}

@app.get("/sessions/{session}")
async def get_vectors(session: str):
    now = datetime.utcnow().timestamp()
    if session in vector_store:
        expired = [k for k, v in vector_store[session].items() if v['expires'] < now]
        for k in expired:
            del vector_store[session][k]
    return {k: v['data'] for k, v in vector_store.get(session, {}).items()}

@app.post("/sessions/{session}/{vector_id}")
async def post_vector(session: str, vector_id: str, request: Request):
    try:
        data = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    now = datetime.utcnow().timestamp()
    if session not in vector_store:
        vector_store[session] = {}
    vector_store[session][vector_id] = {"data": data, "expires": now + TTL}

    for ws in ws_connections.get(session, []):
        try:
            await ws.send_json(data)
        except:
            pass

    return {"status": "ok"}

@app.delete("/sessions/{session}/{vector_id}")
async def delete_vector(session: str, vector_id: str):
    if session in vector_store and vector_id in vector_store[session]:
        del vector_store[session][vector_id]
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Vector not found")

@app.websocket("/ws/{session}")
async def websocket_endpoint(ws: WebSocket, session: str):
    await ws.accept()
    if session not in ws_connections:
        ws_connections[session] = []
    ws_connections[session].append(ws)
    print(f"🌐 WebSocket connected → {session}")
    try:
        while True:
            data = await ws.receive_json()
            now = datetime.utcnow().timestamp()
            msg_id = f"{data['msg_id']}_{data['msg_index']}"
            if session not in vector_store:
                vector_store[session] = {}
            vector_store[session][msg_id] = {"data": data, "expires": now + TTL}
    except WebSocketDisconnect:
        print(f"❌ WebSocket disconnected → {session}")
    finally:
        ws_connections[session].remove(ws)

if __name__ == "__main__":
    print("🚀 SYMBOLIC RELAY NODE READY")
    uvicorn.run("symbolic_relay_fastapi:app", host="0.0.0.0", port=10000)
