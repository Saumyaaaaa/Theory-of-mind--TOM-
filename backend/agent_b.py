import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv
from google import genai
from google.genai import types

from bkt import partition_concepts
from verifier import verify_reply, get_fallback_scaffolding_reply, VerificationResult

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-3.5-flash-lite"]

def build_agent_b_system_prompt(
    mastered_concepts: List[str],
    locked_concepts: List[str],
    concept_being_probed: str,
    observed_outcome: str,
    misconceptions: List[Dict[str, str]],
    scaffolding_strategy: str,
    frustration_level: float = 0.0,
) -> str:
    """
    Dynamically constructs Agent B's system prompt strictly adhering to
    the current cognitive state constraints and pedagogical discipline.
    """
    mastered_str = ", ".join(mastered_concepts) if mastered_concepts else "None yet (beginner)"
    locked_str = ", ".join(locked_concepts) if locked_concepts else "None"
    
    misconception_descriptions = []
    for m in misconceptions:
        if isinstance(m, dict):
            misconception_descriptions.append(f"- {m.get('concept', '')}: {m.get('description', '')}")
        elif hasattr(m, "description"):
            misconception_descriptions.append(f"- {getattr(m, 'concept', '')}: {getattr(m, 'description', '')}")
    misconceptions_text = "\n".join(misconception_descriptions) if misconception_descriptions else "None detected."

    return f"""You are the Socratic Interlocutor (Agent B), the user-facing math tutor.
Your mission is to guide the student toward understanding using gentle, disciplined Socratic questioning.

CURRENT LEARNER COGNITIVE MODEL:
- Current Concept Being Probed: {concept_being_probed}
- Observed Outcome on Latest Turn: {observed_outcome.upper()}
- Frustration Level: {frustration_level:.2f}
- Mastered Concepts (Safe to reference & assume): {mastered_str}
- Misconceptions Currently Diagnosed:
{misconceptions_text}
- Recommended Pedagogical Scaffolding Strategy:
{scaffolding_strategy}

STRICT CONSTRAINTS (MANDATORY ENFORCEMENT):
1. FORBIDDEN LOCKED TERMS:
   The student has NOT yet mastered the following concepts. You MUST NOT mention, define, or name any of these terms or their synonyms:
   [{locked_str}]
   If you mention any of these forbidden words, an external Python verifier will reject your response.

2. NEVER SOLVE OR LEAK THE FINAL ANSWER:
   Never state the final numeric or symbolic answer (e.g. do NOT say "the answer is...", "x = 4", etc.).
   Even if the student is struggling or asks for the answer, respond ONLY with a guiding question or partial breakdown that encourages them to take the next cognitive step.

3. NEVER CONFIRM OR VERIFY PROPOSED VALUES (NO CONFIRMATION LOOPHOLE):
   Never confirm, verify, or restate a specific numeric or symbolic value the student proposes, even indirectly or via a different label for the same quantity (e.g. 'the coefficient' vs 'the slope'), while the relevant concept remains locked. If asked to confirm a value, respond only with a redirecting question — do not acknowledge whether the proposed value is correct or incorrect in any form.

4. NO GUESSING UNDER PRESSURE / EMPATHY WITHOUT GIVING GROUND:
   Never tell the student to guess, 'go with your gut/intuition,' or submit an answer without reasoning through it, regardless of stated time pressure. Under high frustration_level ({frustration_level:.2f}), be warmer and more empathetic in tone, but do not relax the no-confirmation and no-guessing rules — acknowledge the stress explicitly instead of resolving it by giving ground.

5. NO FALSE AFFIRMATION ON INCORRECT / PARTIALLY CORRECT TURNS:
   The student's answer was evaluated as: '{observed_outcome.upper()}'.
   When the outcome is 'incorrect' or 'partially_correct', NEVER use false praise or affirming language ('good thought', 'nice try', 'great thinking', 'you are on the right track', 'almost') toward the substance of the answer.
   Praising a wrong answer confuses the student into believing incorrect reasoning is sound.
   You may acknowledge their input completely neutrally (e.g., "I see you're looking at that number at the end.", "Let's examine how each number behaves in this equation.", "Let's take a look at what each part does.") or go directly to the guiding question.
   ONLY affirm the content ('Spot on!', 'Exactly right!') when the outcome is 'correct'.

6. SOCRATIC POSTURE & NOTATION:
   Keep your response concise (1 to 3 sentences maximum).
   Warm, conversational, and direct.
   End with ONE targeted guiding question that directly enacts the scaffolding strategy.
   PLAIN CONVERSATIONAL NOTATION: Do NOT wrap variables, numbers, or expressions in LaTeX dollar signs (e.g., do NOT write "$x$" or "$n$"). Write them naturally as plain letters and expressions (e.g., x or n or x + 6) so the dialogue reads naturally without confusing math symbols.
"""

