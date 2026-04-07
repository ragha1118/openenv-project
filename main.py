from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import sqlite3
import json
import random
from enum import Enum

app = FastAPI(title="Smart Parking Management", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="."), name="static")

# Enums
class SlotStatus(str, Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"

class VehicleType(str, Enum):
    CAR = "car"
    BIKE = "bike"
    SUV = "suv"

# Models
class BookingRequest(BaseModel):
    vehicle_number: str
    vehicle_type: VehicleType
    start_time: str  # ISO format: "2024-01-15T10:00:00"
    end_time: str    # ISO format: "2024-01-15T12:00:00"

class Booking(BaseModel):
    id: int
    slot_id: int
    vehicle_number: str
    vehicle_type: VehicleType
    start_time: str
    end_time: str
    status: str
    price: float
    created_at: str

# In-memory data (90 slots)
parking_slots = []
bookings = []

def init_db():
    global parking_slots, bookings
    
    # Initialize 90 parking slots
    for i in range(1, 91):
        status = random.choice([SlotStatus.AVAILABLE.value, SlotStatus.OCCUPIED.value, SlotStatus.RESERVED.value])
        parking_slots.append({
            "id": i,
            "status": status,
            "zone": f"A{(i-1)//30 + 1}",
            "booking_id": None if status == "available" else None
        })
    
    # Add some sample bookings
    sample_bookings = [
        {"slot_id": 5, "vehicle_number": "DL01AB1234", "vehicle_type": "car", "start_time": "2024-12-20T10:00:00", "end_time": "2024-12-20T12:00:00", "status": "active", "price": 80.0},
        {"slot_id": 12, "vehicle_number": "MH02CD5678", "vehicle_type": "bike", "start_time": "2024-12-20T14:00:00", "end_time": "2024-12-20T15:00:00", "status": "active", "price": 40.0},
    ]
    
    for i, booking in enumerate(sample_bookings):
        booking["id"] = i + 1
        booking["created_at"] = "2024-12-20T09:00:00"
        bookings.append(booking)
        # Update slot status
        for slot in parking_slots:
            if slot["id"] == booking["slot_id"]:
                slot["status"] = "occupied"
                slot["booking_id"] = booking["id"]
                break

# Initialize data
init_db()

@app.get("/")
async def serve_frontend():
    return {"message": "Smart Parking API is running!"}

@app.get("/api/slots")
async def get_slots():
    return {"slots": parking_slots, "total": len(parking_slots)}

@app.get("/api/stats")
async def get_stats():
    available = len([s for s in parking_slots if s["status"] == "available"])
    occupied = len([s for s in parking_slots if s["status"] == "occupied"])
    reserved = len([s for s in parking_slots if s["status"] == "reserved"])
    
    total_revenue = sum(b["price"] for b in bookings if b["status"] == "completed")
    
    return {
        "total_slots": len(parking_slots),
        "available": available,
        "occupied": occupied,
        "reserved": reserved,
        "revenue": total_revenue
    }

@app.post("/api/book/{slot_id}")
async def book_slot(slot_id: int, booking: BookingRequest):
    # Check if slot exists and is available
    slot = next((s for s in parking_slots if s["id"] == slot_id), None)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    if slot["status"] != "available":
        raise HTTPException(status_code=400, detail="Slot not available")
    
    # Calculate duration and price
    start = datetime.fromisoformat(booking.start_time.replace('Z', '+00:00'))
    end = datetime.fromisoformat(booking.end_time.replace('Z', '+00:00'))
    duration_hours = (end - start).total_seconds() / 3600
    price = round(duration_hours * 40, 2)
    
    # Create booking
    new_booking = {
        "id": len(bookings) + 1,
        "slot_id": slot_id,
        "vehicle_number": booking.vehicle_number,
        "vehicle_type": booking.vehicle_type,
        "start_time": booking.start_time,
        "end_time": booking.end_time,
        "status": "active",
        "price": price,
        "created_at": datetime.now().isoformat()
    }
    
    bookings.append(new_booking)
    
    # Update slot
    slot["status"] = "occupied"
    slot["booking_id"] = new_booking["id"]
    
    return {"message": "Booking successful!", "booking": new_booking}

@app.get("/api/bookings")
async def get_bookings():
    return {"bookings": bookings}

@app.delete("/api/cancel/{booking_id}")
async def cancel_booking(booking_id: int):
    booking = next((b for b in bookings if b["id"] == booking_id), None)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking["status"] == "completed":
        raise HTTPException(status_code=400, detail="Cannot cancel completed booking")
    
    # Update booking status
    booking["status"] = "cancelled"
    
    # Free the slot
    for slot in parking_slots:
        if slot["booking_id"] == booking_id:
            slot["status"] = "available"
            slot["booking_id"] = None
            break
    
    return {"message": "Booking cancelled successfully!"}

@app.get("/api/hourly-occupancy")
async def get_hourly_occupancy():
    # Simulate hourly data
    hours = list(range(24))
    occupancy = [random.randint(20, 80) for _ in hours]
    return {"hours": hours, "occupancy": occupancy}