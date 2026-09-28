import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import (
    init_db,
    create_session,
    save_message,
    save_state_snapshot,
    get_latest_snapshot,
    get_snapshot_history,
    get_messages,
)

# Load concept graph at startup
CONCEPTS_FILE = Path(__file__).parent / "concepts.json"

def load_concept_graph() -> dict:
    if not CONCEPTS_FILE.exists():
        raise FileNotFoundError(f"Missing ontology file: {CONCEPTS_FILE}")
    with open(CONCEPTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

concept_graph = load_concept_graph()

def get_initial_mastery() -> Dict[str, float]:
    """Initializes mastery probability for all concepts in ontology to a baseline prior (0.15)."""
    return {concept: 0.15 for concept in concept_graph.keys()}

def get_initial_cognitive_state() -> Dict[str, Any]:
    """Provides a valid starter cognitive state conforming to the schema."""
    return {
        "concept_being_probed": "variable",
        "observed_outcome": "none",
        "current_misconceptions": [],
        "frustration_level": 0.0,
        "suggested_scaffolding_strategy": "Welcome the learner and probe their understanding of basic variables.",
    }

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite tables on startup
    init_db()
    yield

app = FastAPI(
    title="Learner-State Scaffolding Tutor API",
    description="Backend API for Socratic scaffolding tutor with cognitive state modeling",
    version="0.2.0",
    lifespan=lifespan,
)

# Enable CORS for local Next.js frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    reply: str
    state: Dict[str, Any]
    mastery: Dict[str, float]

@app.get("/")
def read_root():
    return {
        "message": "Learner-State Scaffolding Tutor API is running.",
        "phase": "Phase 2 - SQLite & Session / Chat Stubs",
    }

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "loaded_concepts_count": len(concept_graph),
    }

@app.get("/concept-graph")
def get_concept_graph():
    return concept_graph

@app.post("/session")
def new_session():
    """Creates a new tutoring session and seeds its initial cognitive state & mastery snapshot."""
    session_id = create_session()
    init_state = get_initial_cognitive_state()
    init_mastery = get_initial_mastery()
    
    # Save a system seed message and the initial state snapshot
    seed_msg_id = save_message(session_id, role="system", content="Session initialized.")
    save_state_snapshot(session_id, seed_msg_id, init_state, init_mastery)
    
    return {
        "session_id": session_id,
        "state": init_state,
        "mastery": init_mastery,
    }

@app.post("/chat", response_model=ChatResponse)
def chat_turn(req: ChatRequest):
    """
    Phase 2 stub:
    - Stores the incoming user message
    - Generates a stub echo reply
    - Stores the assistant message
    - Stores a state snapshot linked to this turn
    - Returns { reply, state, mastery }
    """
    latest_snapshot = get_latest_snapshot(req.session_id)
    if not latest_snapshot:
        raise HTTPException(status_code=404, detail="Session not found. Please create a session via POST /session first.")
    
    # 1. Save user message to SQLite
    user_msg_id = save_message(req.session_id, role="user", content=req.message)
    
    # 2. Stub reply (echo for Phase 2)
    reply_text = f"Echo: {req.message}"
    
    # 3. Save assistant message to SQLite
    assistant_msg_id = save_message(req.session_id, role="assistant", content=reply_text)
    
    # 4. In Phase 2 stub, we carry over the state and mastery (real Agent A + BKT in later phases)
    current_state = latest_snapshot["state"]
    current_mastery = latest_snapshot["mastery"]
    
    # 5. Save state snapshot linked to this assistant turn
    save_state_snapshot(
        session_id=req.session_id,
        message_id=assistant_msg_id,
        state=current_state,
        mastery=current_mastery,
    )
    
    return {
        "reply": reply_text,
        "state": current_state,
        "mastery": current_mastery,
    }

@app.get("/state/{session_id}")
def get_session_state(session_id: str):
    """Returns the latest state and mastery snapshot for a given session."""
    snapshot = get_latest_snapshot(session_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Session not found.")
    return snapshot

@app.get("/state/{session_id}/history")
def get_session_history(session_id: str):
    """Returns all state snapshots for this session in chronological order (for debug timeline)."""
    history = get_snapshot_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {
        "session_id": session_id,
        "snapshots_count": len(history),
        "history": history,
    }

@app.get("/messages/{session_id}")
def get_session_messages(session_id: str):
    """Returns all conversation messages for a session."""
    messages = get_messages(session_id)
    return {
        "session_id": session_id,
        "messages": messages,
    }
