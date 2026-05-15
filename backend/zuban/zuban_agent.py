import os
import json
import logging
from pydantic import BaseModel, ValidationError
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Zuban, a multilingual intent extraction agent for a Pakistani service booking app.
Extract service requests from Roman Urdu, Urdu, or English text.
Return ONLY valid JSON. No preamble. No markdown. No explanation.

Examples:
Input: "Mujhe kal subah DHA mein plumber chahiye"
Output: {"service_type":"plumber","service_label":"Plumber","location":"DHA","time_raw":"kal subah","time_normalized":"2026-05-22T09:00:00","urgency":"normal","language_detected":"roman_urdu"}

Input: "urgent electrician needed in Gulshan right now"
Output: {"service_type":"electrician","service_label":"Electrician","location":"Gulshan","time_raw":"right now","time_normalized":"2026-05-21T10:00:00","urgency":"urgent","language_detected":"english"}

Input: "AC theek karwana hai Clifton mein, parso"
Output: {"service_type":"ac_technician","service_label":"AC Technician","location":"Clifton","time_raw":"parso","time_normalized":"2026-05-23T10:00:00","urgency":"normal","language_detected":"roman_urdu"}
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
        self.model = "gemini-2.5-flash"

    def parse_input(self, text: str) -> IntentResponse:
        prompt = f"{SYSTEM_PROMPT}\n\nInput: \"{text}\"\nOutput:"

        try:
            return self._call_llm(prompt)
        except Exception as e:
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
                raise ValueError("Dobara likhein — request samajh nahi aayi.")

    def _call_llm(self, prompt: str) -> IntentResponse:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        text_response = response.text.strip()

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
            raise ValueError(f"Failed to parse JSON: {e}")
        except ValidationError as e:
            raise ValueError(f"JSON does not match schema: {e}")
