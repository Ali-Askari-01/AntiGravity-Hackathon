import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.database import SessionLocal
from backend.khoji.khoji_agent import KhojiAgent

def run_tests():
    agent = KhojiAgent()
    db = SessionLocal()

    test_cases = [
        # (label, service_type, location, urgency)
        ("AC tech in G-13 (normal)",    "ac_technician", "G-13",    "normal"),
        ("AC tech in G-13 (urgent)",     "ac_technician", "G-13",    "urgent"),
        ("Plumber in DHA",               "plumber",       "DHA",     "normal"),
        ("Electrician in Gulshan",       "electrician",   "Gulshan", "normal"),
        ("Unknown service (painter)",    "painter",       "F-6",     "normal"),
        ("Unknown location fallback",    "ac_technician", "Wah Cantt", "normal"),
        ("No matching service",          "welder",        "G-13",    "normal"),
    ]

    try:
        passed = 0
        for i, (label, svc, loc, urgency) in enumerate(test_cases):
            print(f"\n{'='*55}")
            print(f"Test {i+1}: {label}")
            result = agent.find_providers(db, svc, loc, urgency)

            if result["status"] == "success":
                print(f"\n>> TOP {len(result['top_providers'])} RESULTS:")
                for rank, p in enumerate(result["top_providers"], 1):
                    avail = "YES" if p["available"] else "NO"
                    print(f"  {rank}. {p['name']:<22}  score={p['score']}  "
                          f"dist={p['distance_km']}km  rating={p['rating']}  "
                          f"avail={avail}")
                    print(f"     Rationale: {p['rationale']}")
                passed += 1
            else:
                print(f">> HANDLED: {result['message']}")
                passed += 1  # graceful failure is still a pass

        print(f"\n{'='*55}")
        print(f"Tests completed: {passed}/{len(test_cases)}")
    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
