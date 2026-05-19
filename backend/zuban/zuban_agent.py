import os
import json
import logging
from pathlib import Path
from pydantic import BaseModel, ValidationError
from datetime import datetime
from dotenv import load_dotenv

_env_file = Path(__file__).parent.parent / ".env"
load_dotenv(_env_file) if _env_file.exists() else None
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Zuban, a multilingual intent extraction agent for XIDMAT.AI, a Pakistani home service booking app.

Extract the user's service request and return ONLY valid JSON. No markdown. No explanation. No preamble.

SUPPORTED SERVICES: electrician, plumber, ac_technician, carpenter, painter, home_cleaner, mechanic, gas_technician, pest_control, tiler, welder

SERVICE MAPPING RULES (understand context, not just keywords):
- Any electrical work: wiring, DC wiring, bijli, bijli ka kaam, switch, socket, fan installation, circuit breaker, power issue, MCB, solar panel, inverter, UPS, generator, light, bulb, wiring repair → "electrician"
- Any water/piping issue: pipe, tap, leakage, leak, pani, pani ka masla, tanki, nala, motar, drain, toilet, bathroom, nahana, washroom, sewer, pipeline, geyser water connection → "plumber"
- Cooling: AC, air conditioner, AC kharab, thanda, cooling, refrigerator, fridge, AC gas, AC service, AC installation → "ac_technician"
- Wood work: furniture, wood ka kaam, daraza, almari, door repair, shelf, cabinet, chipboard → "carpenter"
- Paint: paint, rang, color, wall painting, whitewash, polish → "painter"
- Cleaning: cleaning, safai, deep clean, house cleaning, ghar ki safai → "home_cleaner"
- Vehicle: car repair, engine, mechanic, vehicle, car kharab → "mechanic"
- Gas: gas, gas ka masla, geyser gas, cylinder, stove, burner, gas leakage → "gas_technician"
- Pests: pest, cockroach, rat, spray, insects, machar, makhhi, termite → "pest_control"
- Tiles: tiles, flooring, marble, tiles ki kaam → "tiler"
- Metal: welding, iron work, gate repair, loha → "welder"

URGENCY MAPPING:
- urgently, emergency, fauri, abhi, right now, jaldi, foran → "urgent"
- kal, tomorrow, later, koi jaldi nahi → "normal"
- flexible, koi masla nahi, jab aap chahain → "flexible"

LOCATION: Extract the neighborhood/area name. Common Karachi areas: DHA, Gulshan, Clifton, PECHS, Nazimabad, Johar, Korangi, Saddar, Lyari, Malir, Landhi, F.B. Area, North Nazimabad, Bahadurabad, Burns Garden, Orangi, Buffer Zone, North Karachi, Water Pump, Boat Basin, Sea View, Zamzama, Tariq Road, Shah Faisal, Garden, Liaquatabad, Keamari, SITE. Default to "Karachi" if no location mentioned.

If the user's GPS coordinates are provided in parentheses at the end, use them to infer the area but still return the area name in the location field.

Examples:
Input: "Mujhe kal subah DHA mein plumber chahiye"
Output: {"service_type":"plumber","service_label":"Plumber","location":"DHA","time_raw":"kal subah","time_normalized":"2026-05-20T09:00:00","urgency":"normal","language_detected":"roman_urdu"}

Input: "AC kharab hai emergency!"
Output: {"service_type":"ac_technician","service_label":"AC Technician","location":"Karachi","time_raw":"emergency","time_normalized":"2026-05-19T10:00:00","urgency":"urgent","language_detected":"roman_urdu"}

Input: "bijli ka kaam hai gulshan mein"
Output: {"service_type":"electrician","service_label":"Electrician","location":"Gulshan","time_raw":"ASAP","time_normalized":"2026-05-19T10:00:00","urgency":"normal","language_detected":"roman_urdu"}

