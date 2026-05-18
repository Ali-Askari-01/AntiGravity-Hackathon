import os
import json
import logging
from pathlib import Path
from pydantic import BaseModel, ValidationError
from google import genai
from dotenv import load_dotenv
from datetime import datetime

# Load .env from backend directory
load_dotenv(Path(__file__).parent.parent / ".env")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Zuban, a multilingual intent extraction agent for a Pakistani service booking app.
Extract service requests from Roman Urdu, Urdu, or English text.
Return ONLY valid JSON. No preamble. No markdown. No explanation.

SUPPORTED SERVICES: electrician, plumber, ac_technician, carpenter, painter, cleaner, mechanic, gas_technician, pest_control, home_cleaner, tiler, welder

MAPPING RULES - Understand the SERVICE NEEDED from context:
- wiring, DC wiring, electrical work, bijli ka kaam, switch, socket, fan installation, circuit, power issue, solar panel, inverter, UPS -> electrician
- pipe, tap, leakage, leak, water, pani, tanki, nala, motar, drain, toilet, bathroom, nahana, washroom, sewer, pipeline -> plumber
- AC, air conditioner, cooling, thanda, refrigerator, fridge -> ac_technician
- furniture, wood, daraza, almari, door repair, shelf, cabinet -> carpenter
- paint, rang, color, wall painting, whitewash -> painter
- cleaning, safai, deep clean, house cleaning -> home_cleaner
- car repair, engine, mechanic, vehicle -> mechanic
- gas, geyser, cylinder, stove, burner -> gas_technician
- pest, cockroach, rat, spray, insects -> pest_control
- tiles, flooring, marble -> tiler
- welding, iron work, gate repair -> welder

Examples:
Input: "Mujhe kal subah DHA mein plumber chahiye"
Output: {"service_type":"plumber","service_label":"Plumber","location":"DHA","time_raw":"kal subah","time_normalized":"2026-05-22T09:00:00","urgency":"normal","language_detected":"roman_urdu"}

Input: "urgent electrician needed in Gulshan right now"
Output: {"service_type":"electrician","service_label":"Electrician","location":"Gulshan","time_raw":"right now","time_normalized":"2026-05-21T10:00:00","urgency":"urgent","language_detected":"english"}

Input: "I want to do DC wiring in my house Gulshan e Iqbal on urgent basis"
Output: {"service_type":"electrician","service_label":"Electrician","location":"Gulshan e Iqbal","time_raw":"urgent basis","time_normalized":"2026-05-21T10:00:00","urgency":"urgent","language_detected":"english"}

Input: "Mere ghar ki wiring kharab hai, electrician chahiye"
Output: {"service_type":"electrician","service_label":"Electrician","location":"Karachi","time_raw":"ASAP","time_normalized":"2026-05-21T10:00:00","urgency":"urgent","language_detected":"roman_urdu"}

Input: "mere ghar ki pani ki tanki mai se pani leak ho raha hai pipe mai se tu mujhay nazimabad mai urgent basis per provider chahiye"
Output: {"service_type":"plumber","service_label":"Plumber","location":"Nazimabad","time_raw":"urgent basis","time_normalized":"2026-05-21T10:00:00","urgency":"urgent","language_detected":"roman_urdu"}

Input: "bathroom ka nala toot gaya hai, plumber bhejo"
Output: {"service_type":"plumber","service_label":"Plumber","location":"Karachi","time_raw":"ASAP","time_normalized":"2026-05-21T10:00:00","urgency":"urgent","language_detected":"roman_urdu"}
"""

class IntentResponse(BaseModel):
    service_type: str
    service_label: str
    location: str
    time_raw: str
    time_normalized: str
    urgency: str
    language_detected: str

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
            (r"\bwiring", "electrician", "Electrician"),
            (r"\bwire", "electrician", "Electrician"),
            (r"\belectrical", "electrician", "Electrician"),
            (r"\bsocket", "electrician", "Electrician"),
            (r"\bswitch", "electrician", "Electrician"),
            (r"\bsolar", "electrician", "Electrician"),
            (r"\binverter", "electrician", "Electrician"),
            (r"\bups\b", "electrician", "Electrician"),
            (r"\bpani\b", "plumber", "Plumber"),
            (r"\btanki", "plumber", "Plumber"),
            (r"\bleak", "plumber", "Plumber"),
            (r"\bpipe", "plumber", "Plumber"),
            (r"\bnala", "plumber", "Plumber"),
            (r"\btoilet", "plumber", "Plumber"),
            (r"\bbathroom", "plumber", "Plumber"),
            (r"\bdrain", "plumber", "Plumber"),
            (r"\bwater", "plumber", "Plumber"),
            (r"\bmotor\b", "plumber", "Plumber"),
            (r"\bsewer", "plumber", "Plumber"),
            (r"\bnahana", "plumber", "Plumber"),
            (r"\bwashroom", "plumber", "Plumber"),
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
        locations = ["gulshan", "dha", "clifton", "pechs", "nazimabad", "johar", "korangi", "saddar", "lyari", "orangi", "malir", "landhi", "f.b. area", "federal"]
        selected_loc = "Karachi"
        for loc in locations:
            if loc in text:
                selected_loc = loc.upper()
                break
        
        return IntentResponse(
            service_type=selected_service[0],
            service_label=selected_service[1],
            location=selected_loc,
            time_raw="As soon as possible",
            time_normalized=datetime.now().isoformat(),
            urgency="urgent" if "urgent" in text or "emergency" in text or "fauri" in text else "normal",
            language_detected="detected_via_fallback"
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
