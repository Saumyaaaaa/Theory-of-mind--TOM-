import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from agent_a import analyze_learner_turn
from main import load_concept_graph

def test_name_dropping_classified_as_incorrect():
    concept_graph = load_concept_graph()

    # Learner merely names a formula without demonstrating reasoning or applying it:
    name_dropping_msg = "I know slope-intercept form! Can we use the y=mx+b equation here?"

    print("=" * 65)
    print("TESTING AGENT A GRADING STRICTNESS ON MERE NAME-DROPPING")
    print(f"Student: \"{name_dropping_msg}\"")
    print("=" * 65)

    result = analyze_learner_turn(
        user_message=name_dropping_msg,
        conversation_history=[
            {"role": "assistant", "content": "Let's explore how the line behaves. How should we start?"}
        ],
        previous_state={
            "concept_being_probed": "slope_intercept_form",
            "observed_outcome": "partially_correct",
            "current_misconceptions": [],
            "frustration_level": 0.1,
            "suggested_scaffolding_strategy": "Ask learner to identify equation parts."
        },
        concept_graph=concept_graph,
    )

    print("\nAGENT A EVALUATION:")
    print(f"  Probed Concept:   {result.concept_being_probed}")
    print(f"  Observed Outcome: {result.observed_outcome}")
    print(f"  Misconceptions:   {result.current_misconceptions}")
    print(f"  Strategy:         {result.suggested_scaffolding_strategy}")

    assert result.observed_outcome == "incorrect", (
        f"Expected 'incorrect' for mere name-dropping, but got '{result.observed_outcome}'!"
    )
    print("\nTEST PASSED: Mere formula name-dropping was correctly classified as 'incorrect' (no free mastery credit).")

if __name__ == "__main__":
    test_name_dropping_classified_as_incorrect()
