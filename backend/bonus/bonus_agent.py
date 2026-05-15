from sqlalchemy.orm import Session
from typing import Dict, Any, List
from backend.models import Provider, Booking
from datetime import datetime

class BonusAgent:
    def optimize_provider(self, db: Session, provider_id: int) -> Dict[str, Any]:
        """
        Provider-side optimization: analyzes workload, forecasts demand, 
        and suggests optimal time slots or price adjustments.
        """
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        if not provider:
            return {"status": "error", "message": "Provider not found"}

        # 1. Workload Analysis
        # Mocking active bookings count (In real life, count bookings where status = 'confirmed')
        active_bookings_count = db.query(Booking).filter(
            Booking.provider_id == provider_id, 
            Booking.status == 'confirmed'
        ).count()
        
        provider.workload = active_bookings_count
        db.commit()

        # 2. Demand Forecast (Mocked logic)
        current_hour = datetime.now().hour
        is_peak_hours = 18 <= current_hour <= 22 # Peak demand between 6 PM - 10 PM
        
        recommendations = []
        if is_peak_hours:
            recommendations.append("High demand expected. Consider increasing availability or charging a surge premium.")
        else:
            recommendations.append("Low demand hours. Offer discounts to attract more bookings.")

        if active_bookings_count > 4:
            recommendations.append("Workload is very high. Adding a 30-min buffer between jobs is strongly recommended to avoid burnout.")

        # 3. Suggest Time Slots
        suggested_slots = []
        if active_bookings_count < 2:
            suggested_slots = ["10:00 AM", "02:00 PM", "05:00 PM"]
        else:
            suggested_slots = ["04:00 PM", "07:00 PM"]

        return {
            "status": "success",
            "provider_name": provider.name,
            "current_workload": active_bookings_count,
            "demand_forecast": "Peak" if is_peak_hours else "Normal",
            "recommendations": recommendations,
            "suggested_slots": suggested_slots,
            "message": "Optimization report generated successfully."
        }
