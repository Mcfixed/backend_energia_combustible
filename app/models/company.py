from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.database import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)

    # Relación M2M con User a través de UserCompany
    users_association = relationship("UserCompany", back_populates="company")
    
    # Relación 1-M con Device
    devices = relationship("Device", back_populates="company")