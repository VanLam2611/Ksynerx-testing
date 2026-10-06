import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Enviroment
    API_KEY = os.getenv('API_KEY')
    
    # Product model config
    ASSET_TYPES = ["Single", "Bundle", "MultipleBarcodes"]
    SIZES = ["S", "M", "L", "XL", "XXL"]
    COLORS = ["Red", "Blue", "Green", "Yellow", "Purple", "Orange", "Pink", "Brown", "Black", "White"]
    UNITS = ["pcs", "kg", "g", "l", "ml", "m", "cm", "mm", "in", "ft", "yd", "mi"]
    CATEGORIES = [
        {
            "categoryCode": "ELT",
            "categoryName": "Electronics"
        },
        {
            "categoryCode": "CLT",
            "categoryName": "Clothing"
        },
        {
            "categoryCode": "HME",
            "categoryName": "Home"
        },
        {
            "categoryCode": "GND",
            "categoryName": "Garden"
        },
        {
            "categoryCode": "SPT",
            "categoryName": "Sports"
        },
    ]
    OUTBOUNDTYPE = ["NotDefined", "FIFO", "LIFO", "FEFO", "LEFO"]

config = Config()