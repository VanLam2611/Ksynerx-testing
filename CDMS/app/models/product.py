from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.database import Base
from datetime import datetime

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(15), unique=True, index=True, nullable=False)
    sku = Column(String, unique=True, index=True, nullable=False)
    parentSKU = Column(String, index=True)
    productName = Column(String, unique=True, index=True, nullable=False)
    
    assetType = Column(String, nullable=True)
    
    hasSerial = Column(Boolean, default=False)
    hasExpiration = Column(Boolean, default=False)
    color = Column(String, nullable=True)
    size = Column(String, nullable=True)
    
    description = Column(String, nullable=True)
    units = Column(String, nullable=True)
    categories = Column(String, nullable=True)
    
    isActive = Column(Boolean, default=True)
    
    createdAt = Column(DateTime, default=datetime.now(), nullable=True)
    updatedAt = Column(DateTime, nullable=True)