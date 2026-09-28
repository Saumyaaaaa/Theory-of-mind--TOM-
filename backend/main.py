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
from agent_a import analyze_learner_turn, CognitiveState
from bkt import (
    update_concept_mastery_map,
    partition_concepts,
    MASTERY_THRESHOLD,
)
from agent_b import generate_scaffolded_turn
from verifier import verify_reply

CONCEPTS_FILE = Path(__file__).parent / "concepts.json"

def load_concept_graph() -> dict:
    if not CONCEPTS_FILE.exists():
        raise FileNotFoundError(f"Missing ontology file: {CONCEPTS_FILE}")
    with open(CONCEPTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

concept_graph = load_concept_graph()

def get_initial_mastery() -> Dict[str, float]:
    """Initializes prior probability for all concepts in ontology to baseline prior (0.15)."""
    return {concept: 0.15 for concept in concept_graph.keys()}

def get_initial_cognitive_state() -> Dict[str, Any]:
    """Provides a valid starter cognitive state conforming to the schema."""
    return {
        "concept_being_probed": "variable",
        "observed_outcome": "partially_correct",
        "current_misconceptions": [],
        "frustration_level": 0.0,
        "suggested_scaffolding_strategy": "Welcome the learner warmly and introduce basic variables through an intuitive everyday container analogy.",
    }

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Learner-State Scaffolding Tutor API",
    description="Dual-Agent Socratic Tutoring System with Cognitive State Scaffolding and Mechanical Verification",
    version="0.9.0",
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

class VerificationMeta(BaseModel):
    attempts_count: int
    used_fallback: bool
    mastered_concepts: List[str]
    locked_concepts: List[str]

class ChatResponse(BaseModel):
    reply: str
    state: Dict[str, Any]
    mastery: Dict[str, float]
    verification: Optional[VerificationMeta] = None

class CounterfactualRequest(BaseModel):
    session_id: str
    modified_state: Optional[Dict[str, Any]] = None
    modified_mastery: Optional[Dict[str, float]] = None

@app.get("/")
def read_root():
    return {
        "message": "Learner-State Scaffolding Tutor API is running.",
        "phase": "Phase 9 - Counterfactual Engine & Full Suite",
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
    
    # Save seed welcome message and initial state snapshot
    welcome_text = "Hello! I'm your algebra tutor. What would you like to explore today, or shall we start with variables?"
    seed_msg_id = save_message(session_id, role="assistant", content=welcome_text)
    save_state_snapshot(session_id, seed_msg_id, init_state, init_mastery)
    
    return {
        "session_id": session_id,
        "reply": welcome_text,
        "state": init_state,
        "mastery": init_mastery,
    }

@app.post("/chat", response_model=ChatResponse)
def chat_turn(req: ChatRequest):
    """
    Phase 6 Real Pipeline (Strictly Sequential):
    1. Retrieve prior state & mastery snapshot from SQLite.
    2. Save user message to database.
    3. Agent A ('Modeler'): Diagnoses concept probed, outcome, misconceptions, frustration.
    4. Deterministic BKT Step: Updates mastery probability and derives mastered/locked lists.
    5. Agent B ('Interlocutor') + Verifier Loop: Drafts reply, checks against locked terms & answer leaks, retries if needed.
    6. Persist assistant reply & snapshot to SQLite.
    7. Return reply, state, mastery, and verification telemetry.
    """
    latest_snapshot = get_latest_snapshot(req.session_id)
    if not latest_snapshot:
        raise HTTPException(
            status_code=404,
            detail="Session not found. Please create a session via POST /session first.",
        )
    
    prev_state = latest_snapshot["state"]
    prev_mastery = latest_snapshot["mastery"]

    # 1. Save user message
    user_msg_id = save_message(req.session_id, role="user", content=req.message)

    # 2. Fetch conversation history for context
    history = get_messages(req.session_id)

    # 3. Agent A ('Modeler') - Hidden assessment
    try:
        agent_a_state: CognitiveState = analyze_learner_turn(
            user_message=req.message,
            conversation_history=history,
            previous_state=prev_state,
            concept_graph=concept_graph,
        )
        current_state = agent_a_state.model_dump()
    except Exception as e:
        print(f"[Chat] Agent A evaluation failed: {e}. Falling back to previous state.")
        current_state = prev_state

    # 4. Deterministic Python BKT Update Step (soft-evidence blend)
    probed_concept = current_state.get("concept_being_probed", "variable")
    observed_outcome = current_state.get("observed_outcome", "partially_correct")

    updated_mastery = update_concept_mastery_map(
        current_mastery_map=prev_mastery,
        concept_being_probed=probed_concept,
        observed_outcome=observed_outcome,
        threshold=MASTERY_THRESHOLD,
    )
    mastered_concepts, locked_concepts = partition_concepts(updated_mastery, concept_graph=concept_graph)

    # 5. Agent B ('Interlocutor') + Mechanical Verifier Loop
    reply_text, verifier_meta = generate_scaffolded_turn(
        user_message=req.message,
        conversation_history=history,
        cognitive_state=current_state,
        mastery_map=updated_mastery,
        concept_graph=concept_graph,
    )

    # 6. Save assistant response to SQLite
    assistant_msg_id = save_message(req.session_id, role="assistant", content=reply_text)

    # 7. Persist turn snapshot
    save_state_snapshot(
        session_id=req.session_id,
        message_id=assistant_msg_id,
        state=current_state,
        mastery=updated_mastery,
    )

    return {
        "reply": reply_text,
        "state": current_state,
        "mastery": updated_mastery,
        "verification": {
            "attempts_count": verifier_meta["attempts_count"],
            "used_fallback": verifier_meta["used_fallback"],
            "mastered_concepts": mastered_concepts,
            "locked_concepts": locked_concepts,
        },
    }

@app.post("/counterfactual")
def run_counterfactual(req: CounterfactualRequest):
    """
    Phase 9 Counterfactual Reasoning Endpoint:
    Re-runs Agent B ONLY on the last user message with a modified cognitive state.
    
    CRITICAL ARCHITECTURAL PROPERTY:
    Derives locked_concepts by feeding modified_mastery through the EXACT SAME
    partition_concepts function from bkt.py (threshold = 0.85).
    
    Does NOT persist any modified state to SQLite.
    Returns { real_reply, counterfactual_reply, modified_state, modified_mastery, verification }.
    """
    latest_snapshot = get_latest_snapshot(req.session_id)
    if not latest_snapshot:
        raise HTTPException(status_code=404, detail="Session not found.")

    messages = get_messages(req.session_id)
    if not messages:
        raise HTTPException(status_code=400, detail="No messages in this session.")

    # 1. Identify the last user message and the last assistant message (real_reply)
    last_user_msg = None
    real_reply = "No previous reply found."
    for m in reversed(messages):
        if m["role"] == "user" and last_user_msg is None:
            last_user_msg = m
        elif m["role"] == "assistant" and last_user_msg is not None:
            real_reply = m["content"]
            break

    if not last_user_msg:
        raise HTTPException(status_code=400, detail="No user message found to run counterfactual against.")

    # 2. Build the modified state and modified mastery map
    base_state = dict(latest_snapshot["state"])
    base_mastery = dict(latest_snapshot["mastery"])

    if req.modified_state:
        base_state.update(req.modified_state)
    if req.modified_mastery:
        base_mastery.update(req.modified_mastery)

    # 3. Derive locked_concepts using the EXACT SAME partition_concepts function with structural prerequisite gating
    mastered_concepts, locked_concepts = partition_concepts(
        base_mastery,
        concept_graph=concept_graph,
        threshold=MASTERY_THRESHOLD,
    )

    # 4. Filter history prior to the last user message to preserve conversational context
    history_before = [m for m in messages if m["created_at"] < last_user_msg["created_at"]]

    # 5. Re-run Agent B ONLY through the mechanical verifier loop
    cf_reply, cf_verifier_meta = generate_scaffolded_turn(
        user_message=last_user_msg["content"],
        conversation_history=history_before,
        cognitive_state=base_state,
        mastery_map=base_mastery,
        concept_graph=concept_graph,
    )

    # Return side-by-side results without SQLite mutation
    return {
        "session_id": req.session_id,
        "user_message": last_user_msg["content"],
        "real_reply": real_reply,
        "counterfactual_reply": cf_reply,
        "modified_state": base_state,
        "modified_mastery": base_mastery,
        "verification": {
            "attempts_count": cf_verifier_meta["attempts_count"],
            "used_fallback": cf_verifier_meta["used_fallback"],
            "mastered_concepts": mastered_concepts,
            "locked_concepts": locked_concepts,
        },
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
