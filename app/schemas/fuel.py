# app/schemas/fuel.py
from pydantic import BaseModel, Field
from typing import List, Optional
import datetime
# --- Schemas de MongoDB ---
# (Basados en tu JSON de ejemplo)

class MongoFuelObject(BaseModel):
    """ 
    Parsea el campo 'object' del JSON de Mongo.
    Ahora acepta 'float' o 'None', con '0' como default si es None.
    """
    volume_L_S0: float | None = 0
    percentage_S0: float | None = 0
    pressure_Bar_S0: float | None = 0
    sensor_0_ok: bool = False
    
    volume_L_S1: float | None = 0
    percentage_S1: float | None = 0
    pressure_Bar_S1: float | None = 0
    sensor_1_ok: bool = False
    
    volume_L_S2: float | None = 0
    percentage_S2: float | None = 0
    pressure_Bar_S2: float | None = 0 # <-- Este era el campo del error
    sensor_2_ok: bool = False

    class Config:
        extra = 'ignore'

class MongoLocation(BaseModel):
    latitude: float = 0.0
    longitude: float = 0.0
    class Config:
        extra = 'ignore'

class MongoRxInfo(BaseModel):
    location: Optional[MongoLocation] = None
    
    class Config:
        extra = 'ignore'

class MongoFuelDoc(BaseModel):
    """ Parsea el documento completo de Mongo """
    time: datetime.datetime
    deviceInfo: dict # No necesitamos parsear esto a fondo
    object: MongoFuelObject
    rxInfo: List[MongoRxInfo] = []

    class Config:
        extra = 'ignore'


# --- Schemas de Respuesta de la API ---
# (Basados en tus 'interfaces' de React)

class FuelSensorData(BaseModel):
    """ Coincide con la 'interface SensorData' de React """
    volume_L: float
    percentage: float
    pressure_Bar: float
    sensor_ok: bool
    lastUpdate: str
    latitude: float
    longitude: float

class FuelTank(BaseModel):
    """ Coincide con la 'interface Tank' de React """
    id: str # p.ej. "devEui-S0"
    name: str
    capacity: int
    fuelType: str
    sensor: FuelSensorData
    centerId: str # El ID del centro de Postgres

class FuelCenter(BaseModel):
    """ Coincide con la 'interface Center' de React """
    id: str # El ID del centro de Postgres
    name: str
    location: str
    status: str # 'secure', 'warning', 'danger', etc.
    tanks: List[FuelTank]
    totalCapacity: int
    currentInventory: float

    class Config:
        from_attributes = True