from pydantic import BaseModel, Field, model_validator, field_validator
from faker import Faker
from config import config

fake = Faker() # Initialize Faker

class Product(BaseModel):
    productId: int = Field(default_factory=fake.random_int, min_value=10000, max_value=99999)
    sku: str = Field(default_factory=lambda: f"SKU{fake.random_int(min=100000, max=999999)}")
    parentSKU: str = Field(default_factory=lambda: f"PR_SKU{fake.random_int(min=100000, max=999999)}")
    productName: str = Field(default_factory=fake.name)
    
    assetType: str = Field(default_factory=lambda: fake.random_element(elements=config.ASSET_TYPES))
    
    hasSerial: bool = Field(default_factory=lambda: fake.boolean())
    hasExpiration: bool = Field(default_factory=lambda: fake.boolean())
    color: str = Field(default_factory=lambda: fake.random_element(elements=config.COLORS))
    size: str = Field(default_factory=lambda: fake.random_element(elements=config.SIZES))
    
    description: str = Field(default_factory=fake.sentence)
    units: list[str] | None = Field(default_factory=lambda: [fake.random_element(elements=config.UNITS) for _ in range(fake.random_int(min=1, max=2))] if fake.boolean() else None)
    categories: list[dict] | None = Field(default_factory=lambda: [fake.random_element(elements=config.CATEGORIES) for _ in range(fake.random_int(min=1, max=3))] if fake.boolean() else None)
    
    isActive: bool = Field(default_factory=lambda: fake.boolean())
    
# Validate
class ProductQuery(BaseModel):
    Keyword: str | None = None
    parentSKUs: str | None = None
    SKUs: str | None = None
    PageIndex: int = 1
    PageSize: int = 10

    @field_validator(
        "SKUs",
        "parentSKUs",
        mode="after"
    )
    @classmethod
    def parse_comma_separated(cls, value):
        if value is None:
            return None

        if isinstance(value, str):
            return [
                item.strip().lower()
                for item in value.split(",")
                if item.strip()
            ]

        return value
    
    @field_validator(
        "Keyword",
        mode="after"
    )
    @classmethod
    def parse_separated(cls, value):
        if value is None:
            return None

        return value.strip().lower()
