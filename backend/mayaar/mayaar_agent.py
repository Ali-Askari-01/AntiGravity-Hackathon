from sqlalchemy.orm import Session
from typing import Dict, Any
from backend.models import Booking, Provider

class MayaarAgent:
    def update_status(self, db: Session, booking_id: int, new_status: str) -> Dict[str, Any]:
        """
        Updates the booking status: en-route, arrived, completed.
        """
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            return {"status": "error", "message": "Booking not found"}
        
        booking.status = new_status
        db.commit()
        
        return {
            "status": "success", 
            "booking_id": booking_id, 
            "current_status": new_status,
            "message": f"Aapki booking ka status update ho gaya hai: {new_status}."
        }

    def process_feedback(self, db: Session, booking_id: int, rating: float, review: str) -> Dict[str, Any]:
        """
        Takes user feedback and updates the provider's rating dynamically.
        """
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            return {"status": "error", "message": "Booking not found"}
            
        provider = db.query(Provider).filter(Provider.id == booking.provider_id).first()
        if provider:
            # Simple moving average simulation (assuming they had 10 previous ratings for mock purposes)
            # In a real app, you'd store all reviews and calculate the true average.
            current_rating = provider.rating
            new_rating = ((current_rating * 10) + rating) / 11
            provider.rating = round(new_rating, 2)
            db.commit()
            
        return {
            "status": "success",
            "provider_id": provider.id if provider else None,
            "new_rating": provider.rating if provider else None,
            "message": "Aapke feedback ka shukriya! Provider ki rating update kar di gayi hai."
        }
