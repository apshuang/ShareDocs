from typing import Dict, Set
from fastapi import WebSocket
import json


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Dict[int, WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, document_id: int, user_id: int):
        await websocket.accept()
        
        if document_id not in self.active_connections:
            self.active_connections[document_id] = {}
        
        self.active_connections[document_id][user_id] = websocket
    
    def disconnect(self, document_id: int, user_id: int):
        if document_id in self.active_connections:
            if user_id in self.active_connections[document_id]:
                del self.active_connections[document_id][user_id]
            
            if not self.active_connections[document_id]:
                del self.active_connections[document_id]
    
    async def send_personal_message(self, message: dict, document_id: int, user_id: int):
        if document_id in self.active_connections:
            if user_id in self.active_connections[document_id]:
                websocket = self.active_connections[document_id][user_id]
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    print(f"发送消息失败: {e}")
    
    async def broadcast_to_document(self, message: dict, document_id: int, exclude_user_id: int = None):
        if document_id not in self.active_connections:
            return
        
        disconnected_users = []
        
        for user_id, websocket in self.active_connections[document_id].items():
            if exclude_user_id is not None and user_id == exclude_user_id:
                continue
            
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"广播消息失败 (user_id={user_id}): {e}")
                disconnected_users.append(user_id)
        
        for user_id in disconnected_users:
            self.disconnect(document_id, user_id)
    
    def get_subscribed_users(self, document_id: int) -> Set[int]:
        if document_id not in self.active_connections:
            return set()
        return set(self.active_connections[document_id].keys())


manager = ConnectionManager()

