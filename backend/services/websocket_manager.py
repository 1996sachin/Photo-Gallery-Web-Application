from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json

class ConnectionManager:
    def __init__(self):
        # Map user_id (str) to a set of active WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            msg_text = json.dumps(message)
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(msg_text)
                except:
                    pass

    async def broadcast(self, message: dict):
        msg_text = json.dumps(message)
        for user_conns in self.active_connections.values():
            for connection in user_conns:
                try:
                    await connection.send_text(msg_text)
                except:
                    pass

manager = ConnectionManager()
