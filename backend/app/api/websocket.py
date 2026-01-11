from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.document import Document
from app.models.user import User
from app.models.document_share import PermissionType
from app.utils.jwt import verify_token
from app.utils.permission import has_document_access
from app.websocket.manager import manager
import json

router = APIRouter()


async def get_user_from_token(token: str, db: Session) -> User:
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌"
        )
    
    user_id: int = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )
    
    return user


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    document_id: int = Query(...)
):
    db = next(get_db())
    try:
        user = await get_user_from_token(token, db)
        
        if not has_document_access(db, document_id, user.id, PermissionType.READ):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        document = db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        await manager.connect(websocket, document_id, user.id)
        
        await websocket.send_json({
            "type": "connected",
            "data": {
                "user_id": user.id,
                "document_id": document_id,
                "current_version": document.current_version
            }
        })
        
        try:
            while True:
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    message_type = message.get("type")
                    
                    if message_type == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif message_type == "subscribe":
                        document = db.query(Document).filter(Document.id == document_id).first()
                        await websocket.send_json({
                            "type": "subscribed",
                            "data": {
                                "document_id": document_id,
                                "current_version": document.current_version if document else 0
                            }
                        })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "data": {
                                "message": f"未知的消息类型: {message_type}"
                            }
                        })
                
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "data": {
                            "message": "无效的 JSON 格式"
                        }
                    })
        
        except WebSocketDisconnect:
            manager.disconnect(document_id, user.id)
        finally:
            db.close()
    
    except Exception as e:
        print(f"WebSocket 错误: {e}")
        try:
            await websocket.close()
        except:
            pass
        finally:
            db.close()

