import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Car, CartItem, Order

app = FastAPI(title="Car Commerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Car Commerce API running"}

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
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

# Utility to convert Mongo _id to string

def serialize_doc(doc: dict):
    if not doc:
        return doc
    doc = dict(doc)
    _id = doc.get("_id")
    if isinstance(_id, ObjectId):
        doc["id"] = str(_id)
        del doc["_id"]
    return doc

# Seed some demo cars if collection empty
@app.post("/seed", tags=["dev"])
def seed_demo():
    count = db["car"].count_documents({}) if db else 0
    if count > 0:
        return {"seeded": False, "message": "Cars already exist"}
    demo = [
        {
            "title": "Falcon GT",
            "brand": "Flames",
            "description": "High‑performance electric sports car",
            "price": 125000,
            "imageUrl": "https://images.unsplash.com/photo-1549924231-f129b911e442",
            "modelUrl": "https://prod.spline.design/8fw9Z-c-rqW3nWBN/scene.splinecode",
            "in_stock": True,
        },
        {
            "title": "Nebula X",
            "brand": "Flames",
            "description": "Luxury sedan with adaptive AI drive",
            "price": 98000,
            "imageUrl": "https://images.unsplash.com/photo-1503376780353-7e6692767b70",
            "modelUrl": "https://prod.spline.design/8fw9Z-c-rqW3nWBN/scene.splinecode",
            "in_stock": True,
        },
    ]
    ids = [create_document("car", c) for c in demo]
    return {"seeded": True, "ids": ids}

# Cars endpoints
@app.get("/cars", response_model=List[dict])
def list_cars():
    docs = get_documents("car")
    return [serialize_doc(d) for d in docs]

@app.post("/cars", status_code=201)
def create_car(payload: Car):
    _id = create_document("car", payload)
    return {"id": _id}

@app.get("/cars/{car_id}")
def get_car(car_id: str):
    try:
        doc = db["car"].find_one({"_id": ObjectId(car_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return serialize_doc(doc)

# Simple cart endpoints using session_id sent by frontend
@app.post("/cart", status_code=201)
def add_to_cart(item: CartItem):
    _id = create_document("cartitem", item)
    return {"id": _id}

@app.get("/cart/{session_id}")
def get_cart(session_id: str):
    items = get_documents("cartitem", {"session_id": session_id})
    # Join with car docs
    result = []
    for it in items:
        car = db["car"].find_one({"_id": ObjectId(it["product_id"])}) if it.get("product_id") else None
        result.append({
            "id": str(it.get("_id")),
            "product": serialize_doc(car) if car else None,
            "quantity": it.get("quantity", 1)
        })
    return result

class CheckoutRequest(BaseModel):
    session_id: str

@app.post("/checkout")
def checkout(req: CheckoutRequest):
    items = get_documents("cartitem", {"session_id": req.session_id})
    total = 0.0
    enriched = []
    for it in items:
        try:
            car = db["car"].find_one({"_id": ObjectId(it["product_id"])})
            price = float(car.get("price", 0)) if car else 0
        except Exception:
            price = 0
            car = None
        q = int(it.get("quantity", 1))
        total += price * q
        enriched.append({"product": serialize_doc(car) if car else None, "quantity": q, "subtotal": price * q})

    order_doc = Order(session_id=req.session_id, items=enriched, total=round(total, 2))
    order_id = create_document("order", order_doc)

    # Clear cart after checkout
    db["cartitem"].delete_many({"session_id": req.session_id})

    return {"order_id": order_id, "total": round(total, 2)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
