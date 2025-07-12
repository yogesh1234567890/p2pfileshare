from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "P2P Signaling Server"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    redis_url: str = "redis://localhost:6379/0" 

    class Config:
        env_file = ".env"

settings = Settings()
