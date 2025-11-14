import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Customer, Technician, Booking, Review, Payment

app = FastAPI(title="On-Call Repairs & Maintenance API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "On-Call Repairs & Maintenance Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Connected & Working"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


# Utilities
class IdModel(BaseModel):
    id: str


def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")


# Public schemas endpoint to aid admin tools
@app.get("/schema")
def get_schema():
    return {
        "customer": Customer.model_json_schema(),
        "technician": Technician.model_json_schema(),
        "booking": Booking.model_json_schema(),
        "review": Review.model_json_schema(),
        "payment": Payment.model_json_schema(),
    }


# Bookings
@app.post("/bookings", response_model=dict)
def create_booking(payload: Booking):
    booking_id = create_document("booking", payload)
    return {"id": booking_id}


@app.get("/bookings", response_model=List[dict])
def list_bookings(status: Optional[str] = None, limit: int = 50):
    flt = {"status": status} if status else {}
    docs = get_documents("booking", flt, limit)
    for d in docs:
        d["id"] = str(d.get("_id"))
        d.pop("_id", None)
    return docs


@app.post("/bookings/assign", response_model=dict)
def assign_technician(data: dict):
    booking_id = data.get("booking_id")
    technician_id = data.get("technician_id")
    if not booking_id or not technician_id:
        raise HTTPException(400, detail="booking_id and technician_id required")
    r = db["booking"].update_one(
        {"_id": _oid(booking_id)},
        {"$set": {"technician_id": technician_id, "status": "assigned", "updated_at": datetime.utcnow()}},
    )
    if r.matched_count == 0:
        raise HTTPException(404, detail="Booking not found")
    return {"ok": True}


@app.post("/track/update", response_model=dict)
def update_technician_location(data: dict):
    technician_id = data.get("technician_id")
    lat = data.get("lat")
    lng = data.get("lng")
    if not technician_id or lat is None or lng is None:
        raise HTTPException(400, detail="technician_id, lat, lng required")
    r = db["technician"].update_one(
        {"_id": _oid(technician_id)},
        {"$set": {"lat": float(lat), "lng": float(lng), "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    return {"ok": True}


@app.get("/track/{technician_id}", response_model=dict)
def get_technician_location(technician_id: str):
    doc = db["technician"].find_one({"_id": _oid(technician_id)})
    if not doc:
        raise HTTPException(404, detail="Technician not found")
    return {"lat": doc.get("lat", 0), "lng": doc.get("lng", 0)}


# Reviews
@app.post("/reviews", response_model=dict)
def create_review(payload: Review):
    review_id = create_document("review", payload)
    # update aggregate rating on technician
    try:
        tid = payload.technician_id
        reviews = db["review"].find({"technician_id": tid})
        ratings = [r.get("rating", 0) for r in reviews]
        if ratings:
            avg = sum(ratings) / len(ratings)
            db["technician"].update_one(
                {"_id": _oid(tid)}, {"$set": {"rating_avg": avg, "rating_count": len(ratings)}}
            )
    except Exception:
        pass
    return {"id": review_id}


@app.get("/technicians", response_model=List[dict])
def list_technicians(limit: int = 50):
    docs = get_documents("technician", {}, limit)
    for d in docs:
        d["id"] = str(d.get("_id"))
        d.pop("_id", None)
    return docs


# Payments (mock provider)
@app.post("/payments/intent", response_model=dict)
def create_payment_intent(payload: Payment):
    # In real world, integrate Stripe/Adyen. Here we mock the flow.
    tx_id = create_document("payment", payload)
    db["payment"].update_one({"_id": _oid(tx_id)}, {"$set": {"status": "pending", "transaction_id": tx_id}})
    return {"client_secret": f"mock_secret_{tx_id}", "transaction_id": tx_id}


@app.post("/payments/confirm", response_model=dict)
def confirm_payment(data: dict):
    tx_id = data.get("transaction_id")
    if not tx_id:
        raise HTTPException(400, detail="transaction_id required")
    db["payment"].update_one({"_id": _oid(tx_id)}, {"$set": {"status": "succeeded", "updated_at": datetime.utcnow()}})
    return {"status": "succeeded"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
