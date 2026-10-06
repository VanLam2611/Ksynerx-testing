import os
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    PREFIX = os.getenv('PREFIX', 'v1')
    PORT = os.getenv('PORT', '3000')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', "")
    
    VIETFUL_API_URL = os.getenv('VIETFUL_API_URL')
    VIETFUL_API_AUTH_TOKEN = os.getenv('VIETFUL_API_AUTH_TOKEN')
    
    # Redis & Rate Limit
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    WEBHOOK_RATE_LIMIT_TIMES = int(os.getenv('WEBHOOK_RATE_LIMIT_TIMES', '2'))
    WEBHOOK_RATE_LIMIT_SECONDS = int(os.getenv('WEBHOOK_RATE_LIMIT_SECONDS', '60'))
    
    # Webhook Authentication
    WEBHOOK_AUTH_TOKEN = os.getenv('WEBHOOK_AUTH_TOKEN', "")
    
config = Config()