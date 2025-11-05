# app/schemas/fuel.py
from pydantic import BaseModel, Field
from typing import List, Optional
import datetime
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
    pressure_Bar_S2: float | None = 0
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
    deviceInfo: dict
    object: MongoFuelObject
    rxInfo: List[MongoRxInfo] = []

    class Config:
        extra = 'ignore'


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
    id: str 
    name: str
    capacity: int
    fuelType: str
    sensor: FuelSensorData
    centerId: str 

class FuelCenter(BaseModel):
    """ Coincide con la 'interface Center' de React """
    id: str
    name: str
    location: str
    status: str
    tanks: List[FuelTank]
    totalCapacity: int
    currentInventory: float

    class Config:
        from_attributes = True