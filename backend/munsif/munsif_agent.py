from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend import models
import uuid
import json
from typing import Dict, Any, Optional
class MunsifAgent:
    def __init__(self):
        pass

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
        
        # In pure ADK mode, process_input shouldn't be used to call Zuban directly.
        # This function is kept for backward compatibility if needed.
        self.add_workplan_step(session_id, "Munsif", "Processing input (delegated to ADK)")
        
        return {
            "message": "Input received",
            "session_state": self.get_session(session_id)
        }
        

