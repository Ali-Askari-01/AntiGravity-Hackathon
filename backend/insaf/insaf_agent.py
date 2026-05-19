import os
import json
import logging
from pathlib import Path
from typing import Dict, Any
from sqlalchemy.orm import Session
from backend.models import Provider, Booking, Feedback, Dispute
from sqlalchemy import func
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InsafAgent:
    def __init__(self):
        from backend.llm_client import call_llm_json
        self._call_llm_json = call_llm_json

    def classify_dispute(self, issue_type: str, description: str, booking_data: Dict[str, Any]) -> Dict[str, Any]:
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

    def _ai_resolve_dispute(self, dispute_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = (
            f"You are Insaf, an AI dispute resolution agent for a Pakistani service booking app called XIDMAT.AI.\n"
            f"Analyze the following dispute and provide a resolution recommendation.\n\n"
            f"Booking Details:\n"
            f"- Service: {dispute_data.get('service_type', 'Unknown')}\n"
            f"- Price: PKR {dispute_data.get('price', 0):,}\n"
            f"- Provider: {dispute_data.get('provider_name', 'Unknown')}\n"
            f"- Issue Type: {dispute_data.get('issue_type', 'Unknown')}\n"
            f"- Description: {dispute_data.get('description', 'No description')}\n"
            f"- Provider Rating: {dispute_data.get('provider_rating', 'N/A')}\n\n"
            f"Provide your response as JSON with these fields:\n"
            f'- "resolution_type": one of "full_refund", "partial_refund", "redo_service", or "escalate"\n'
            f'- "refund_percentage": number 0-100 (percentage of booking price to refund)\n'
            f'- "provider_penalty": number -0.5 to 0 (rating penalty to apply to provider, e.g. -0.3)\n'
            f'- "message": a brief explanation in roman Urdu+English mix for the customer (2-3 sentences)\n'
            f'- "provider_warning": a brief warning message for the provider\n\n'
            f'Respond ONLY with valid JSON, no markdown.'
        )
        return self._call_llm_json(prompt)

    def handle_dispute(self, db: Session, booking_id: int, issue_type: str, description: str) -> Dict[str, Any]:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise ValueError("Booking not found")

        provider = db.query(Provider).filter(Provider.id == booking.provider_id).first()

        dispute_data = {
            "service_type": booking.service_type,
            "price": booking.price,
            "provider_name": provider.name if provider else "Unknown",
            "provider_rating": provider.rating if provider else None,
            "issue_type": issue_type,
            "description": description,
        }

        booking_data = {"final_price": booking.price}
        resolution = self.classify_dispute(issue_type, description, booking_data)

        ai_resolution = self._ai_resolve_dispute(dispute_data)

        if ai_resolution:
            resolution_type = ai_resolution.get("resolution_type", resolution["action"])
            message = ai_resolution.get("message", resolution["message"])
            provider_penalty = float(ai_resolution.get("provider_penalty", resolution["provider_penalty"]))
            provider_warning = ai_resolution.get("provider_warning", "")

            if provider_penalty != resolution["provider_penalty"]:
                resolution["provider_penalty"] = provider_penalty

            resolution["action"] = resolution_type
            resolution["message"] = message
            if provider_warning:
                resolution["provider_warning"] = provider_warning

        if provider:
            old_rating = provider.rating or 5.0
            new_rating = max(1.0, old_rating + resolution["provider_penalty"])
            provider.rating = round(new_rating, 2)
            db.commit()

        dispute = Dispute(
            booking_id=booking_id,
            issue_type=issue_type,
            description=description,
            resolution=resolution["message"],
            status="RESOLVED"
        )
        db.add(dispute)
        db.commit()

        trace_log = self._generate_trace_log(issue_type, booking.price, resolution)

        return {
            "status": "resolved",
            "resolution": resolution["message"],
            "trace_log": trace_log,
            "new_rating": provider.rating if provider else None,
            "resolution_type": resolution.get("action", "unknown"),
            "ai_powered": ai_resolution is not None
        }

    def update_provider_rating(self, db: Session, provider_id: int):
        avg_rating = db.query(func.avg(Feedback.rating)).filter(Feedback.provider_id == provider_id).scalar()
        if avg_rating is not None:
            db.query(Provider).filter(Provider.id == provider_id).update({"rating": round(avg_rating, 2)})
            db.commit()

    def _generate_trace_log(self, issue_type: str, price: float, resolution: Dict[str, Any]) -> str:
        ai_tag = " [AI-Enhanced]" if resolution.get("ai_powered") else ""
        log = [
            f"[Insaf]{ai_tag}  Dispute received: {issue_type}",
            f"[Insaf]{ai_tag}  Confirmed price: PKR {price:,}",
            f"[Insaf]{ai_tag}  Classification: {issue_type}",
            f"[Insaf]{ai_tag}  Resolution: {resolution['action'].replace('_', ' ').title()}",
            f"[Insaf]{ai_tag}  Provider penalty: {resolution['provider_penalty']} rating impact applied"
        ]
        return "\n".join(log)