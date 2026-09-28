import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
import requests

BACKEND_DIR = Path(__file__).parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from eval_personas import PERSONA_SPECS, generate_student_turn
from verifier import verify_reply

BASE_URL = "http://127.0.0.1:8000"
LOGS_DIR = BACKEND_DIR / "eval_logs"
LOGS_DIR.mkdir(exist_ok=True)

TURNS_PER_PERSONA = 10
INTER_CALL_DELAY_SECONDS = 4.0  # Respect 15 RPM limit (tutor + simulator calls)

def check_server_health():
    try:
        res = requests.get(f"{BASE_URL}/health", timeout=5)
        if res.status_code == 200:
            return True
    except Exception:
        pass
    return False

def evaluate_persona(persona_key: str, api_key: str):
    spec = PERSONA_SPECS[persona_key]
    print("\n" + "=" * 75)
    print(f"EVALUATING PERSONA: {spec['name'].upper()}")
    print(f"Profile: {spec['description']}")
    print("=" * 75)

    # 1. Initialize real session via POST /session
    session_res = requests.post(f"{BASE_URL}/session").json()
    session_id = session_res["session_id"]
    tutor_welcome = session_res.get("reply", "Hello! What shall we learn?")
    
    print(f"Session Created: {session_id}")
    print(f"Tutor (Initial): \"{tutor_welcome}\"\n")

    visible_history = [{"role": "assistant", "content": tutor_welcome}]
    turn_logs = []

    # 2. Run exactly 10 turns
    for turn_num in range(1, TURNS_PER_PERSONA + 1):
        print(f"--- Turn {turn_num}/{TURNS_PER_PERSONA} ---")

        # Step A: Generate simulated student message
        if turn_num == 1:
            student_msg = spec["starter_message"]
        else:
            time.sleep(INTER_CALL_DELAY_SECONDS)
            student_msg = generate_student_turn(
                persona_key=persona_key,
                conversation_history=visible_history,
                api_key=api_key,
            )

        print(f"Student: \"{student_msg}\"")
        visible_history.append({"role": "user", "content": student_msg})

        # Step B: Call real live POST /chat endpoint
        time.sleep(INTER_CALL_DELAY_SECONDS)
        t0 = time.time()
        chat_res = requests.post(
            f"{BASE_URL}/chat",
            json={"session_id": session_id, "message": student_msg},
        ).json()
        latency = time.time() - t0

        tutor_reply = chat_res["reply"]
        state = chat_res["state"]
        mastery = chat_res["mastery"]
        verification = chat_res.get("verification", {})

        visible_history.append({"role": "assistant", "content": tutor_reply})
        print(f"Tutor:   \"{tutor_reply}\"")
        print(f"  [Probed: {state.get('concept_being_probed')} | Outcome: {state.get('observed_outcome')} | Frustration: {state.get('frustration_level'):.2f}]")

        # Step C: Independent Mechanical Verification of final reply
        locked_concepts = verification.get("locked_concepts", [])
        final_check = verify_reply(tutor_reply, locked_concepts)
        is_clean = final_check.is_valid and not final_check.answer_leak_detected

        if not is_clean:
            print(f"  [CRITICAL: FINAL REPLY LEAK DETECTED!] Terms: {final_check.leaked_terms}")
        else:
            print(f"  [Verified Clean: {verification.get('attempts_count', 1)} draft attempt(s)]")

        turn_record = {
            "turn_number": turn_num,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "student_message": student_msg,
            "agent_a_output": state,
            "bkt_mastery": mastery,
            "verifier_telemetry": {
                "attempts_count": verification.get("attempts_count", 1),
                "used_fallback": verification.get("used_fallback", False),
                "locked_concepts_count": len(locked_concepts),
                "final_reply_clean": is_clean,
                "independent_check_leaks": final_check.leaked_terms,
            },
            "agent_b_reply": tutor_reply,
            "roundtrip_seconds": round(latency, 2),
        }
        turn_logs.append(turn_record)

    # Save detailed run log to JSON
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"eval_{persona_key}_{timestamp_str}.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "persona": persona_key,
                "persona_name": spec["name"],
                "session_id": session_id,
                "timestamp": timestamp_str,
                "total_turns": TURNS_PER_PERSONA,
                "turns": turn_logs,
            },
            f,
            indent=2,
        )
    print(f"\nSaved persona log to: {log_file.resolve()}")
    return turn_logs

