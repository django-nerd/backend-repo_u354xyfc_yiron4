"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List

class Car(BaseModel):
    """
    Cars collection schema
    Collection name: "car"
    """
    title: str = Field(..., description="Car model name")
    brand: str = Field(..., description="Car brand/make")
    description: Optional[str] = Field(None, description="Short description")
    price: float = Field(..., ge=0, description="Price in USD")
    imageUrl: Optional[str] = Field(None, description="Hero image URL")
    modelUrl: Optional[str] = Field(None, description="3D model URL (e.g., Spline scene)")
    in_stock: bool = Field(True, description="Availability")

class CartItem(BaseModel):
    """
    Cart items collection schema
    Collection name: "cartitem"
    """
    session_id: str = Field(..., description="Client session identifier")
    product_id: str = Field(..., description="Referenced product _id as string")
    quantity: int = Field(1, ge=1, le=10, description="Quantity")

class Order(BaseModel):
    """
    Orders collection schema
    Collection name: "order"
    """
    session_id: str = Field(..., description="Client session identifier")
    items: List[dict] = Field(..., description="List of items with product and quantity")
    total: float = Field(..., ge=0, description="Order total in USD")
    status: str = Field("created", description="Order status")
