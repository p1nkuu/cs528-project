import json
import os
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the static directory
static_dir = os.path.join(os.path.dirname(__file__), "../static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

data_dir = os.path.join(os.path.dirname(__file__), "../data")
os.makedirs(data_dir, exist_ok=True)
password_file = os.path.join(data_dir, "saved_passwords.json")

if not os.path.exists(password_file):
    with open(password_file, "w", encoding="utf-8") as file_handle:
        json.dump([], file_handle, indent=2)

# Store connected frontend clients
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()


class PasswordSaveRequest(BaseModel):
    name: str
    sequence: list[str]


class PasswordVerifyRequest(BaseModel):
    sequence: list[str]

@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")

@app.websocket("/ws/subscriber")
async def websocket_subscriber(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Just keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

class ActionRequest(BaseModel):
    action: str

@app.post("/predict")
async def post_predict(req: ActionRequest):
    """
    Endpoint for the inference script to push predictions via HTTP.
    """
    await manager.broadcast(req.action)
    return {"status": "ok"}


@app.post("/passwords/save")
async def save_password(req: PasswordSaveRequest):
    normalized_name = req.name.strip()
    normalized_sequence = [item.strip().lower() for item in req.sequence if item.strip()]

    if not normalized_name:
        return {"status": "error", "message": "Password name is required."}

    if len(normalized_sequence) != 6:
        return {"status": "error", "message": "Password sequence must contain exactly 6 moves."}

    with open(password_file, "r", encoding="utf-8") as file_handle:
        saved_passwords = json.load(file_handle)

    entry = {
        "name": normalized_name,
        "sequence": normalized_sequence,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    saved_passwords.append(entry)

    with open(password_file, "w", encoding="utf-8") as file_handle:
        json.dump(saved_passwords, file_handle, indent=2)

    return {"status": "ok", "saved": entry}


@app.get("/passwords")
async def list_passwords():
    with open(password_file, "r", encoding="utf-8") as file_handle:
        saved_passwords = json.load(file_handle)
    return {"status": "ok", "passwords": saved_passwords}


@app.post("/passwords/verify")
async def verify_password(req: PasswordVerifyRequest):
    normalized_sequence = [item.strip().lower() for item in req.sequence if item.strip()]

    if len(normalized_sequence) != 6:
        return {"status": "error", "message": "Password sequence must contain exactly 6 moves."}

    with open(password_file, "r", encoding="utf-8") as file_handle:
        saved_passwords = json.load(file_handle)

    for saved_password in saved_passwords:
        if [step.strip().lower() for step in saved_password.get("sequence", [])] == normalized_sequence:
            return {
                "status": "ok",
                "matched": True,
                "user_name": saved_password.get("name", "User"),
            }

    return {"status": "ok", "matched": False}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)