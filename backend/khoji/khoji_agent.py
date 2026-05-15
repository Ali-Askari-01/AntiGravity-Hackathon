import os
import math
import logging
import requests
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.models import Provider
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")


# ── Haversine distance (from PRD) ─────────────────────────────────────────────
def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


# ── PRD 6-factor scoring formula ──────────────────────────────────────────────
def score_provider(provider: Dict[str, Any], user_lat: float, user_lng: float, urgency: str):
    distance_km = haversine(user_lat, user_lng, provider["lat"], provider["lng"])
    max_distance = 10.0

    distance_score = 1 - min(distance_km / max_distance, 1.0)
    rating_score   = (provider["rating"] - 1) / 4
    availability   = 1.0 if provider["available"] else 0.0
    experience     = min(provider["experience"] / 10, 1.0)
    urgency_bonus  = 0.1 if urgency == "urgent" and provider["available"] else 0.0
    trust_score    = rating_score * 0.6 + experience * 0.4

    score = (0.35 * distance_score
             + 0.30 * trust_score
             + 0.20 * availability
             + 0.10 * experience
             + 0.05 * urgency_bonus)

    return round(score, 4), round(distance_km, 2)


# ── Google Maps Geocoding ─────────────────────────────────────────────────────
def geocode_location(location: str) -> tuple[float, float] | None:
    """Returns (lat, lng) for a location string using Google Maps Geocoding API."""
    if not MAPS_API_KEY:
        logger.warning("GOOGLE_MAPS_API_KEY not set — falling back to default Islamabad coords.")
        return None

    # Add "Islamabad, Pakistan" context for better results
    query = f"{location}, Islamabad, Pakistan"
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": query, "key": MAPS_API_KEY}

    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        if data.get("status") == "OK":
            loc = data["results"][0]["geometry"]["location"]
            return loc["lat"], loc["lng"]
        else:
            logger.warning(f"Geocoding failed for '{location}': {data.get('status')}")
    except Exception as e:
        logger.error(f"Geocoding request error: {e}")
    return None


class KhojiAgent:

    # Fallback coords for known Islamabad sectors (if Maps API unavailable)
    SECTOR_COORDS = {
        "g-13": (33.6938, 72.9797), "g13": (33.6938, 72.9797),
        "g-11": (33.6844, 73.0064), "g-10": (33.6892, 73.0189),
        "f-10": (33.7078, 73.0209), "f-6":  (33.7294, 73.0909),
        "f-7":  (33.7240, 73.0788), "f-8":  (33.7203, 73.0627),
        "i-8":  (33.6748, 73.0565), "i-9":  (33.6613, 73.0468),
        "dha":  (33.5651, 73.1651), "gulshan": (33.6844, 73.0950),
        "clifton": (24.8138, 67.0300),
    }

    def _get_user_coords(self, location: str) -> tuple[float, float]:
        """Try Maps API first, then fallback to sector dict, then city centre."""
        coords = geocode_location(location)
        if coords:
            return coords

        key = location.lower().strip()
        if key in self.SECTOR_COORDS:
            return self.SECTOR_COORDS[key]

        logger.warning(f"Unknown location '{location}' — defaulting to Islamabad centre.")
        return (33.6844, 73.0479)  # Islamabad centre

    def find_providers(
        self,
        db: Session,
        service_type: str,
        location: str,
        urgency: str = "normal",
    ) -> Dict[str, Any]:

        user_lat, user_lng = self._get_user_coords(location)

        # ── PRD Trace Log ────────────────────────────────────────────────────
        print(f"\n📡 Searching for {service_type} in {location}...")

        all_providers = db.query(Provider).all()
        matched = [
            p for p in all_providers
            if p.skills and service_type.lower() in [s.lower() for s in p.skills]
        ]

        if not matched:
            print(f"❌ No providers found for {service_type}.")
            return {
                "status": "failed",
                "message": f"Maazrat, {service_type} ka koi provider available nahi mila.",
                "trace": []
            }

        print(f"📊 Found {len(matched)} providers. Applying 6-factor ranking...")

        scored = []
        trace_lines = []
        for p in matched:
            pdict = {
                "lat": p.lat, "lng": p.lng,
                "rating": p.rating, "available": p.is_available,
                "experience": p.experience,
            }
            score, dist_km = score_provider(pdict, user_lat, user_lng, urgency)

            avail_label = "YES" if p.is_available else "NO"
            line = (f"   {p.name:<22} score={score}  dist={dist_km}km"
                    f"  rating={p.rating}  available={avail_label}")
            print(line)
            trace_lines.append(line)

            scored.append({
                "provider_id": p.id,
                "name": p.name,
                "score": score,
                "distance_km": dist_km,
                "rating": p.rating,
                "experience_years": p.experience,
                "available": p.is_available,
                "base_price": p.base_price,
                "location": p.location,
                "rationale": self._build_rationale(p, score, dist_km, urgency),
            })

        # Sort: unavailable providers to bottom, then by score
        scored.sort(key=lambda x: (0 if x["available"] else -1, x["score"]), reverse=True)
        top_3 = scored[:3]

        if top_3:
            winner = top_3[0]
            print(f"🏆 Selected: {winner['name']} — {winner['rationale']}")

        return {
            "status": "success",
            "user_location": {"lat": user_lat, "lng": user_lng},
            "total_found": len(matched),
            "top_providers": top_3,
            "message": f"Humne {len(top_3)} behtareen providers dhoond liye hain.",
            "trace": trace_lines,
        }

    @staticmethod
    def _build_rationale(p: Provider, score: float, dist_km: float, urgency: str) -> str:
        parts = []
        if dist_km <= 3:
            parts.append("qareeb hai")
        elif dist_km <= 6:
            parts.append("munasib doori par hai")
        else:
            parts.append("thora door hai")

        if p.rating >= 4.7:
            parts.append("bohot acha rated")
        elif p.rating >= 4.0:
            parts.append("acha rated")

        if p.experience >= 7:
            parts.append("tajurbakar")

        if urgency in ("urgent", "emergency") and p.is_available:
            parts.append("abhi available")

        return ", ".join(parts) if parts else "suitable match"
