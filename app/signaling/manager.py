import redis.asyncio as redis
from fastapi import WebSocket
from starlette.websockets import WebSocketState
from app.config import settings
import uuid
import logging
import weakref

logger = logging.getLogger("signaling")

class RedisConnectionManager:
    def __init__(self):
        self.redis_url = settings.redis_url
        self.redis = None
        self.local_connections = weakref.WeakValueDictionary()  # {conn_id: websocket}
        self.connection_rooms = {}  # {conn_id: room_id}

    async def connect_redis(self):
        try:
            self.redis = redis.from_url(self.redis_url)
            await self.redis.ping()
            logger.info("✅ Connected to Redis")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise

    async def connect(self, websocket: WebSocket, room_id: str) -> str:
        if self.redis is None:
            raise RuntimeError("Redis not connected")

        await websocket.accept()
        conn_id = str(uuid.uuid4())

        self.local_connections[conn_id] = websocket
        self.connection_rooms[conn_id] = room_id

        try:
            await self.redis.sadd(f"room:{room_id}", conn_id)
            logger.info(f"[{room_id}] User {conn_id} joined")
        except Exception as e:
            logger.error(f"Redis error adding connection {conn_id} to room {room_id}: {e}")

        return conn_id


    async def disconnect(self, conn_id: str):
        websocket = self.local_connections.get(conn_id)
        room_id = self.connection_rooms.get(conn_id)

        # Gracefully close the WebSocket if it's still connected
        if websocket and websocket.application_state == WebSocketState.CONNECTED:
            try:
                await websocket.close()
                logger.info(f"[{room_id}] Gracefully closed WebSocket for {conn_id}")
            except Exception as e:
                logger.warning(f"[{room_id}] Failed to close WebSocket for {conn_id}: {e}")

        # Remove from Redis room set
        if room_id:
            try:
                await self.redis.srem(f"room:{room_id}", conn_id)
                logger.info(f"[{room_id}] User {conn_id} left")
            except Exception as e:
                logger.error(f"Redis error removing {conn_id} from room {room_id}: {e}")

        # Cleanup local references
        self.local_connections.pop(conn_id, None)
        self.connection_rooms.pop(conn_id, None)

    async def broadcast(self, room_id: str, message: str, sender_id: str = None):
        if self.redis is None:
            raise RuntimeError("Redis not connected")

        try:
            conn_ids = await self.redis.smembers(f"room:{room_id}")
        except Exception as e:
            logger.error(f"Redis error reading room {room_id}: {e}")
            return

        for conn_id_bytes in conn_ids:
            conn_id = conn_id_bytes.decode() if isinstance(conn_id_bytes, bytes) else str(conn_id_bytes)
            if conn_id == sender_id:
                continue

            websocket = self.local_connections.get(conn_id)
            if websocket:
                try:
                    await websocket.send_text(message)
                except Exception as e:
                    logger.warning(f"[{room_id}] Failed to send message to {conn_id}: {e}")

        logger.info(f"[{room_id}] Broadcasted: {message}")

    async def leave_room(self, conn_id: str):
        await self.disconnect(conn_id)
# Create and export a single instance
manager = RedisConnectionManager()
