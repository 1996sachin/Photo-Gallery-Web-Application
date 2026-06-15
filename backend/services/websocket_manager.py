from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Map user_id (str) to a set of active WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        try:
            await websocket.accept()
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
            logger.info(f"WebSocket connected for user {user_id}")
        except Exception as e:
            logger.error(f"Error accepting WebSocket for user {user_id}: {e}")
            raise

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            msg_text = json.dumps(message)
            for connection in list(self.active_connections[user_id]):
                try:
                    await connection.send_text(msg_text)
                except Exception as e:
                    logger.warning(f"Error sending message to user {user_id}: {e}")
                    self.disconnect(user_id, connection)

    async def broadcast(self, message: dict):
        msg_text = json.dumps(message)
        for user_id, user_conns in list(self.active_connections.items()):
            for connection in list(user_conns):
                try:
                    await connection.send_text(msg_text)
                except Exception as e:
                    logger.warning(f"Error broadcasting message to user {user_id}: {e}")
                    self.disconnect(user_id, connection)

manager = ConnectionManager()
