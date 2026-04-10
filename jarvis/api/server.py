import asyncio
import logging
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI(title="Rocky Omega API")

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared state (will be updated by the main voice loop)
class GlobalState:
    def __init__(self):
        self.status = "IDLE"
        self.stats = {}
        self.transcript = []
        self.memory = []
        self.active_context = "Unknown"
        self.current_user_text = ""
        self.current_ai_text = ""
        self.connections: List[WebSocket] = []

state = GlobalState()

@app.get("/health")
async def health():
    return {"status": "online", "version": "1.0.0"}

@app.get("/state")
async def get_state():
    return {
        "status": state.status,
        "stats": state.stats,
        "active_context": state.active_context,
        "current_user_text": state.current_user_text,
        "current_ai_text": state.current_ai_text,
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    state.connections.append(websocket)
    try:
        # Send initial state
        await websocket.send_json({
            "type": "init",
            "data": {
                "status": state.status,
                "stats": state.stats,
                "history": state.transcript[-10:] if state.transcript else []
            }
        })
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        state.connections.remove(websocket)

_loop = None

@app.on_event("startup")
async def startup_event():
    global _loop
    _loop = asyncio.get_running_loop()

async def broadcast(message: Dict[str, Any]):
    """Send a message to all connected dashboard clients."""
    if not state.connections or not _loop:
        return
    
    for connection in state.connections:
        try:
            await connection.send_json(message)
        except Exception:
            pass

def run_server(port: int = 8000):
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

# Integration helpers for main.py (Thread-Safe)
def update_status(new_status: str):
    state.status = new_status
    if _loop:
        _loop.call_soon_threadsafe(
            lambda: asyncio.create_task(broadcast({"type": "status", "data": new_status}))
        )

def update_stats(new_stats: Dict[str, Any]):
    state.stats = new_stats
    if _loop:
        _loop.call_soon_threadsafe(
            lambda: asyncio.create_task(broadcast({"type": "stats", "data": new_stats}))
        )

def update_transcript(user: str, ai: str):
    entry = {"user": user, "ai": ai}
    state.transcript.append(entry)
    state.current_user_text = user
    state.current_ai_text = ai
    if _loop:
        _loop.call_soon_threadsafe(
            lambda: asyncio.create_task(broadcast({"type": "transcript", "data": entry}))
        )

def update_notification(msg: str):
    if _loop:
        _loop.call_soon_threadsafe(
            lambda: asyncio.create_task(broadcast({"type": "notification", "data": msg}))
        )

def update_emotion(emotion: str):
    """
    emotion can be: 'neutral', 'productive', 'stressed', 'alert'
    """
    if _loop:
        _loop.call_soon_threadsafe(
            lambda: asyncio.create_task(broadcast({"type": "emotion", "data": emotion}))
        )
