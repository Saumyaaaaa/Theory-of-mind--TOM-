import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Learner-State Scaffolding Tutor API",
    description="Backend API for Socratic scaffolding tutor with cognitive state modeling",
    version="0.1.0",
)

# Enable CORS for local Next.js frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load concept graph at startup
CONCEPTS_FILE = Path(__file__).parent / "concepts.json"

def load_concept_graph() -> dict:
    if not CONCEPTS_FILE.exists():
        raise FileNotFoundError(f"Missing ontology file: {CONCEPTS_FILE}")
    with open(CONCEPTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

concept_graph = load_concept_graph()

@app.get("/")
def read_root():
    return {
        "message": "Learner-State Scaffolding Tutor API is running.",
        "phase": "Phase 1 - Project Scaffolding",
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
