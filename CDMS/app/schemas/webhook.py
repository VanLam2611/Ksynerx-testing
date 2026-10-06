import json
from typing import Any, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class ProductSchema(BaseModel):
    """
    Schema for validating individual product data from webhook.
    """
    productId: Union[int, str] = Field(..., description="ID sản phẩm từ hệ thống đối tác")
    sku: str = Field(..., min_length=1, description="Mã SKU sản phẩm")
    productName: str = Field(..., min_length=1, description="Tên sản phẩm")
    parentSKU: Optional[str] = Field(None, description="Mã SKU từ đối tác")
    assetType: Optional[str] = Field(None, description="Loại tài sản/sản phẩm")
    hasSerial: bool = Field(False, description="Sản phẩm có serial number hay không")
    hasExpiration: bool = Field(False, description="Sản phẩm có hạn sử dụng hay không")
    color: Optional[str] = Field(None, description="Màu sắc")
    size: Optional[str] = Field(None, description="Kích thước")
    description: Optional[str] = Field(None, description="Mô tả sản phẩm")
    units: Optional[Union[List[Any], dict, str]] = Field(None, description="Đơn vị tính (danh sách, object hoặc string)")
    categories: Optional[Union[List[Any], dict, str]] = Field(None, description="Danh mục sản phẩm")
    isActive: bool = Field(True, description="Trạng thái kích hoạt")

    @field_validator("productId", mode="before")
    @classmethod
    def validate_product_id(cls, v):
        if v is None:
            raise ValueError("productId is required and cannot be null")
        s = str(v).strip()
        if not s:
            raise ValueError("productId cannot be empty")
        if len(s) > 15:
            # PostgreSQL external_id is VARCHAR(15)
            s = s[:15]
        return s

    @field_validator("sku", "productName", mode="before")
    @classmethod
    def validate_non_empty_string(cls, v, info):
        if v is None:
            raise ValueError(f"{info.field_name} is required and cannot be null")
        s = str(v).strip()
        if not s:
            raise ValueError(f"{info.field_name} cannot be empty or blank")
        return s

    @field_validator("parentSKU", "assetType", "color", "size", "description", mode="before")
    @classmethod
    def clean_optional_strings(cls, v):
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None


class WebhookResponseData(BaseModel):
    total_received: int = Field(..., description="")
    valid_items: int = Field(..., description="")
    upserted: int = Field(..., description="")
    skipped: int = Field(0, description="")
    errors: List[str] = Field(default_factory=list, description="")


class WebhookResponse(BaseModel):
    code: int = Field(200, description="HTTP code")
    status: str = Field("success", description="")
    message: str = Field(..., description="")
    data: WebhookResponseData
