from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend import models
from backend.zuban.zuban_agent import ZubanAgent
from typing import Dict, Any, Optional
import uuid
import json

class MunsifAgent:
    def __init__(self):
        self.zuban = ZubanAgent()

    def _get_db_session(self):
        return SessionLocal()

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        db = self._get_db_session()
        try:
            db_session = models.Session(
                id=session_id,
                status="active",
                workplan=[],
                context={}
            )
            db.add(db_session)
            db.commit()
        finally:
            db.close()
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        db = self._get_db_session()
        try:
            db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
            if not db_session:
                return None
            return {
                "session_id": db_session.id,
                "status": db_session.status,
                "workplan": db_session.workplan,
                "context": db_session.context
            }
        finally:
            db.close()

    def add_workplan_step(self, session_id: str, agent: str, action: str, result: Any = None, error: str = None):
        db = self._get_db_session()
        try:
            db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
            if db_session:
                # SQLAlchemy JSON mutation detection needs care. Re-assigning works.
                current_workplan = list(db_session.workplan)
                step = {"agent": agent, "action": action}
                if result: step["result"] = result
                if error: step["error"] = error
                current_workplan.append(step)
                db_session.workplan = current_workplan
                db.commit()
        finally:
            db.close()

    def process_input(self, session_id: str, raw_input: str) -> Dict[str, Any]:
        session_data = self.get_session(session_id)
        if not session_data:
            raise ValueError("Session not found")

        # Step 1: Call Zuban to parse intent
        self.add_workplan_step(session_id, "Munsif", "Calling Zuban (NLP Agent)")
        
        try:
            intent_res = self.zuban.parse_input(raw_input)
        except ValueError as e:
            self.add_workplan_step(session_id, "Zuban", "Failed to parse intent", error=str(e))
            return {
                "message": str(e),
                "session_state": self.get_session(session_id)
            }

        intent_data = intent_res.model_dump()
        self.add_workplan_step(session_id, "Zuban", f"Intent Parsed: {intent_res.service_label}", result=intent_data)
        
        # Update context in DB
        db = self._get_db_session()
        try:
            db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
            if db_session:
                db_session.context = {"intent": intent_data}
                db.commit()
        finally:
            db.close()

        # Step 2: Route to Khoji
        self.add_workplan_step(session_id, "Munsif", f"Routing to Khoji for {intent_res.service_label} search in {intent_res.location}")

        return {
            "message": f"Samajh gaya! '{intent_res.service_label}' ki talash {intent_res.location} mein ho rahi hai.",
            "intent": intent_data,
            "next_step": "khoji_search",
            "session_state": self.get_session(session_id)
        }
