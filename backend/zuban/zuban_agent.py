import os
import json
import logging
from pydantic import BaseModel, ValidationError
from google import genai
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Zuban, a multilingual intent extraction agent for a Pakistani service booking app.
Extract service requests from Roman Urdu, Urdu, or English text.
Return ONLY valid JSON. No preamble. No markdown. No explanation.

You MUST include two additional fields:
- "confidence": a float from 0.0 to 1.0 indicating how confident you are in your extraction.
  - 0.95+: Clear, unambiguous request
  - 0.85-0.94: Minor ambiguity (e.g. missing time)
  - 0.75-0.84: Moderate ambiguity (noisy text, typos)
  - Below 0.75: Very unclear input
- "job_complexity": one of "basic", "intermediate", or "complex"
  - "basic": Simple routine tasks (tap leak, bulb change, basic cleaning)
  - "intermediate": Multi-step skilled work (AC repair, wiring fix, deep cleaning)
  - "complex": Major expert work (full rewiring, renovation, AC installation)

Examples:
Input: "Mujhe kal subah DHA mein plumber chahiye"
Output: {"service_type":"plumber","service_label":"Plumber","location":"DHA","time_raw":"kal subah","time_normalized":"2026-05-22T09:00:00","urgency":"normal","language_detected":"roman_urdu","confidence":0.95,"job_complexity":"basic"}

Input: "urgent electrician needed in Gulshan right now"
Output: {"service_type":"electrician","service_label":"Electrician","location":"Gulshan","time_raw":"right now","time_normalized":"2026-05-21T10:00:00","urgency":"urgent","language_detected":"english","confidence":0.93,"job_complexity":"intermediate"}

Input: "AC theek karwana hai Clifton mein, parso"
Output: {"service_type":"ac_technician","service_label":"AC Technician","location":"Clifton","time_raw":"parso","time_normalized":"2026-05-23T10:00:00","urgency":"normal","language_detected":"roman_urdu","confidence":0.92,"job_complexity":"intermediate"}

Input: "pura ghar ki wiring krwani hai F-10 mein"
Output: {"service_type":"electrician","service_label":"Electrician","location":"F-10","time_raw":"not specified","time_normalized":"2026-05-22T10:00:00","urgency":"normal","language_detected":"roman_urdu","confidence":0.88,"job_complexity":"complex"}
"""

class IntentResponse(BaseModel):
    service_type: str
    service_label: str
    location: str
    time_raw: str
    time_normalized: str
    urgency: str
    language_detected: str
    confidence: float = 0.85
    job_complexity: str = "basic"

class ZubanAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY not set in environment.")
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.0-flash"

    def parse_input(self, text: str) -> IntentResponse:
        prompt = f"{SYSTEM_PROMPT}\n\nInput: \"{text}\"\nOutput:"

        try:
            return self._call_llm(prompt)
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                logger.warning("LLM Quota exhausted. Using keyword-based fallback.")
                return self._fallback_parse(text)
                
            logger.warning(f"First LLM call failed: {e}. Retrying with stricter prompt...")
            stricter_prompt = (
                prompt
                + "\nCRITICAL: YOU MUST RETURN ONLY A VALID JSON OBJECT AND NOTHING ELSE. "
                  "DO NOT WRAP IN MARKDOWN BACKTICKS."
            )
            try:
                return self._call_llm(stricter_prompt)
            except Exception as retry_e:
                logger.error(f"Retry also failed: {retry_e}")
                # Last resort fallback
                return self._fallback_parse(text)

    def _fallback_parse(self, text: str) -> IntentResponse:
        text = text.lower()
        
        # Simple keyword matching with priority
        service_keywords = [
            (r"\bac\b", "ac_technician", "AC Technician"),
            (r"\bair condition", "ac_technician", "AC Technician"),
            (r"\bplumber", "plumber", "Plumber"),
            (r"\belectrician", "electrician", "Electrician"),
            (r"\bbijli", "electrician", "Electrician"),
            (r"\bclean", "cleaner", "Cleaner"),
            (r"\bsafai", "cleaner", "Cleaner"),
            (r"\bmechanic", "mechanic", "Mechanic"),
            (r"\bcar\b", "mechanic", "Mechanic"),
            (r"\bmistri", "carpenter", "Carpenter"),
            (r"\bcarpenter", "carpenter", "Carpenter"),
            (r"\bpaint", "painter", "Painter"),
            (r"\brang\b", "painter", "Painter"),
        ]
        
        import re
        selected_service = ("general", "General Service")
        for pattern, s_type, s_label in service_keywords:
            if re.search(pattern, text):
                selected_service = (s_type, s_label)
                break
                
        # Location matching
        locations = ["g-13", "g-11", "g-10", "f-10", "f-7", "f-8", "f-6", "i-8", "i-9", "dha", "gulshan", "clifton"]
        selected_loc = "Islamabad"
        for loc in locations:
            if loc in text:
                selected_loc = loc.upper()
                break
        
        # Determine job complexity from keywords
        complex_keywords = ["pura", "full", "complete", "renovation", "installation", "install", "new"]
        intermediate_keywords = ["repair", "fix", "theek", "deep", "service", "leak", "tapak", "cool"]
        
        job_complexity = "basic"
        for kw in complex_keywords:
            if kw in text:
                job_complexity = "complex"
                break
        if job_complexity == "basic":
            for kw in intermediate_keywords:
                if kw in text:
                    job_complexity = "intermediate"
                    break

        # Confidence: fallback is inherently less certain
        confidence = 0.72 if selected_service[0] == "general" else 0.78

        return IntentResponse(
            service_type=selected_service[0],
            service_label=selected_service[1],
            location=selected_loc,
            time_raw="As soon as possible",
            time_normalized=datetime.now().isoformat(),
            urgency="urgent" if "urgent" in text or "emergency" in text or "fauri" in text else "normal",
            language_detected="detected_via_fallback",
            confidence=confidence,
            job_complexity=job_complexity
        )

    def _call_llm(self, prompt: str) -> IntentResponse:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        text_response = response.text.strip()
        print(f"DEBUG: Raw LLM response: '{text_response}'")

        # Strip markdown fences if present
        if text_response.startswith("```json"):
            text_response = text_response[7:]
        elif text_response.startswith("```"):
            text_response = text_response[3:]
        if text_response.endswith("```"):
            text_response = text_response[:-3]
        text_response = text_response.strip()

        try:
            parsed_json = json.loads(text_response)
            return IntentResponse(**parsed_json)
        except json.JSONDecodeError as e:
            logger.error(f"JSON Decode Error: {e}. Raw: {text_response}")
            raise ValueError(f"Failed to parse JSON: {e}")
        except ValidationError as e:
            logger.error(f"Validation Error: {e}")
            raise ValueError(f"JSON does not match schema: {e}")
