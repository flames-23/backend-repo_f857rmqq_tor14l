"""
Database Schemas for On-Call Repairs & Maintenance App

Each Pydantic model represents a collection in your MongoDB database.
Collection name = lowercase of the class name (e.g., Booking -> "booking").
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class Customer(BaseModel):
    name: str = Field(..., description="Full name")
    phone: str = Field(..., description="Phone number")
    email: Optional[str] = Field(None, description="Email address")
    address: Optional[str] = Field(None, description="Address for home services")
    preferred_contact: Literal["phone", "email"] = Field("phone")


class Technician(BaseModel):
    name: str
    phone: str
    skills: List[str] = Field(default_factory=list, description="e.g., plumbing, electrical, auto-repair")
    lat: float = Field(0, description="Current latitude")
    lng: float = Field(0, description="Current longitude")
    is_available: bool = True
    rating_avg: float = 0.0
    rating_count: int = 0


class Booking(BaseModel):
    customer_name: str
    contact_phone: str
    contact_email: Optional[str] = None
    category: Literal["home", "vehicle"]
    service_type: str = Field(..., description="Type of repair or maintenance")
    address: Optional[str] = Field(None, description="Required for home services")
    vehicle_info: Optional[str] = Field(None, description="Vehicle make/model if applicable")
    scheduled_time: datetime
    price_quote: float = Field(0, ge=0)
    notes: Optional[str] = None
    status: Literal[
        "requested", "assigned", "en_route", "in_progress", "completed", "cancelled"
    ] = "requested"
    technician_id: Optional[str] = None


class Review(BaseModel):
    booking_id: str
    technician_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class Payment(BaseModel):
    booking_id: str
    amount: float = Field(..., ge=0)
    currency: Literal["usd", "eur", "gbp"] = "usd"
    provider: Literal["mock"] = "mock"
    status: Literal["pending", "succeeded", "failed"] = "pending"
    transaction_id: Optional[str] = None