def draft_agent_b_response(
    client: genai.Client,
    model: str,
    system_instruction: str,
    user_message: str,
    conversation_history: List[Dict[str, str]],
    correction_instruction: Optional[str] = None,
) -> str:
    """Calls Gemini Flash to generate a single draft reply for Agent B."""
    history_lines = []
    for m in conversation_history[-6:]:
        role = "Student" if m.get("role") == "user" else "Tutor"
        history_lines.append(f"{role}: {m.get('content', '')}")
    history_formatted = "\n".join(history_lines) if history_lines else "None yet."

    prompt_parts = [
        f"[RECENT CONVERSATION]\n{history_formatted}",
        f"\n[LATEST STUDENT MESSAGE]\n\"{user_message}\"",
    ]
    if correction_instruction:
        prompt_parts.append(
            f"\n[CORRECTION REQUIRED ON PREVIOUS DRAFT]\n{correction_instruction}"
        )
    prompt_parts.append("\nRespond to the student now following all constraints:")

    full_prompt = "\n".join(prompt_parts)

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.2,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    models_to_try = [model] + [m for m in FALLBACK_MODELS if m != model]
    last_err = None

    for candidate in models_to_try:
        try:
            response = client.models.generate_content(
                model=candidate,
                contents=full_prompt,
                config=config,
            )
            if response.text and response.text.strip():
                return response.text.strip()
        except Exception as e:
            last_err = e
            time.sleep(2)
            continue

    raise RuntimeError(f"Agent B failed across models {models_to_try}: {last_err}")

def generate_scaffolded_turn(
    user_message: str,
    conversation_history: List[Dict[str, str]],
    cognitive_state: Dict[str, Any],
    mastery_map: Dict[str, float],
    concept_graph: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    max_verifier_retries: int = 2,
) -> Tuple[str, Dict[str, Any]]:
    """
    Executes Agent B within the mechanical Python Verifier loop:
    1. Derives mastered and locked concepts using structural prerequisite gating.
    2. Dynamically constructs the system prompt with anti-sycophancy instructions.
    3. Drafts a response with Gemini Flash.
    4. Runs Python Verifier to check for locked terms and answer leaks.
    5. If verified: returns response immediately.
    6. If rejected: feeds explicit correction back to Agent B (up to max_verifier_retries).
    7. If retries exhausted: returns safe deterministic fallback Socratic question.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=key)

    mastered_concepts, locked_concepts = partition_concepts(mastery_map, concept_graph=concept_graph)
    concept_being_probed = cognitive_state.get("concept_being_probed", "variable")
    observed_outcome = cognitive_state.get("observed_outcome", "partially_correct")
    misconceptions = cognitive_state.get("current_misconceptions", [])
    scaffolding_strategy = cognitive_state.get(
        "suggested_scaffolding_strategy", "Guide the student with a clarifying question."
    )
    frustration_level = float(cognitive_state.get("frustration_level", 0.0))

    system_instruction = build_agent_b_system_prompt(
        mastered_concepts=mastered_concepts,
        locked_concepts=locked_concepts,
        concept_being_probed=concept_being_probed,
        observed_outcome=observed_outcome,
        misconceptions=misconceptions,
        scaffolding_strategy=scaffolding_strategy,
        frustration_level=frustration_level,
    )

    correction_note: Optional[str] = None
    verification_log = []

    for attempt in range(1, max_verifier_retries + 2):
        draft = draft_agent_b_response(
            client=client,
            model=model,
            system_instruction=system_instruction,
            user_message=user_message,
            conversation_history=conversation_history,
            correction_instruction=correction_note,
        )

        # Run lexical verifier
        v_result: VerificationResult = verify_reply(draft, locked_concepts)
        
        attempt_record = {
            "attempt": attempt,
            "draft": draft,
            "is_valid": v_result.is_valid,
            "leaked_concepts": v_result.leaked_concepts,
            "leaked_terms": v_result.leaked_terms,
            "answer_leak": v_result.answer_leak_detected,
        }
        verification_log.append(attempt_record)

        if v_result.is_valid:
            # Passed verification!
            return draft, {
                "attempts_count": attempt,
                "used_fallback": False,
                "verification_log": verification_log,
                "mastered_concepts": mastered_concepts,
                "locked_concepts": locked_concepts,
            }

        # Verification failed — construct specific correction instructions
        print(f"[Verifier] Draft {attempt} REJECTED! Leaked: {v_result.leaked_terms}")
        leak_msg = []
        if v_result.leaked_concepts:
            leak_msg.append(
                f"You used forbidden locked terms: {v_result.leaked_terms}. "
                f"The learner has not mastered {v_result.leaked_concepts}. Do NOT use these terms or their aliases."
            )
        if v_result.answer_leak_detected:
            leak_msg.append(
                "You leaked the direct final answer. State NO direct answers. Ask a guiding question only."
            )
        correction_note = " ".join(leak_msg)

    # All retries exhausted — trigger safe fallback
    print(f"[Verifier] Max retries exhausted ({max_verifier_retries}). Triggering safe fallback template.")
    fallback_reply = get_fallback_scaffolding_reply(concept_being_probed, scaffolding_strategy)
    return fallback_reply, {
        "attempts_count": max_verifier_retries + 1,
        "used_fallback": True,
        "verification_log": verification_log,
        "mastered_concepts": mastered_concepts,
        "locked_concepts": locked_concepts,
    }
