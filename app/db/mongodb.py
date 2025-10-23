import motor.motor_asyncio
from app.core.config import settings

client = None
db = None

async def connect_to_mongo():
    global client, db
    client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGO_URL)
    db = client[settings.MONGO_DB_NAME]
    print("Conectado a MongoDB...")

async def close_mongo_connection():
    global client
    if client:
        client.close()
        print("Desconectado de MongoDB.")

def get_mongo_db() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    return db

def get_mongo_collection() -> motor.motor_asyncio.AsyncIOMotorCollection:
    return db[settings.MONGO_COLLECTION_NAME]