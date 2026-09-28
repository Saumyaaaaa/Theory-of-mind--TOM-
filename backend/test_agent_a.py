import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend root is on Python module path
BACKEND_DIR = Path(__file__).parent
sys.path.insert(0, str(BACKEND_DIR))

# Load .env
load_dotenv(BACKEND_DIR / ".env")

from agent_a import analyze_learner_turn, CognitiveState

CONCEPTS_FILE = BACKEND_DIR / "concepts.json"

def load_concept_graph() -> dict:
    with open(CONCEPTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def run_tests():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("\n" + "!" * 70)
        print("ERROR: GEMINI_API_KEY is not set.")
        print(f"Please create a file at: {(BACKEND_DIR / '.env').resolve()}")
        print("and add your Gemini API key (free tier Flash):")
        print("    GEMINI_API_KEY=your_actual_key_here")
        print("!" * 70 + "\n")
        sys.exit(1)

    concept_graph = load_concept_graph()
    print("=" * 70)
    print("PHASE 3: TESTING AGENT A ('MODELER') WITH SERVER-SIDE STRUCTURED OUTPUT")
    print(f"Loaded {len(concept_graph)} concepts from ontology.")
    print("Model: Gemini Flash via google-genai SDK")
    print("=" * 70)

    test_cases = [
        {
            "name": "Test Case 1: Clear Misconception (Slope vs Y-Intercept)",
            "message": "In the equation y = 3x + 5, the slope is 5 because it's the number at the end.",
            "history": [
                {"role": "assistant", "content": "Let's look at y = 3x + 5. Can you identify the slope?"}
            ],
            "prev_state": {
                "concept_being_probed": "slope",
                "observed_outcome": "none",
                "current_misconceptions": [],
                "frustration_level": 0.1,
                "suggested_scaffolding_strategy": "Ask the learner to identify the slope in slope-intercept form."
            }
        },
        {
            "name": "Test Case 2: Partially Correct Understanding",
            "message": "The slope is 3 because it multiplies x, but I'm completely lost on what 5 is doing there.",
            "history": [
                {"role": "assistant", "content": "Can you tell me what the 3 and 5 represent in y = 3x + 5?"}
            ],
            "prev_state": {
                "concept_being_probed": "slope",
                "observed_outcome": "incorrect",
                "current_misconceptions": [{"concept": "slope", "description": "confused slope with intercept"}],
                "frustration_level": 0.4,
                "suggested_scaffolding_strategy": "Reinforce that 3 is the slope, then scaffold y-intercept."
            }
        },
        {
            "name": "Test Case 3: Accurate Answer Demonstrating Mastery",
            "message": "Slope is rise over run, which is change in y divided by change in x, so for every 1 step right on x, y goes up by 3.",
            "history": [
                {"role": "assistant", "content": "How would you explain what a slope of 3 actually means graphically?"}
            ],
            "prev_state": {
                "concept_being_probed": "slope",
                "observed_outcome": "partially_correct",
                "current_misconceptions": [],
                "frustration_level": 0.2,
                "suggested_scaffolding_strategy": "Prompt learner to explain graphical meaning of slope."
            }
        }
    ]

    for idx, tc in enumerate(test_cases, 1):
        print(f"\n--- {tc['name']} ---")
        print(f"Learner Message: \"{tc['message']}\"")
        try:
            state: CognitiveState = analyze_learner_turn(
                user_message=tc["message"],
                conversation_history=tc["history"],
                previous_state=tc["prev_state"],
                concept_graph=concept_graph,
            )

            print("\n[AGENT A STRUCTURED JSON OUTPUT]")
            json_output = state.model_dump_json(indent=2)
            print(json_output)

            # Assertions to verify schema compliance
            assert state.concept_being_probed in concept_graph, f"Unknown concept: {state.concept_being_probed}"
            assert state.observed_outcome in ["correct", "incorrect", "partially_correct"], f"Invalid outcome: {state.observed_outcome}"
            assert 0.0 <= state.frustration_level <= 1.0, f"Frustration level out of bounds: {state.frustration_level}"
            assert isinstance(state.suggested_scaffolding_strategy, str) and len(state.suggested_scaffolding_strategy) > 0

            print(f"✓ Schema validation passed: Probed='{state.concept_being_probed}', Outcome='{state.observed_outcome}', Frustration={state.frustration_level}")

        except Exception as e:
            print(f"✗ Test failed with error: {e}")
            sys.exit(1)

    print("\n" + "=" * 70)
    print("ALL 3 AGENT A TEST CASES PASSED SUCCESSFULLY!")
    print("Server-side structured JSON schema enforcement confirmed.")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
