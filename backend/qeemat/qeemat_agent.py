import os
import json
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from dotenv import load_dotenv

_env_file = Path(__file__).parent.parent / ".env"
load_dotenv(_env_file) if _env_file.exists() else None
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


class QeematAgent:
    def __init__(self):
        self.urgency_map = {
            'urgent': 0.25,
            'normal': 0.0,
            'flexible': -0.05
        }
        self.distance_threshold = 2.0
        self.distance_rate = 20.0
        self.quality_threshold = 4.5
        self.quality_premium_rate = 0.10
        self.experience_threshold = 5
        self.experience_premium_rate = 0.08
        self.peak_hour_surcharge = 0.15
        self.tax_rate = 0.0

        self._gemini_client = None
        if GEMINI_API_KEY:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=GEMINI_API_KEY)
                logger.info("Qeemat: Gemini client initialized for AI pricing analysis")
            except Exception as e:
                logger.warning(f"Qeemat: Gemini init failed, using formula-based pricing: {e}")

    def is_peak_hour(self, appointment_time: datetime) -> bool:
        hour = appointment_time.hour
        if (8 <= hour < 10) or (17 <= hour < 20):
            return True
        return False

    def _ai_pricing_rationale(self, breakdown: Dict[str, float], urgency: str,
                               distance: float, rating: float, experience: int,
                               is_peak: bool, provider_name: str) -> str:
        if not self._gemini_client:
            return self._generate_trace_log(breakdown, urgency, distance, rating, experience)

        prompt = (
            f"You are Qeemat, an AI pricing agent for a Pakistani service booking app.\n"
            f"Generate a brief (2-3 sentence) explanation in roman Urdu + English mix for why the price "
            f"is what it is. Be specific about which factors increased or decreased the price.\n\n"
            f"Provider: {provider_name}\n"
            f"Base Rate: PKR {breakdown['base_rate']:,}\n"
            f"Urgency ({urgency}): +PKR {breakdown['urgency']:,}\n"
            f"Distance Charge ({distance}km): +PKR {breakdown['distance']:,}\n"
            f"Peak Hour Surcharge: +PKR {breakdown['peak_hour']:,}\n"
            f"Quality Premium (rating {rating}): +PKR {breakdown['quality_premium']:,}\n"
            f"Experience Bonus ({experience} years): +PKR {breakdown['experience_premium']:,}\n"
            f"Final Price: PKR {breakdown['total']:,}\n\n"
            f"Example style: 'Base rate PKR 500 hai. Urgency surcharge lag gaya qarak aapne urgent bataya. "
            f"Rating 4.8 hai isliye quality premium bhi add hua.'\n"
            f"Rationale:"
        )
        try:
            response = self._gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            text = response.text.strip()
            if text and len(text) > 15:
                return text
            return self._generate_trace_log(breakdown, urgency, distance, rating, experience)
        except Exception as e:
            logger.warning(f"Qeemat AI rationale failed, falling back: {e}")
            return self._generate_trace_log(breakdown, urgency, distance, rating, experience)

    def calculate_price(self, base_rate: float, urgency: str, distance_km: float,
                        appointment_time: datetime, provider_rating: float,
                        experience_years: int, provider_name: str = "Provider") -> Dict[str, Any]:
        current_price = base_rate

        urgency_surcharge = base_rate * self.urgency_map.get(urgency.lower(), 0.0)
        current_price += urgency_surcharge

        distance_fee = 0.0
        if distance_km > self.distance_threshold:
            distance_fee = self.distance_rate + (distance_km - self.distance_threshold) * self.distance_rate
        current_price += distance_fee

        peak_surcharge = 0.0
        is_peak = self.is_peak_hour(appointment_time)
        if is_peak:
            peak_surcharge = current_price * self.peak_hour_surcharge
            current_price += peak_surcharge

        quality_premium = 0.0
        if provider_rating >= self.quality_threshold:
            quality_premium = base_rate * self.quality_premium_rate
            current_price += quality_premium

        experience_premium = 0.0
        if experience_years > self.experience_threshold:
            experience_premium = base_rate * self.experience_premium_rate
            current_price += experience_premium

        tax_amount = current_price * self.tax_rate
        current_price += tax_amount

        final_price = round(current_price, 2)

        breakdown = {
            "base_rate": round(base_rate, 2),
            "urgency": round(urgency_surcharge, 2),
            "distance": round(distance_fee, 2),
            "peak_hour": round(peak_surcharge, 2),
            "quality_premium": round(quality_premium, 2),
            "experience_premium": round(experience_premium, 2),
            "tax": round(tax_amount, 2),
            "total": final_price
        }

        trace_log = self._ai_pricing_rationale(
            breakdown, urgency, distance_km, provider_rating,
            experience_years, is_peak, provider_name
        )

        return {
            "final_price": final_price,
            "breakdown": breakdown,
            "trace_log": trace_log,
            "is_peak": is_peak
        }

    def _generate_trace_log(self, breakdown: Dict[str, float], urgency: str,
                           distance: float, rating: float, experience: int) -> str:
        log = [
            f"Calculating price...",
            f"   Base rate:          PKR {breakdown['base_rate']:,}",
            f"   Urgency ({urgency}):   +PKR {breakdown['urgency']:,}",
            f"   Distance ({distance}km):   +PKR {breakdown['distance']:,}",
            f"   Peak hour:          +PKR {breakdown['peak_hour']:,}",
            f"   Quality premium:    +PKR {breakdown['quality_premium']:,}",
            f"   Experience bonus:   +PKR {breakdown['experience_premium']:,}",
            f"Final price: PKR {breakdown['total']:,}"
        ]
        return "\n".join(log)