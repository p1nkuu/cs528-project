import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
import uvicorn

app = FastAPI()

# Mount the static directory
static_dir = os.path.join(os.path.dirname(__file__), "../static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

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

from pydantic import BaseModel

class ActionRequest(BaseModel):
    action: str

@app.post("/predict")
async def post_predict(req: ActionRequest):
    """
    Endpoint for the inference script to push predictions via HTTP.
    """
    await manager.broadcast(req.action)
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)