from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import contextlib

from backend.database import engine
from backend import models
from backend.munsif.munsif_agent import MunsifAgent

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the SQLite tables
    models.Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Antigravity Agents API", lifespan=lifespan)

munsif_agent = MunsifAgent()

class UserInput(BaseModel):
    session_id: Optional[str] = None
    text: str

@app.post("/chat")
def chat(user_input: UserInput):
    session_id = user_input.session_id
    if not session_id:
        session_id = munsif_agent.create_session()
        
    response = munsif_agent.process_input(session_id, user_input.text)
    response["session_id"] = session_id
    return response

@app.get("/session/{session_id}")
def get_session(session_id: str):
    if session_id not in munsif_agent.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return munsif_agent.sessions[session_id]
