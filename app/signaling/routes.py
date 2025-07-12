from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from fastapi.exceptions import HTTPException
import jwt
from jwt import PyJWTError
import datetime
from app.signaling.manager import manager


JWT_SECRET = "your-very-secure-secret"
JWT_ALGORITHM = "HS256"
router = APIRouter()

async def verify_token(token: str) -> bool:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return False
        return True
    except PyJWTError:
        return False


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    # if not await verify_token(token):
    #     await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    #     return
    conn_id = await manager.connect(websocket, room_id)
    try:
        while True:
            message = await websocket.receive_text()
            await manager.broadcast(room_id, message, sender_id=conn_id)
    except WebSocketDisconnect:
        await manager.disconnect(conn_id)
