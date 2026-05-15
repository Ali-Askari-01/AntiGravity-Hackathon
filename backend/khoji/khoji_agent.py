from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.models import Provider

class KhojiAgent:
    def __init__(self):
        # The 6 factors weights
        self.weights = {
            "distance": 0.2,
            "rating": 0.25,
            "skill_match": 0.2,
            "price": 0.15,
            "workload": 0.1,
            "urgency_readiness": 0.1
        }

    def find_providers(self, db: Session, service_type: str, complexity: str, urgency: str) -> Dict[str, Any]:
        # 1. Query SQLite for providers that match the basic skill and are available
        all_providers = db.query(Provider).filter(Provider.is_available == True).all()
        
        # If no providers exist, return fallback
        if not all_providers:
            return {
                "status": "failed",
                "message": "Koi provider available nahi hai is waqt. (No provider is available at the moment.)"
            }

        scored_providers = []
        for provider in all_providers:
            # Check skill match (simplified logic)
            if provider.skills and service_type.lower() not in [s.lower() for s in provider.skills]:
                continue # Hard filter

            # Calculate 6 factors
            # Factor 1: Distance (Mocking distance score based on ID for demo)
            distance_score = 1.0 - (provider.id % 10) * 0.05 
            
            # Factor 2: Rating (Normalized to 0-1)
            rating_score = provider.rating / 5.0
            
            # Factor 3: Skill match / Complexity
            # Complex jobs need higher rating/experience
            skill_score = 1.0
            if complexity == "complex" and provider.rating < 4.0:
                skill_score = 0.5
                
            # Factor 4: Price
            price_score = 1.0
            if provider.base_price > 2000:
                price_score = 0.6
                
            # Factor 5: Workload
            workload_score = 1.0
            if provider.workload > 3:
                workload_score = 0.4
                
            # Factor 6: Urgency readiness
            urgency_score = 1.0
            if urgency == "emergency" and provider.workload > 1:
                urgency_score = 0.5

            # Calculate total score
            total_score = (
                (distance_score * self.weights["distance"]) +
                (rating_score * self.weights["rating"]) +
                (skill_score * self.weights["skill_match"]) +
                (price_score * self.weights["price"]) +
                (workload_score * self.weights["workload"]) +
                (urgency_score * self.weights["urgency_readiness"])
            )

            rationale = f"Provider ki rating {provider.rating} hai aur workload {provider.workload} hai. Skill match aur location munasib hai."

            scored_providers.append({
                "provider_id": provider.id,
                "name": provider.name,
                "total_score": round(total_score, 2),
                "breakdown": {
                    "distance": round(distance_score, 2),
                    "rating": round(rating_score, 2),
                    "skill_match": round(skill_score, 2),
                    "price": round(price_score, 2),
                    "workload": round(workload_score, 2),
                    "urgency": round(urgency_score, 2)
                },
                "rationale": rationale
            })

        # Sort by total_score descending
        scored_providers.sort(key=lambda x: x["total_score"], reverse=True)
        
        # Return top-3
        top_3 = scored_providers[:3]
        
        if not top_3:
             return {
                "status": "failed",
                "message": "Maazrat, aapki requirement ke mutabiq koi provider nahi mila."
            }

        return {
            "status": "success",
            "top_providers": top_3,
            "message": f"Humne {len(top_3)} behtareen providers dhoond liye hain."
        }
