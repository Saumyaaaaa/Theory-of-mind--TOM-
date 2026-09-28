import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel, Field

# Load environment variables from backend/.env if present
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

class Misconception(BaseModel):
    concept: str = Field(description="The concept name from the ontology that the misconception relates to")
    description: str = Field(description="Clear, concise description of the misconception observed")

class CognitiveState(BaseModel):
    concept_being_probed: str = Field(
        description="The concept from the ontology currently being probed or discussed"
    )
    observed_outcome: Literal["correct", "incorrect", "partially_correct"] = Field(
        description="Classification of the user's latest answer relative to the probed concept"
    )
    current_misconceptions: List[Misconception] = Field(
        default_factory=list,
        description="List of misconceptions detected in the user's thinking"
    )
    frustration_level: float = Field(
        ge=0.0,
        le=1.0,
        description="Estimated frustration/confusion level from 0.0 (calm/confident) to 1.0 (highly frustrated)"
    )
    suggested_scaffolding_strategy: str = Field(
        description="Actionable pedagogical scaffolding strategy for Agent B to guide the student without giving away answers"
    )

def build_system_instruction(concept_graph: Dict[str, Any]) -> str:
    concepts_list = ", ".join(concept_graph.keys())
    return f"""You are the hidden Cognitive Modeler (Agent A) in a dual-agent Socratic tutoring system.
You NEVER speak to the learner. Your sole job is to observe the interaction and output a strict cognitive state assessment.

DOMAIN CONCEPT ONTOLOGY:
You must strictly align probed concepts with this domain ontology:
Available concepts: {concepts_list}

Full ontology structure:
{json.dumps(concept_graph, indent=2)}

TASK:
Given:
1. The recent conversation history
2. The previous cognitive state
3. The learner's latest message

Perform these exact evaluations:
- concept_being_probed: Identify which concept from the ontology is being probed or addressed in this turn.
- observed_outcome: Classify the learner's understanding in their latest answer as 'correct', 'incorrect', or 'partially_correct'.
- current_misconceptions: If the learner exhibits confusion or a wrong premise, identify the concept and describe the misconception. If none, return an empty list [].
- frustration_level: Estimate a score between 0.0 and 1.0 reflecting how confused, uncertain, or frustrated the learner sounds.
- suggested_scaffolding_strategy: Provide a concise pedagogical hint for the user-facing tutor on how to guide the learner Socratically (e.g. asking a clarifying question, breaking down a formula, or referencing an earlier concept).
"""

def analyze_learner_turn(
    user_message: str,
    conversation_history: List[Dict[str, str]],
    previous_state: Optional[Dict[str, Any]],
    concept_graph: Dict[str, Any],
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    max_retries: int = 2,
) -> CognitiveState:
    """
    Invokes Agent A (Gemini Flash) with server-side structured output enforcement.
    Uses response_mime_type='application/json' and response_schema=CognitiveState.
    Includes API retry logic for transient network/server errors.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Please create a backend/.env file containing GEMINI_API_KEY=your_key."
        )

    # Initialize Google GenAI client explicitly with API key
    client = genai.Client(api_key=key)

    # Build context prompt
    history_formatted = "\n".join(
        [f"{m.get('role', 'user').capitalize()}: {m.get('content', '')}" for m in conversation_history[-6:]]
    )
    prev_state_formatted = json.dumps(previous_state, indent=2) if previous_state else "None (initial turn)"

    user_prompt = f"""[CONVERSATION HISTORY]
{history_formatted if history_formatted else "None yet."}

[PREVIOUS COGNITIVE STATE]
{prev_state_formatted}

[LATEST LEARNER MESSAGE]
"{user_message}"

Assess the learner's state now."""

    # Server-side structured output configuration
    config = types.GenerateContentConfig(
        system_instruction=build_system_instruction(concept_graph),
        response_mime_type="application/json",
        response_schema=CognitiveState,
        temperature=0.1,
    )

    last_error = None
    for attempt in range(1, max_retries + 2):
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_prompt,
                config=config,
            )

            if not response.text:
                raise ValueError("Gemini returned an empty response.")

            # Validate and parse directly into our Pydantic model
            parsed_state = CognitiveState.model_validate_json(response.text)
            return parsed_state

        except (APIError, Exception) as e:
            last_error = e
            if attempt <= max_retries:
                backoff = attempt * 2
                print(f"[Agent A] API call failed (attempt {attempt}/{max_retries + 1}): {e}. Retrying in {backoff}s...")
                time.sleep(backoff)
            else:
                break

    raise RuntimeError(f"Agent A failed after {max_retries + 1} attempts: {last_error}")
