import sys
import os
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.database import SessionLocal
from backend.jadwal.jadwal_agent import JadwalAgent
from backend.models import Provider, Schedule

def run_tests():
    agent = JadwalAgent()
    db = SessionLocal()

    try:
        # 1. Fetch a provider
        provider = db.query(Provider).filter(Provider.name == "Ali AC Services").first()
        if not provider:
            print("❌ Provider not found.")
            return

        # Clear existing schedules for this provider for clean test
        db.query(Schedule).filter(Schedule.provider_id == provider.id).delete()
        db.commit()

        print(f"\n{'='*55}")
        print(f"Scenario A: Slot Available")
        req_time = "2026-05-21T10:00:00"
        res = agent.validate_and_book(db, provider.id, req_time)
        print(f"Result: {res['status']} - {res['message']}")

        # 2. Occupy the slot
        print(f"\n{'='*55}")
        print(f"Action: Occupying slot 10:00 - 12:00")
        agent.occupy_slot(db, provider.id, req_time)

        # 3. Scenario B: Conflict Detected
        print(f"\n{'='*55}")
        print(f"Scenario B: Conflict (Requesting 11:00 AM)")
        req_time_conflict = "2026-05-21T11:00:00"
        res = agent.validate_and_book(db, provider.id, req_time_conflict)
        print(f"Result: {res['status']} - {res['message']}")
        if "alternatives" in res:
            print(f"Alternatives: {res['alternatives']}")

        # 4. Scenario C: Fully Booked (Simulate by filling next few slots)
        print(f"\n{'='*55}")
        print(f"Scenario C: Fully Booked (Waitlist)")
        # Occupy next 48 hours in chunks
        for h in range(12, 60, 2):
            t = (datetime.fromisoformat(req_time) + timedelta(hours=h-10)).isoformat()
            agent.occupy_slot(db, provider.id, t)
        
        res = agent.validate_and_book(db, provider.id, "2026-05-21T14:00:00")
        print(f"Result: {res['status']} - {res['message']}")

    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
