# app/db/mongodb.py
import motor.motor_asyncio
from app.core.config import settings

client: motor.motor_asyncio.AsyncIOMotorClient = None
db_energy: motor.motor_asyncio.AsyncIOMotorDatabase = None
db_fuel: motor.motor_asyncio.AsyncIOMotorDatabase = None

async def connect_to_mongo():
    global client, db_energy, db_fuel
    print("Iniciando conexión a MongoDB...")
    client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGO_URL)
    
    db_energy = client[settings.MONGO_DB_NAME]
    
    db_fuel = client[settings.MONGO_FUEL_DB_NAME] 
    
    print(f"Conectado a MongoDB. DB Energia: '{settings.MONGO_DB_NAME}', DB Combustible: '{settings.MONGO_FUEL_DB_NAME}'")

async def close_mongo_connection():
    global client
    if client:
        client.close()
        print("Desconectado de MongoDB.")


def get_mongo_collection() -> motor.motor_asyncio.AsyncIOMotorCollection:
    """ 
    Dependencia de FastAPI:
    Devuelve la colección de ENERGÍA desde la DB de energía 
    """
    print(f"Accediendo a DB: {settings.MONGO_DB_NAME}, Colección: {settings.MONGO_COLLECTION_NAME}")
    return db_energy[settings.MONGO_COLLECTION_NAME]

def get_mongo_fuel_collection() -> motor.motor_asyncio.AsyncIOMotorCollection:
    """ 
    Dependencia de FastAPI:
    Devuelve la colección de COMBUSTIBLE desde la DB de combustible 
    """
    print(f"Accediendo a DB: {settings.MONGO_FUEL_DB_NAME}, Colección: {settings.MONGO_COLLECTION_NAME2}")
    # ¡Usa el manejador db_fuel!
    return db_fuel[settings.MONGO_COLLECTION_NAME2]