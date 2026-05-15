from fastapi import HTTPException
from typing import Dict, Any
import uuid
from backend.zuban.zuban_agent import ZubanAgent

class MunsifAgent:
    def __init__(self):
        self.zuban = ZubanAgent()
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "session_id": session_id,
            "status": "active",
            "workplan": [],
            "context": {}
        }
        return session_id

    def process_input(self, session_id: str, raw_input: str) -> Dict[str, Any]:
        if session_id not in self.sessions:
            raise HTTPException(status_code=404, detail="Session not found")

        session = self.sessions[session_id]

        # Step 1: Call Zuban to parse intent
        session["workplan"].append({"agent": "Munsif", "action": "Calling Zuban", "status": "started"})
        try:
            intent_res = self.zuban.parse_input(raw_input)
        except ValueError as e:
            # Zuban returned the user-facing error after 2 retries
            session["workplan"].append({"agent": "Zuban", "action": "Failed to parse intent", "error": str(e)})
            session["status"] = "failed"
            return {
                "message": str(e),  # "Dobara likhein — request samajh nahi aayi."
                "session_state": session
            }

        session["workplan"].append({
            "agent": "Zuban",
            "action": "Parsed Intent",
            "result": intent_res.model_dump()
        })
        session["context"]["intent"] = intent_res.model_dump()

        # Step 2: Route to Khoji with extracted fields
        session["workplan"].append({
            "agent": "Munsif",
            "action": "Routing to Khoji",
            "service_type": intent_res.service_type,
            "location": intent_res.location,
            "urgency": intent_res.urgency,
            "status": "pending"
        })

        return {
            "message": f"Samajh gaya! '{intent_res.service_label}' ki talash {intent_res.location} mein ho rahi hai.",
            "intent": intent_res.model_dump(),
            "next_step": "khoji_search",
            "session_state": session
        }
