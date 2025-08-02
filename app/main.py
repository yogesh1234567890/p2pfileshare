from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import datetime
import jwt
import time, hmac, hashlib, base64
from app.config import settings
from app.signaling.routes import router as signaling_router
from app.signaling.manager import manager  


JWT_SECRET = "your-very-secure-secret"
JWT_ALGORITHM = "HS256"


logging.basicConfig(
    level=logging.INFO,  
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

async def lifespan(app: FastAPI):
    await manager.connect_redis()
    yield
    if manager.redis:
        await manager.redis.close()

app = FastAPI(title=settings.app_name, lifespan=lifespan)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket signaling
app.include_router(signaling_router)


@app.get("/")
async def root():
    def create_token(user_id: str) -> str:
        payload = {
            "sub": user_id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token
    
    return {"message": create_token("test_user")}

@app.get("/turn-credentials")
async def generate_turn_credentials(ttl: int = 600):
    secret = 'e9b86b5836eecee9b6d2c62652c81b7e'
    username = str(int(time.time()) + ttl)
    key = hmac.new(secret.encode(), username.encode(), hashlib.sha1)
    password = base64.b64encode(key.digest()).decode()
    return {"username": username, "credential": password}

