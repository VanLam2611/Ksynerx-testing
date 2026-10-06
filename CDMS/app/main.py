from fastapi import FastAPI, Depends
from fastapi.routing import APIRoute

from sqlalchemy.orm import Session
from app.database import Base
from app.database import engine, get_db
from app.models import Product

from app.api.main import api_router
from app.config import config
from app.utils.logger import setup_logger

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Change data management service",
    description="",
    version="1.0.0"
)

app.include_router(api_router, prefix=config.PREFIX)

@app.get('/')
def index():
    """Health check endpoint"""
    return {
        'status': 'running',
        'service': 'Change data management service',
        'version': '1.0.0'
    }

# Setup logger
logger = setup_logger('app', 'logs/app.log', 'INFO')