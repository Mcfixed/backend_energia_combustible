from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.mongodb import connect_to_mongo, close_mongo_connection
from app.api.endpoints import auth, users, devices
from fastapi.middleware.cors import CORSMiddleware
# Evento de ciclo de vida para conectar y desconectar MongoDB al iniciar/apagar
@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(
    title="API de Medidores de Energía",
    description="Una API para gestionar dispositivos y leer datos de MongoDB.",
    lifespan=lifespan
)
origins = [
    "http://localhost:5173", # Puerto por defecto de Vite
    "http://localhost:3000", # Puerto por defecto de Create React App
    "http://localhost",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # Lista de orígenes permitidos
    allow_credentials=True,    # Permite cookies/tokens de autorización
    allow_methods=["*"],       # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],       # Permite todos los headers
)

# Incluir los routers
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(users.router, prefix="/api", tags=["Users & Companies"])
app.include_router(devices.router, prefix="/api", tags=["Devices"])

@app.get("/api/health")
def health_check():
    return {"status": "ok"}