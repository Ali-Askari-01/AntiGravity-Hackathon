"""
Run this once to seed the SQLite database with sample providers.
Usage: python backend/seed_providers.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import engine, SessionLocal
from backend import models

# Create all tables (applies the new lat/lng/experience columns)
models.Base.metadata.create_all(bind=engine)

PROVIDERS = [
    # ── AC Technicians ───────────────────────────────────────────────────────
    {
        "name": "Ali AC Services",
        "phone": "0312-4567890",
        "skills": ["ac_technician"],
        "location": "G-13",
        "lat": 33.6938, "lng": 72.9797,
        "rating": 4.8, "experience": 8,
        "base_price": 1200.0, "workload": 1, "is_available": True,
    },
    {
        "name": "Khan Cooling Co",
        "phone": "0300-1112223",
        "skills": ["ac_technician"],
        "location": "G-11",
        "lat": 33.6844, "lng": 73.0064,
        "rating": 4.6, "experience": 7,
        "base_price": 1400.0, "workload": 2, "is_available": True,
    },
    {
        "name": "Rehman AC Works",
        "phone": "0333-5556667",
        "skills": ["ac_technician"],
        "location": "F-10",
        "lat": 33.7078, "lng": 73.0209,
        "rating": 4.3, "experience": 5,
        "base_price": 1200.0, "workload": 3, "is_available": True,
    },
    {
        "name": "Fast Cool AC",
        "phone": "0321-9998887",
        "skills": ["ac_technician"],
        "location": "I-8",
        "lat": 33.6748, "lng": 73.0565,
        "rating": 4.5, "experience": 6,
        "base_price": 1350.0, "workload": 0, "is_available": False,  # busy
    },
    {
        "name": "CoolBreeze Experts",
        "phone": "0345-0001112",
        "skills": ["ac_technician", "electrician"],
        "location": "F-7",
        "lat": 33.7240, "lng": 73.0788,
        "rating": 4.9, "experience": 10,
        "base_price": 1800.0, "workload": 2, "is_available": True,
    },
    # ── Plumbers ─────────────────────────────────────────────────────────────
    {
        "name": "Ustad Plumbing",
        "phone": "0311-2223334",
        "skills": ["plumber"],
        "location": "G-10",
        "lat": 33.6892, "lng": 73.0189,
        "rating": 4.7, "experience": 8,
        "base_price": 1000.0, "workload": 1, "is_available": True,
    },
    {
        "name": "DHA Plumbers",
        "phone": "0301-4445556",
        "skills": ["plumber"],
        "location": "DHA",
        "lat": 33.5651, "lng": 73.1651,
        "rating": 4.5, "experience": 6,
        "base_price": 1100.0, "workload": 0, "is_available": True,
    },
    {
        "name": "Gulshan Pipe Works",
        "phone": "0334-7778889",
        "skills": ["plumber"],
        "location": "Gulshan",
        "lat": 33.6844, "lng": 73.0950,
        "rating": 4.2, "experience": 4,
        "base_price": 900.0, "workload": 2, "is_available": True,
    },
    # ── Electricians ─────────────────────────────────────────────────────────
    {
        "name": "Bijli Experts",
        "phone": "0322-6667778",
        "skills": ["electrician"],
        "location": "F-8",
        "lat": 33.7203, "lng": 73.0627,
        "rating": 4.8, "experience": 10,
        "base_price": 1200.0, "workload": 1, "is_available": True,
    },
    {
        "name": "Wiring Wale",
        "phone": "0310-3334445",
        "skills": ["electrician"],
        "location": "I-9",
        "lat": 33.6613, "lng": 73.0468,
        "rating": 4.4, "experience": 5,
        "base_price": 1000.0, "workload": 3, "is_available": True,
    },
    {
        "name": "Power Solutions",
        "phone": "0302-8889990",
        "skills": ["electrician", "plumber"],
        "location": "G-13",
        "lat": 33.6960, "lng": 72.9810,
        "rating": 4.6, "experience": 7,
        "base_price": 1300.0, "workload": 0, "is_available": True,
    },
    # ── Painters ─────────────────────────────────────────────────────────────
    {
        "name": "Rang Baaz Painters",
        "phone": "0335-1234567",
        "skills": ["painter"],
        "location": "F-6",
        "lat": 33.7294, "lng": 73.0909,
        "rating": 4.5, "experience": 6,
        "base_price": 800.0, "workload": 1, "is_available": True,
    },
    # ── Carpenters ───────────────────────────────────────────────────────────
    {
        "name": "Master Carpenter",
        "phone": "0315-9876543",
        "skills": ["carpenter"],
        "location": "G-11",
        "lat": 33.6860, "lng": 73.0080,
        "rating": 4.7, "experience": 12,
        "base_price": 1500.0, "workload": 2, "is_available": True,
    },
    # ── Cleaners ─────────────────────────────────────────────────────────────
    {
        "name": "Saaf Safai Team",
        "phone": "0320-1112223",
        "skills": ["cleaner", "maid"],
        "location": "F-10",
        "lat": 33.7090, "lng": 73.0215,
        "rating": 4.3, "experience": 3,
        "base_price": 700.0, "workload": 0, "is_available": True,
    },
    # ── Mechanics ────────────────────────────────────────────────────────────
    {
        "name": "Mobile Mechanic ISB",
        "phone": "0303-3334445",
        "skills": ["mechanic", "car_repair"],
        "location": "I-8",
        "lat": 33.6750, "lng": 73.0560,
        "rating": 4.6, "experience": 8,
        "base_price": 2000.0, "workload": 1, "is_available": True,
    },
    # ── Additional 16 Providers for PRD 30+ Requirement ──────────────────────
    {
        "name": "Shahid AC Repair",
        "phone": "0313-1111111",
        "skills": ["ac_technician"],
        "location": "G-10",
        "lat": 33.6890, "lng": 73.0185,
        "rating": 4.2, "experience": 4,
        "base_price": 1100.0, "workload": 0, "is_available": True,
    },
    {
        "name": "Cool Zone",
        "phone": "0314-2222222",
        "skills": ["ac_technician"],
        "location": "Blue Area",
        "lat": 33.7088, "lng": 73.0538,
        "rating": 4.7, "experience": 9,
        "base_price": 1600.0, "workload": 1, "is_available": True,
    },
    {
        "name": "Iqbal Plumbing",
        "phone": "0315-3333333",
        "skills": ["plumber"],
        "location": "F-8",
        "lat": 33.7210, "lng": 73.0630,
        "rating": 4.1, "experience": 3,
        "base_price": 950.0, "workload": 0, "is_available": True,
    },
    {
        "name": "Water Fixers",
        "phone": "0316-4444444",
        "skills": ["plumber"],
        "location": "G-13",
        "lat": 33.6930, "lng": 72.9790,
        "rating": 4.4, "experience": 5,
        "base_price": 1050.0, "workload": 1, "is_available": True,
    },
    {
        "name": "Spark Electric",
        "phone": "0317-5555555",
        "skills": ["electrician"],
        "location": "DHA",
        "lat": 33.5655, "lng": 73.1655,
        "rating": 4.9, "experience": 11,
        "base_price": 1500.0, "workload": 2, "is_available": True,
    },
    {
        "name": "Tariq Electrician",
        "phone": "0318-6666666",
        "skills": ["electrician"],
        "location": "G-11",
        "lat": 33.6840, "lng": 73.0060,
        "rating": 4.3, "experience": 6,
        "base_price": 1100.0, "workload": 0, "is_available": True,
    },
    {
        "name": "Bright Colors",
        "phone": "0319-7777777",
        "skills": ["painter"],
        "location": "I-8",
        "lat": 33.6740, "lng": 73.0560,
        "rating": 4.6, "experience": 7,
        "base_price": 850.0, "workload": 1, "is_available": True,
    },
    {
        "name": "Wood Crafts",
        "phone": "0320-8888888",
        "skills": ["carpenter"],
        "location": "F-10",
        "lat": 33.7080, "lng": 73.0200,
        "rating": 4.8, "experience": 15,
        "base_price": 1800.0, "workload": 3, "is_available": True,
    },
    {
        "name": "Spotless Maids",
        "phone": "0321-9999999",
        "skills": ["cleaner", "maid"],
        "location": "G-13",
        "lat": 33.6940, "lng": 72.9800,
        "rating": 4.5, "experience": 4,
        "base_price": 800.0, "workload": 1, "is_available": True,
    },
    {
        "name": "A-to-Z Mechanics",
        "phone": "0322-1010101",
        "skills": ["mechanic", "car_repair"],
        "location": "G-11",
        "lat": 33.6850, "lng": 73.0070,
        "rating": 4.4, "experience": 5,
        "base_price": 1800.0, "workload": 0, "is_available": True,
    },
    {
        "name": "Clifton Cooling",
        "phone": "0323-2020202",
        "skills": ["ac_technician"],
        "location": "Clifton",
        "lat": 24.8140, "lng": 67.0310,
        "rating": 4.6, "experience": 8,
        "base_price": 1300.0, "workload": 2, "is_available": True,
    },
    {
        "name": "Gulshan Plumbers Pro",
        "phone": "0324-3030303",
        "skills": ["plumber"],
        "location": "Gulshan",
        "lat": 33.6840, "lng": 73.0940,
        "rating": 4.7, "experience": 10,
        "base_price": 1200.0, "workload": 1, "is_available": True,
    },
    {
        "name": "F-6 Electric Services",
        "phone": "0325-4040404",
        "skills": ["electrician"],
        "location": "F-6",
        "lat": 33.7290, "lng": 73.0900,
        "rating": 4.5, "experience": 7,
        "base_price": 1150.0, "workload": 0, "is_available": True,
    },
    {
        "name": "I-9 Cleaners",
        "phone": "0326-5050505",
        "skills": ["cleaner", "maid"],
        "location": "I-9",
        "lat": 33.6610, "lng": 73.0460,
        "rating": 4.2, "experience": 2,
        "base_price": 600.0, "workload": 0, "is_available": True,
    },
    {
        "name": "DHA Woodworks",
        "phone": "0327-6060606",
        "skills": ["carpenter"],
        "location": "DHA",
        "lat": 33.5650, "lng": 73.1650,
        "rating": 4.8, "experience": 14,
        "base_price": 1700.0, "workload": 2, "is_available": True,
    },
    {
        "name": "G-10 Quick Painters",
        "phone": "0328-7070707",
        "skills": ["painter"],
        "location": "G-10",
        "lat": 33.6890, "lng": 73.0190,
        "rating": 4.0, "experience": 3,
        "base_price": 750.0, "workload": 0, "is_available": True,
    },
]

def seed():
    db = SessionLocal()
    try:
        existing = db.query(models.Provider).count()
        if existing > 0:
            print(f"⚠️  Database already has {existing} providers. Skipping seed.")
            print("   Delete 'antigravity.db' and re-run to reseed.")
            return

        for p in PROVIDERS:
            provider = models.Provider(**p)
            db.add(provider)

        db.commit()
        print(f"✅ Seeded {len(PROVIDERS)} providers successfully.")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
