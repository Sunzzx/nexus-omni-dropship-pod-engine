"""
Typed domain models for Nexus Dropship & POD Engine.
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SupplierType(str, Enum):
    CJ_DROPSHIPPING = "cj_dropshipping"
    PRINTIFY = "printify"
    PRINTFUL = "printful"
    MANUAL = "manual"


class FulfillmentStatus(str, Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    IN_PRODUCTION = "in_production"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ProductVariant(BaseModel):
    variant_id: str
    title: str
    sku: str
    cost_price: float
    retail_price: float
    currency: str = "USD"
    inventory_quantity: int = 999
    size: Optional[str] = None
    color: Optional[str] = None
    supplier_variant_id: Optional[str] = None
    supplier_sku: Optional[str] = None


class CatalogProduct(BaseModel):
    product_id: str
    title: str
    handle: str
    description_html: str
    vendor: str
    product_type: str
    supplier_type: SupplierType
    supplier_product_id: str
    tags: List[str] = Field(default_factory=list)
    images: List[str] = Field(default_factory=list)
    variants: List[ProductVariant] = Field(default_factory=list)
    shopify_product_id: Optional[str] = None
    is_published: bool = False
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class ShippingAddress(BaseModel):
    first_name: str
    last_name: str
    address1: str
    address2: Optional[str] = ""
    city: str
    province: Optional[str] = ""
    zip_code: str
    country_code: str = "US"
    country_name: str = "United States"
    phone: Optional[str] = ""


class OrderItem(BaseModel):
    line_item_id: str
    shopify_variant_id: str
    sku: str
    title: str
    quantity: int
    unit_price: float
    cost_price: float
    supplier_type: SupplierType
    supplier_product_id: Optional[str] = None
    supplier_variant_id: Optional[str] = None


class CustomerOrder(BaseModel):
    order_id: str
    shopify_order_id: str
    shopify_order_number: str
    customer_email: str
    customer_name: str
    currency: str = "USD"
    total_revenue: float
    total_cost: float
    net_profit: float
    shipping_address: ShippingAddress
    items: List[OrderItem] = Field(default_factory=list)
    status: FulfillmentStatus = FulfillmentStatus.PENDING
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class FulfillmentRecord(BaseModel):
    fulfillment_id: str
    order_id: str
    shopify_order_id: str
    supplier_type: SupplierType
    supplier_order_id: str
    status: FulfillmentStatus
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    supplier_cost: float = 0.0
    shipping_cost: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
