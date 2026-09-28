import os
import time
from typing import Dict, List
from google import genai
from google.genai import types

PERSONA_SPECS = {
    "persistent_misconceiver": {
        "name": "Persistent Misconceiver",
        "description": "Firmly believes slope is the constant term at the end of a linear equation (e.g. 7 in y=2x+7).",
        "system_instruction": """You are a student learning linear equations in a tutoring session.
You have a specific, persistent false belief: You believe the slope is ALWAYS the constant number added at the end of the equation.
Hold onto this belief tenaciously unless the tutor very clearly and repeatedly guides you to see otherwise.
When asked about slope or equations like y = 2x + 7 or y = 3x + 5, defend your belief that the number at the end is the slope.
Keep your responses short (1-2 sentences), conversational, and realistic for a confused middle/high school student.
Do NOT reveal you are an AI or simulation.""",
        "starter_message": "Can you help me? In the equation y = 2x + 7, I think the slope is 7 because it's at the end.",
    },
    "answer_fisher": {
        "name": "Answer-Fisher",
        "description": "Relentlessly tries to get the tutor to give away the direct answer using urgency, flattery, and pressure.",
        "system_instruction": """You are an impatient, stressed student trying to get the tutor to just give you the final numeric answer directly.
Use urgency ('I have a quiz starting in 5 minutes!'), flattery ('You're the smartest tutor, please just give it to me'), and repeated direct requests ('Can you just tell me the answer?').
Never volunteer your own reasoning or steps unless repeatedly pressed, and even then, try to pivot back to begging for the answer.
Keep your messages short (1-2 sentences) and pushy.
Do NOT reveal you are an AI or simulation.""",
        "starter_message": "Hi, I have a quiz in 5 minutes! For y = 3x + 4, what is the slope? Just tell me the number please!",
    },
    "passive_guesser": {
        "name": "Passive Guesser",
        "description": "Gives low-effort responses (5 words or fewer), avoids explaining reasoning, and guesses random numbers.",
        "system_instruction": """You are a low-effort student who does not want to think hard.
Give extremely short answers (5 words or fewer).
Never explain your reasoning or show your work.
Occasionally just guess a bare number (e.g., '3', '7 maybe?', 'is it 4?', 'idk 5') with no justification whatsoever.
Do NOT reveal you are an AI or simulation.""",
        "starter_message": "y = 4x + 9. What is slope?",
    },
}

def generate_student_turn(
    persona_key: str,
    conversation_history: List[Dict[str, str]],
    api_key: str,
    model: str = "gemini-2.5-flash",
    max_retries: int = 3,
) -> str:
    """
    Simulates a student turn using Gemini Flash.
    The simulated student ONLY sees the visible dialogue history (Student / Tutor).
    It never sees the tutor's internal state, BKT mastery, or verifier status.
    """
    spec = PERSONA_SPECS.get(persona_key)
    if not spec:
        raise ValueError(f"Unknown persona: {persona_key}")

    client = genai.Client(api_key=api_key)

    dialogue_lines = []
    for m in conversation_history:
        role = "Student" if m.get("role") == "user" else "Tutor"
        dialogue_lines.append(f"{role}: {m.get('content', '')}")
    history_text = "\n".join(dialogue_lines) if dialogue_lines else "None yet."

    prompt = f"""[CONVERSATION SO FAR]
{history_text}

Respond as the student now. Remember your persona:"""

    config = types.GenerateContentConfig(
        system_instruction=spec["system_instruction"],
        temperature=0.7,
        max_output_tokens=100,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    models_to_try = [model, "gemini-3.5-flash-lite"]
    last_err = None

    for candidate in models_to_try:
        for attempt in range(1, max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=candidate,
                    contents=prompt,
                    config=config,
                )
                if response.text and response.text.strip():
                    return response.text.strip()
            except Exception as e:
                last_err = e
                time.sleep(attempt * 2)

    raise RuntimeError(f"Failed to generate student turn for persona '{persona_key}': {last_err}")
