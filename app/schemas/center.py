from pydantic import BaseModel
from typing import List, Optional
from .device import Device

class CenterBase(BaseModel):
    name: str
    company_id: int
    price_kwh: Optional[float] = 250.0

class CenterCreate(CenterBase):
    pass
class CenterUpdate(BaseModel):
    name: Optional[str] = None
    price_kwh: Optional[float] = None

class Center(CenterBase):
    id: int
    
    class Config:
        from_attributes = True

class CenterWithDevices(Center):
    devices: List[Device] = []
#nmas esplicito
class CenterPriceUpdate(BaseModel):
    price_kwh: float    