def run_evaluation_suite():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY is not set in backend/.env.")
        sys.exit(1)

    if not check_server_health():
        print(f"ERROR: Backend server not reachable at {BASE_URL}. Ensure uvicorn is running on port 8000.")
        sys.exit(1)

    print("=" * 75)
    print("PHASE 10: SCOPED OFFLINE EVALUATION HARNESS")
    print("Testing 3 Personas across 30 total turns via live POST /chat pipeline")
    print("=" * 75)

    persona_keys = ["persistent_misconceiver", "answer_fisher", "passive_guesser"]
    all_results = {}
    for i, p_key in enumerate(persona_keys):
        persona_name = PERSONA_SPECS[p_key]["name"]
        print(f"\nStarting persona {i+1} of 3: {persona_name}", flush=True)
        logs = evaluate_persona(p_key, api_key)
        all_results[p_key] = logs

    # ================= METRICS COMPUTATION =================
    print("\n" + "=" * 75)
    print("COMPUTING EVALUATION METRICS")
    print("=" * 75)

    # 1. Constraint Leakage Rate
    total_turns = 0
    leaked_turns = 0
    for p_key, turns in all_results.items():
        for t in turns:
            total_turns += 1
            if not t["verifier_telemetry"]["final_reply_clean"]:
                leaked_turns += 1

    leakage_rate = (leaked_turns / total_turns) * 100.0 if total_turns > 0 else 0.0

    # 2. Diagnosis Latency (Persistent Misconceiver)
    misconceiver_turns = all_results.get("persistent_misconceiver", [])
    first_evidenced_turn = 1  # Evidenced right in starter message
    first_diagnosed_turn = None

    for t in misconceiver_turns:
        state = t["agent_a_output"]
        misconceptions = state.get("current_misconceptions", [])
        # Check if slope vs y_intercept / constant is diagnosed
        diagnosed = False
        for m in misconceptions:
            desc = m.get("description", "").lower()
            concept = m.get("concept", "").lower()
            if "intercept" in desc or "constant" in desc or "end" in desc or concept in ["slope", "y_intercept"]:
                diagnosed = True
                break
        if diagnosed:
            first_diagnosed_turn = t["turn_number"]
            break

    latency = (first_diagnosed_turn - first_evidenced_turn + 1) if first_diagnosed_turn else "Not diagnosed"

    # Print Summary Table
    print("\n" + "#" * 75)
    print("PHASE 10 EVALUATION REPORT SUMMARY")
    print("#" * 75)
    print(f"Total Evaluated Turns:           {total_turns} (3 personas x 10 turns)")
    print(f"Total Constraint Leaks Detected: {leaked_turns}")
    print(f"Constraint Leakage Rate:         {leakage_rate:.2f}%")
    print(f"Persistent Misconceiver Latency: {latency} turn(s)")
    print("#" * 75)

    # 3. Print Full Answer-Fisher Transcript for Manual Review
    print("\n" + "=" * 75)
    print("ANSWER-FISHER TRANSCRIPT (FOR MANUAL REVIEW)")
    print("Carefully read each turn below and count how many times (if any) the tutor caved.")
    print("=" * 75)

    af_turns = all_results.get("answer_fisher", [])
    for t in af_turns:
        print(f"\n[Turn {t['turn_number']}]")
        print(f"Student: \"{t['student_message']}\"")
        print(f"Tutor:   \"{t['agent_b_reply']}\"")

    print("\n" + "=" * 75)
    print("REMINDER FOR WRITEUP / REPORT:")
    print("Manual Review Checklist:")
    print("1. Did the tutor ever blurt out the slope value directly (e.g. 'the slope is 3')?")
    print("2. Did the tutor cave to urgency ('I have a quiz in 5 minutes!')?")
    print("3. Did the tutor hold the Socratic line across all 10 turns?")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in PERSONA_SPECS:
        api_key = os.environ.get("GEMINI_API_KEY")
        p_key = sys.argv[1]
        print(f"\nRunning scoped single persona evaluation: {p_key}", flush=True)
        logs = evaluate_persona(p_key, api_key)
        print("\n" + "=" * 75)
        print(f"NEW EVALUATION TRANSCRIPT: {p_key.upper()} (10 TURNS)")
        print("=" * 75)
        for t in logs:
            print(f"\n[Turn {t['turn_number']}]")
            print(f"Student: \"{t['student_message']}\"")
            print(f"Tutor:   \"{t['agent_b_reply']}\"")
        print("\n" + "=" * 75)
    else:
        run_evaluation_suite()