Input: "I need a painter in Clifton preferably tomorrow afternoon"
Output: {"service_type":"painter","service_label":"Painter","location":"Clifton","time_raw":"tomorrow afternoon","time_normalized":"2026-05-20T14:00:00","urgency":"normal","language_detected":"english"}
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
        from backend.llm_client import call_llm, call_llm_json
        self._call_llm = call_llm
        self._call_llm_json = call_llm_json

        api_key = os.getenv("GEMINI_API_KEY")
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key and not openrouter_key:
            raise EnvironmentError("GEMINI_API_KEY or OPENROUTER_API_KEY must be set.")

    def parse_input(self, text: str) -> IntentResponse:
        prompt = f"{SYSTEM_PROMPT}\n\nInput: \"{text}\"\nOutput:"

        parsed = self._call_llm_json(prompt)
        if parsed:
            try:
                return IntentResponse(**parsed)
            except ValidationError as e:
                logger.warning(f"LLM returned valid JSON but invalid schema: {e}")

        stricter_prompt = (
            prompt
            + "\nCRITICAL: YOU MUST RETURN ONLY A VALID JSON OBJECT AND NOTHING ELSE. "
              "DO NOT WRAP IN MARKDOWN BACKTICKS."
        )
        parsed = self._call_llm_json(stricter_prompt)
        if parsed:
            try:
                return IntentResponse(**parsed)
            except ValidationError as e:
                logger.warning(f"LLM retry returned invalid schema: {e}")

        logger.warning("All LLM providers failed. Using keyword-based fallback.")
        return self._fallback_parse(text)

    def _fallback_parse(self, text: str) -> IntentResponse:
        import re
        text_lower = text.lower()

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
            (r"\bclean", "home_cleaner", "Home Cleaner"),
            (r"\bsafai", "home_cleaner", "Home Cleaner"),
            (r"\bmechanic", "mechanic", "Mechanic"),
            (r"\bcar\b", "mechanic", "Mechanic"),
            (r"\bmistri", "carpenter", "Carpenter"),
            (r"\bcarpenter", "carpenter", "Carpenter"),
            (r"\bpaint", "painter", "Painter"),
            (r"\brang\b", "painter", "Painter"),
        ]

        selected_service = ("general", "General Service")
        for pattern, s_type, s_label in service_keywords:
            if re.search(pattern, text_lower):
                selected_service = (s_type, s_label)
                break

        locations = [
            "gulshan", "gulshan-e-iqbal", "dha", "clifton", "pechs",
            "nazimabad", "north nazimabad", "johar", "gulistan-e-johar",
            "korangi", "saddar", "lyari", "orangi", "malir", "landhi",
            "f.b. area", "federal b area", "bahadurabad", "burns garden",
            "defence", "keamari", "site", "shah faisal", "liaquatabad",
            "garden", "nursing", "bahadur", "boat basin", "sea view",
            "dioar", "jutland", "metrovil", "jameseband", "nazimabad",
            "bufferzone", "buffer zone", "north karachi", "sharifabad",
            "water pump", "ancholi", "numaish", "regal chowk", "tariq road",
            "zamzama", "do darya", "clifton block", "dha phase",
        ]
        selected_loc = "Karachi"
        for loc in locations:
            if loc in text_lower:
                selected_loc = loc.upper().replace("F.B. AREA", "F.B. Area").replace("FEDERAL B AREA", "F.B. Area").replace("DHA PHASE", "DHA").replace("GULSHAN-E-IQBAL", "Gulshan-e-Iqbal").replace("GULISTAN-E-JOHAR", "Gulistan-e-Johar").replace("BUFFER ZONE", "Buffer Zone").replace("NORTH KARACHI", "North Karachi").replace("NORTH NAZIMABAD", "North Nazimabad").replace("WATER PUMP", "Water Pump").replace("SEA VIEW", "Sea View").replace("BOAT BASIN", "Boat Basin").replace("TARIQ ROAD", "Tariq Road").replace("ZAMZAMA", "Zamzama")
                break

        return IntentResponse(
            service_type=selected_service[0],
            service_label=selected_service[1],
            location=selected_loc,
            time_raw="As soon as possible",
            time_normalized=datetime.now().isoformat(),
            urgency="urgent" if any(w in text_lower for w in ["urgent", "emergency", "fauri", "abhi", "jaldi", "foran"]) else "normal",
            language_detected="detected_via_fallback"
        )