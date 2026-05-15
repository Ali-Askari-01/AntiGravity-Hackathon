from sqlalchemy.orm import Session
from typing import Dict, Any
from backend.models import Booking
import uuid
import datetime

class HukumAgent:
    def create_booking(self, db: Session, session_id: str, provider_id: int, service_type: str, final_price: float, scheduled_time: str) -> Dict[str, Any]:
        """
        Simulates booking: writes to DB, generates receipt, and sends mock notification.
        """
        # 1. DB Write
        new_booking = Booking(
            session_id=session_id,
            provider_id=provider_id,
            service_type=service_type,
            price=final_price,
            status="confirmed"
        )
        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)

        # 2. Generate Receipt ID
        receipt_id = f"REC-{uuid.uuid4().hex[:8].upper()}"

        # 3. Simulate Notification
        notification_msg = f"SMS/WhatsApp sent: Your booking for {service_type} is confirmed for {scheduled_time}. Receipt: {receipt_id}."

        return {
            "status": "success",
            "booking_id": new_booking.id,
            "receipt": {
                "receipt_id": receipt_id,
                "service": service_type,
                "total_paid": final_price,
                "time": scheduled_time,
                "date_issued": datetime.datetime.now().isoformat()
            },
            "notification_log": notification_msg,
            "message": "Booking muqammal ho gayi hai! (Booking is confirmed!)"
        }
