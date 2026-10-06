from fastapi import FastAPI, Depends, Request, status
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from product_model import Product, ProductQuery
from typing import List, Optional, Annotated
from fastapi.responses import JSONResponse
from config import config

tz = timezone(timedelta(hours=7)) # Vietnam time

VIETFUL_PRODUCT_DB = {}
PRODUCT_GENERATION_NUMBER = 1000

# Generate fake products
def generate_products(n: int = 50):
    return [Product().model_dump() for _ in range(n)]

@asynccontextmanager
async def lifespan(app: FastAPI):
    products = generate_products(PRODUCT_GENERATION_NUMBER)
    VIETFUL_PRODUCT_DB.update({product["productId"]: Product(**product) for product in products})
    yield

    print("App shutting down")

app = FastAPI(
    title="Vietful Mock API",
    description="A mock API for Vietful",
    version="1.0.0",
    lifespan=lifespan
)

@app.middleware("http")
async def check_auth_header(request: Request, call_next):
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Missing or invalid Authorization header"},
        )
        
    token = auth_header.split(" ")[1]

    # Kiểm tra tính hợp lệ của token
    if token != config.API_KEY:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid or expired token"},
        )

    # Nếu hợp lệ, tiếp tục xử lý request
    response = await call_next(request)
    return response

@app.get("/api/v1/Products", response_model=dict | list)
def get_products(
    query: Annotated[ProductQuery, Depends()]
):
    filtered_products = []
    
    try:
        for p in VIETFUL_PRODUCT_DB.values():
            if query.Keyword and not (query.Keyword in p.productName.lower() or query.Keyword in p.sku.lower()):
                continue

            if query.parentSKUs and p.parentSKU.lower() not in query.parentSKUs:
                continue

            if query.SKUs and p.sku.lower() not in query.SKUs:
                continue

            filtered_products.append(p)
            
        # Pagination
        page = max(1, query.PageIndex)
        per_page = max(1, query.PageSize)
        
        start = (page - 1) * per_page
        end = start + per_page
            
        return filtered_products[start:end]
        
    except Exception as e:
        return {
            "code": "",
            "errorMessage": "Failed"
        }