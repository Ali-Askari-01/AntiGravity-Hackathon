from typing import Dict, Any

class InsafAgent:
    def handle_dispute(self, dispute_text: str, booking_id: int) -> Dict[str, Any]:
        """
        Analyzes the dispute (no-show, price issue, quality, overrun) and proposes a resolution.
        """
        text_lower = dispute_text.lower()
        
        # 1. Categorize Dispute
        category = "unknown"
        resolution_action = "human_escalation"
        message = "Aapka masla humari support team ko bhej diya gaya hai. Hum jald aapse raabta karenge."
        
        if "nahi aya" in text_lower or "no show" in text_lower or "late" in text_lower:
            category = "no_show"
            resolution_action = "provider_penalty_and_reschedule"
            message = "Maazrat chahte hain! Humne provider ko penalty flag kiya hai. Kya hum naya provider bhejain?"
            
        elif "zyada paise" in text_lower or "price" in text_lower or "mehnga" in text_lower:
            category = "price_dispute"
            resolution_action = "partial_refund_review"
            message = "Hum price ki tasdeeq kar rahay hain. Agar overcharging hui hai, toh aapko partial refund mil jayega."
            
        elif "kharab kam" in text_lower or "quality" in text_lower or "bekar" in text_lower:
            category = "quality_issue"
            resolution_action = "manager_review"
            message = "Quality ka masla darj kar liya gaya hai. Ek senior manager is kaam ka jaiza lega."
            
        elif "time" in text_lower or "bohat daer" in text_lower or "overrun" in text_lower:
            category = "time_overrun"
            resolution_action = "time_compensation"
            message = "Kaam mein zyada waqt lagne par hum maazrat khwa hain. Aapko next booking pe discount milega."

        return {
            "status": "dispute_logged",
            "booking_id": booking_id,
            "dispute_category": category,
            "resolution_action": resolution_action,
            "message": message
        }
