from fastapi import HTTPException
from typing import List, Optional, Dict, Any
import uuid
from backend.zuban.zuban_agent import ZubanAgent

class MunsifAgent:
    def __init__(self):
        self.zuban = ZubanAgent()
        # For now we use in-memory dictionary. 
        # Future: Use SQLite Session model from backend.models
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
        
        # 1. Call Zuban Agent
        session["workplan"].append({"agent": "Munsif", "action": "Calling Zuban", "status": "started"})
        intent_res = self.zuban.parse_input(raw_input)
        
        session["workplan"].append({
            "agent": "Zuban", 
            "action": "Parsed Intent", 
            "result": intent_res.model_dump()
        })
        session["context"]["intent"] = intent_res.model_dump()

        # Handle low confidence fallback
        if intent_res.confidence_score < 0.75:
            session["workplan"].append({"agent": "Munsif", "action": "Triggered fallback: Ask user", "reason": "Low confidence"})
            return {
                "message": intent_res.clarifying_question,
                "session_state": session
            }

        # Proceed to Khoji
        session["workplan"].append({"agent": "Munsif", "action": "Routing to Khoji", "status": "pending"})
        
        return {
            "message": "Intent understood. Proceeding to matching provider.",
            "session_state": session
        }
