from typing import Dict, Any
from datetime import datetime

class QeematAgent:
    def __init__(self):
        # Configuration for pricing components
        self.urgency_map = {
            'urgent': 0.25,
            'normal': 0.0,
            'flexible': -0.05
        }
        self.distance_threshold = 2.0  # km
        self.distance_rate = 20.0     # PKR per km
        self.quality_threshold = 4.5
        self.quality_premium_rate = 0.10
        self.experience_threshold = 5   # years
        self.experience_premium_rate = 0.08
        self.peak_hour_surcharge = 0.15 # 15%
        self.tax_rate = 0.0

    def is_peak_hour(self, appointment_time: datetime) -> bool:
        """
        Peak hour surcharge (8–10 AM and 5–8 PM)
        """
        hour = appointment_time.hour
        if (8 <= hour < 10) or (17 <= hour < 20):
            return True
        return False

    def calculate_price(self, base_rate: float, urgency: str, distance_km: float, 
                        appointment_time: datetime, provider_rating: float, 
                        experience_years: int) -> Dict[str, Any]:
        """
        Calculates the final price using the 7-component formula.
        """
        # Component 1: Base rate
        current_price = base_rate
        
        # Component 2: Urgency surcharge
        urgency_surcharge = base_rate * self.urgency_map.get(urgency.lower(), 0.0)
        current_price += urgency_surcharge

        # Component 3: Distance fee (PKR 20 per km beyond 2km)
        distance_fee = 0.0
        if distance_km > self.distance_threshold:
            # Base 20 PKR surcharge for exceeding threshold + 20 PKR per km beyond it
            distance_fee = self.distance_rate + (distance_km - self.distance_threshold) * self.distance_rate
        current_price += distance_fee

        # Component 4: Peak hour surcharge
        peak_surcharge = 0.0
        is_peak = self.is_peak_hour(appointment_time)
        if is_peak:
            peak_surcharge = current_price * self.peak_hour_surcharge
            current_price += peak_surcharge

        # Component 5: Quality premium (rating above 4.5)
        quality_premium = 0.0
        if provider_rating >= self.quality_threshold:
            quality_premium = base_rate * self.quality_premium_rate
            current_price += quality_premium

        # Component 6: Experience premium (above 5 years)
        experience_premium = 0.0
        if experience_years > self.experience_threshold:
            experience_premium = base_rate * self.experience_premium_rate
            current_price += experience_premium

        # Component 7: Tax
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

        trace_log = self._generate_trace_log(breakdown, urgency, distance_km, provider_rating, experience_years)

        return {
            "final_price": final_price,
            "breakdown": breakdown,
            "trace_log": trace_log,
            "is_peak": is_peak
        }

    def _generate_trace_log(self, breakdown: Dict[str, float], urgency: str, 
                           distance: float, rating: float, experience: int) -> str:
        """
        Generates a formatted trace log as per PRD.
        """
        log = [
            f"💰 Calculating price...",
            f"   Base rate:          PKR {breakdown['base_rate']:,}",
            f"   Urgency ({urgency}):   +PKR {breakdown['urgency']:,}",
            f"   Distance ({distance}km):   +PKR {breakdown['distance']:,}",
            f"   Peak hour:          +PKR {breakdown['peak_hour']:,}",
            f"   Quality premium:    +PKR {breakdown['quality_premium']:,}",
            f"   Experience bonus:   +PKR {breakdown['experience_premium']:,}",
            f"✅  Final price: PKR {breakdown['total']:,}"
        ]
        return "\n".join(log)
