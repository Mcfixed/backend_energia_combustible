from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    MONGO_URL: str
    #energia
    MONGO_DB_NAME: str
    MONGO_COLLECTION_NAME: str
    
    #combustible
    MONGO_FUEL_DB_NAME: str        
    MONGO_COLLECTION_NAME2: str
    
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 43200
    class Config:
        env_file = ".env"

settings = Settings()