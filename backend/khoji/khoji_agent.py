import os
import math
import json
import logging
import requests
from pathlib import Path
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.models import Provider
from dotenv import load_dotenv

_env_file = Path(__file__).parent.parent / ".env"
load_dotenv(_env_file) if _env_file.exists() else None
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


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


def geocode_location(location: str) -> tuple[float, float] | None:
    if not MAPS_API_KEY:
        logger.warning("GOOGLE_MAPS_API_KEY not set, skipping geocoding")
        return None
    query = f"{location}, Karachi, Pakistan"
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": query, "key": MAPS_API_KEY}
    try:
        resp = requests.get(url, params=params, timeout=8)
        data = resp.json()
        if data.get("status") == "OK" and data.get("results"):
            loc = data["results"][0]["geometry"]["location"]
            logger.info(f"Geocoded '{location}' → ({loc['lat']}, {loc['lng']})")
            return loc["lat"], loc["lng"]
        else:
            logger.warning(f"Geocoding failed for '{location}': {data.get('status')} - {data.get('error_message', '')}")
    except requests.exceptions.Timeout:
        logger.warning(f"Geocoding timeout for '{location}'")
    except Exception as e:
        logger.error(f"Geocoding request error: {e}")
    return None


class KhojiAgent:

    SECTOR_COORDS = {
        "gulshan": (24.9200, 67.0950),
        "gulshan-e-iqbal": (24.9200, 67.0950),
        "gulshan e iqbal": (24.9200, 67.0950),
        "gulshan-e-iqbal block 1": (24.9170, 67.0900),
        "gulshan-e-iqbal block 13": (24.9240, 67.0980),
        "dha": (24.8100, 67.0700),
        "dha phase 1": (24.8150, 67.0650),
        "dha phase 2": (24.8050, 67.0680),
        "dha phase 5": (24.8200, 67.0570),
        "dha phase 6": (24.8230, 67.0500),
        "dha phase 7": (24.8300, 67.0650),
        "dha phase 8": (24.8350, 67.0750),
        "clifton": (24.8138, 67.0300),
        "clifton block 1": (24.8150, 67.0320),
        "clifton block 2": (24.8100, 67.0280),
        "clifton block 5": (24.8080, 67.0250),
        "clifton block 8": (24.8180, 67.0180),
        "pechs": (24.8700, 67.0450),
        "north nazimabad": (24.9430, 67.0430),
        "nazimabad": (24.9190, 67.0350),
        "f.b. area": (24.9350, 67.0600),
        "federal b area": (24.9350, 67.0600),
        "johar": (24.9060, 67.1180),
        "gulistan-e-johar": (24.9060, 67.1180),
        "gulistan-e-johar block 1": (24.9030, 67.1100),
        "gulistan-e-johar block 14": (24.9090, 67.1250),
        "korangi": (24.8280, 67.1280),
        "korangi industrial": (24.8350, 67.1350),
        "saddar": (24.8610, 67.0100),
        "lyari": (24.8670, 67.0040),
        "orangi": (24.9550, 67.0050),
        "orangi town": (24.9550, 67.0050),
        "malir": (24.8920, 67.1940),
        "malir cantonment": (24.8850, 67.1850),
        "landhi": (24.8550, 67.1640),
        "bahadurabad": (24.8750, 67.0650),
        "burns garden": (24.8610, 67.0250),
        "defence": (24.8100, 67.0700),
        "defence view": (24.8000, 67.0600),
        "keamari": (24.8500, 66.9800),
        "site": (24.8850, 67.0150),
        "site industrial": (24.8850, 67.0150),
        "shah faisal": (24.8750, 67.0750),
        "shah faisal colony": (24.8750, 67.0750),
        "liaquatabad": (24.9250, 67.0300),
        "liaquatabad block 1": (24.9230, 67.0280),
        "garden": (24.8700, 67.0200),
        "garden east": (24.8720, 67.0250),
        "buffer zone": (24.9400, 67.0500),
        "north karachi": (24.9500, 67.0550),
        "sharifabad": (24.9280, 67.0400),
        "water pump": (24.9260, 67.0480),
        "ancholi": (24.9130, 67.0520),
        "numaish": (24.8640, 67.0300),
        "regal chowk": (24.8600, 67.0150),
        "tariq road": (24.8750, 67.0600),
        "zamzama": (24.8120, 67.0250),
        "do darya": (24.8020, 67.0200),
        "boat basin": (24.8100, 67.0300),
        "sea view": (24.7950, 67.0450),
        "hawkesbay": (24.8700, 66.9700),
        "manora": (24.8000, 66.9800),
        "shahrah-e-faisal": (24.8700, 67.0800),
        "jinnah": (24.8620, 67.0200),
        " Civic Center": (24.8700, 67.0450),
        "pir ilahi bux": (24.9360, 67.0530),
        "nusrat bhutto": (24.9200, 67.0600),
        "azizabad": (24.9180, 67.0520),
        "karachi": (24.8862, 67.0693),
    }

    def __init__(self):
        from backend.llm_client import call_llm
        self._call_llm = call_llm

    def _get_user_coords(self, location: str) -> tuple[float, float]:
        coords = geocode_location(location)
        if coords:
            return coords
        key = location.lower().strip()
        if key in self.SECTOR_COORDS:
            return self.SECTOR_COORDS[key]
        for sector_key, sector_coords in self.SECTOR_COORDS.items():
            if sector_key in key or key in sector_key:
                return sector_coords
        tokens = key.replace(",", " ").replace("-", " ").split()
        for token in tokens:
            if token in self.SECTOR_COORDS:
                return self.SECTOR_COORDS[token]
        for sector_key, sector_coords in self.SECTOR_COORDS.items():
            for token in tokens:
                if token and token in sector_key:
                    return sector_coords
        logger.warning(f"Unknown location '{location}' — defaulting to central Karachi.")
        return (24.8862, 67.0693)

    def _ai_rationale(self, provider_name: str, service_type: str, location: str,
                      rating: float, experience: int, distance_km: float,
                      available: bool, urgency: str) -> str:
        avail_str = "available" if available else "unavailable"
        prompt = (
            f"You are Khoji, a smart provider-matching agent for a Pakistani service app.\n"
            f"Generate a brief (1-2 sentence) Urdu+English mixed rationale for why this provider "
            f"is recommended. Be specific about their strengths. Keep it natural and conversational.\n"
            f"Provider: {provider_name}, Service: {service_type}, Location: {location}, "
            f"Rating: {rating}/5, Experience: {experience} years, Distance: {distance_km}km, "
            f"Status: {avail_str}, Urgency: {urgency}.\n"
            f"Respond in roman Urdu + English mix. Example style: "
            f"'Ali ka experience 8 saal hai aur rating 4.8 hai — qareeb aur reliable option hai.'\n"
            f"Rationale:"
        )
        text = self._call_llm(prompt)
        if text and len(text) > 10:
            return text.strip()
        return self._static_rationale(rating, experience, distance_km, available, urgency, provider_name)

    @staticmethod
    def _static_rationale(rating, experience, distance_km, available, urgency, name):
        parts = []
        if distance_km <= 3:
            parts.append("qareeb hai")
        elif distance_km <= 6:
            parts.append("munasib doori par hai")
        else:
            parts.append("thora door hai")
        if rating >= 4.7:
            parts.append("bohot acha rated")
        elif rating >= 4.0:
            parts.append("acha rated")
        if experience >= 7:
            parts.append("tajurbakar")
        if urgency in ("urgent", "emergency") and available:
            parts.append("abhi available")
        return ", ".join(parts) if parts else "suitable match"

    def find_providers(
        self,
        db: Session,
        service_type: str,
        location: str,
        urgency: str = "normal",
        user_lat: float = None,
        user_lng: float = None,
    ) -> Dict[str, Any]:

        if user_lat is not None and user_lng is not None:
            user_lat, user_lng = float(user_lat), float(user_lng)
            trace_lines = [f"AI Agent Khoji: Searching for {service_type} near user GPS ({user_lat:.4f}, {user_lng:.4f})..."]
        else:
            user_lat, user_lng = self._get_user_coords(location)
            trace_lines = [f"AI Agent Khoji: Searching for {service_type} in {location}..."]

        all_providers = db.query(Provider).all()

        matched = [
            p for p in all_providers
            if p.skills and service_type.lower() in [s.lower() for s in p.skills]
        ]

        if not matched:
            trace_lines.append(f"No exact {service_type} providers found. AI expanding search to similar services...")
            skill_groups = {
                "electrician": ["electrician", "welder"],
                "plumber": ["plumber", "gas_technician"],
                "ac_technician": ["ac_technician", "gas_technician"],
                "carpenter": ["carpenter", "painter"],
                "painter": ["painter", "carpenter"],
                "cleaner": ["home_cleaner", "pest_control"],
                "mechanic": ["mechanic"],
                "gas_technician": ["gas_technician", "plumber"],
                "pest_control": ["pest_control", "home_cleaner"],
                "home_cleaner": ["home_cleaner", "pest_control"],
                "tiler": ["tiler", "carpenter"],
                "welder": ["welder", "electrician"],
            }
            similar_skills = skill_groups.get(service_type.lower(), [service_type])
            matched = [
                p for p in all_providers
                if p.skills and any(s.lower() in [sk.lower() for sk in p.skills] for s in similar_skills)
            ]
            if matched:
                trace_lines.append(f"AI found {len(matched)} providers with similar skills.")
            else:
                trace_lines.append("No similar providers found. Showing nearest available providers.")
                matched = all_providers

        trace_lines.append(f"AI ranking {len(matched)} providers using 6-factor scoring...")

        scored = []
        for p in matched:
            pdict = {
                "lat": p.lat, "lng": p.lng,
                "rating": p.rating, "available": p.is_available,
                "experience": p.experience,
            }
            dist_km = haversine(user_lat, user_lng, p.lat, p.lng)
            max_distance = 15.0
            distance_score = 1 - min(dist_km / max_distance, 1.0)
            rating_score = (pdict["rating"] - 1) / 4
            availability = 1.0 if pdict["available"] else 0.0
            experience = min(pdict["experience"] / 10, 1.0)
            urgency_bonus = 0.1 if urgency == "urgent" and pdict["available"] else 0.0
            trust_score = rating_score * 0.6 + experience * 0.4
            score = (0.35 * distance_score
                     + 0.30 * trust_score
                     + 0.20 * availability
                     + 0.10 * experience
                     + 0.05 * urgency_bonus)
            score = round(score, 4)
            dist_km = round(dist_km, 2)

            avail_label = "YES" if p.is_available else "NO"
            trace_lines.append(
                f"AI: {p.name}: score={score}, dist={dist_km}km, rating={p.rating}, avail={avail_label}"
            )

            rationale = self._ai_rationale(
                p.name, service_type, location,
                p.rating, p.experience, dist_km,
                p.is_available, urgency
            )

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
                "lat": p.lat,
                "lng": p.lng,
                "rationale": rationale,
            })

        scored.sort(key=lambda x: (0 if x["available"] else -1, x["score"]), reverse=True)
        top_3 = scored[:3]

        if top_3:
            winner = top_3[0]
            trace_lines.append(f"AI selected: {winner['name']} — {winner['rationale']}")

        if len(matched) > 0:
            message = f"Humne {len(top_3)} behtareen providers dhoond liye hain."
        else:
            message = f"Maazrat, {service_type} ka koi provider available nahi mila."

        return {
            "status": "success" if top_3 else "failed",
            "user_location": {"lat": user_lat, "lng": user_lng},
            "total_found": len(matched),
            "top_providers": top_3,
            "message": message,
            "trace": trace_lines,
        }