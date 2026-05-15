from pydantic import BaseModel
from typing import Optional

class IntentResponse(BaseModel):
    intent: str
    confidence_score: float
    clarifying_question: Optional[str] = None
    job_complexity: str  # "basic", "intermediate", "complex"
    urgency_level: str   # "normal", "urgent", "emergency"

class ZubanAgent:
    def parse_input(self, text: str) -> IntentResponse:
        # Mocking multilingual NLP parsing for now
        text_lower = text.lower()
        
        # Simple heuristic rules for mocking
        urgency_level = "normal"
        if "emergency" in text_lower or "urgent" in text_lower or "jaldi" in text_lower:
            urgency_level = "emergency"
        elif "asap" in text_lower or "fast" in text_lower:
            urgency_level = "urgent"

        job_complexity = "basic"
        if "wiring" in text_lower or "plumbing" in text_lower:
            job_complexity = "intermediate"
        elif "build" in text_lower or "construction" in text_lower:
            job_complexity = "complex"

        # Mocking confidence based on length or specific keywords
        confidence = 0.9
        clarifying_question = None
        if len(text.split()) < 3:
            confidence = 0.6
            clarifying_question = "Could you please provide more details about what you need?"

        return IntentResponse(
            intent="service_request",
            confidence_score=confidence,
            clarifying_question=clarifying_question,
            job_complexity=job_complexity,
            urgency_level=urgency_level
        )
