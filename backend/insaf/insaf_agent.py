from typing import Dict, Any
from sqlalchemy.orm import Session
from backend.models import Provider, Booking, Feedback, Dispute
from sqlalchemy import func

class InsafAgent:
    def classify_dispute(self, issue_type: str, description: str, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispute classification logic (from PRD).
        """
        resolutions = {
            'no_show': {
                'action': 'full_refund',
                'message': 'Provider did not arrive. Full refund of PKR {price} recommended.',
                'provider_penalty': -0.3
            },
            'overcharge': {
                'action': 'partial_refund',
                'message': 'Confirmed price was PKR {price}. Difference to be refunded.',
                'provider_penalty': -0.2
            },
            'poor_quality': {
                'action': 'redo_or_partial_refund',
                'message': 'Provider to redo work or 30% refund of PKR {partial} recommended.',
                'provider_penalty': -0.15
            },
            'damage': {
                'action': 'escalate',
                'message': 'Case escalated for human review.',
                'provider_penalty': -0.5
            }
        }
        
        resolution = resolutions.get(issue_type, resolutions['poor_quality']).copy()
        resolution['message'] = resolution['message'].format(
            price=booking_data['final_price'],
            partial=round(booking_data['final_price'] * 0.3, 2)
        )
        return resolution

    def handle_dispute(self, db: Session, booking_id: int, issue_type: str, description: str) -> Dict[str, Any]:
        """
        Rigorous dispute resolution process with trace logs and DB updates.
        """
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise ValueError("Booking not found")

        # Mock booking data for classification
        booking_data = {"final_price": booking.price}
        resolution = self.classify_dispute(issue_type, description, booking_data)

        # 1. Update Provider Rating (Penalty)
        provider = db.query(Provider).filter(Provider.id == booking.provider_id).first()
        if provider:
            old_rating = provider.rating or 5.0
            new_rating = max(1.0, old_rating + resolution['provider_penalty'])
            provider.rating = round(new_rating, 2)
            db.commit()

        # 2. Log Dispute in DB
        dispute = Dispute(
            booking_id=booking_id,
            issue_type=issue_type,
            description=description,
            resolution=resolution['message'],
            status="RESOLVED"
        )
        db.add(dispute)
        db.commit()

        # 3. Generate Trace Log
        trace_log = self._generate_trace_log(issue_type, booking.price, resolution)

        return {
            "status": "resolved",
            "resolution": resolution['message'],
            "trace_log": trace_log,
            "new_rating": provider.rating if provider else None
        }

    def update_provider_rating(self, db: Session, provider_id: int):
        """
        Rating recalculation formula (from PRD).
        """
        avg_rating = db.query(func.avg(Feedback.rating)).filter(Feedback.provider_id == provider_id).scalar()
        if avg_rating is not None:
            db.query(Provider).filter(Provider.id == provider_id).update({"rating": round(avg_rating, 2)})
            db.commit()

    def _generate_trace_log(self, issue_type: str, price: float, resolution: Dict[str, Any]) -> str:
        """
        Insaf trace log output (from PRD).
        """
        log = [
            f"⚖️  [Insaf]  Dispute received: {issue_type}",
            f"🔍  [Insaf]  Confirmed price: PKR {price:,}",
            f"📋  [Insaf]  Classification: {issue_type}",
            f"✅  [Insaf]  Resolution: {resolution['action'].replace('_', ' ').title()}",
            f"⚠️  [Insaf]  Provider penalty: {resolution['provider_penalty']} rating impact applied"
        ]
        return "\n".join(log)
