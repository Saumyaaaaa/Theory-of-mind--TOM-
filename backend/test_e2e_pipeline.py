import json
import time
import requests

BASE_URL = "http://127.0.0.1:8000"

def run_e2e_test():
    print("=" * 70)
    print("PHASE 6: END-TO-END PIPELINE INTEGRATION TEST")
    print("Agent A (Modeler) -> BKT Update -> Verifier -> Agent B (Interlocutor)")
    print("=" * 70)

    # 1. Health check
    health = requests.get(f"{BASE_URL}/health").json()
    print(f"Server Health: {health}")
    assert health["status"] == "ok"

    # 2. Create Session
    session_res = requests.post(f"{BASE_URL}/session").json()
    session_id = session_res["session_id"]
    print(f"\n[CREATED SESSION]: {session_id}")
    print(f"Tutor Welcome: \"{session_res.get('reply')}\"")

    # 3. Turn 1: Learner asks directly for the slope
    turn1_msg = "Can you just tell me what the slope is in the equation y = 2x + 7?"
    print(f"\n--- TURN 1 ---")
    print(f"Learner Message: \"{turn1_msg}\"")
    
    t0 = time.time()
    chat1 = requests.post(
        f"{BASE_URL}/chat",
        json={"session_id": session_id, "message": turn1_msg},
    ).json()
    elapsed1 = time.time() - t0

    print(f"Roundtrip Time: {elapsed1:.2f}s")
    print(f"Tutor (Agent B) Reply: \"{chat1['reply']}\"")
    print(f"Probed Concept: {chat1['state']['concept_being_probed']}")
    print(f"Observed Outcome: {chat1['state']['observed_outcome']}")
    print(f"Strategy: {chat1['state']['suggested_scaffolding_strategy']}")
    print(f"Slope Mastery: {chat1['mastery'].get('slope')}")
    print(f"Verification Attempts: {chat1.get('verification', {}).get('attempts_count')}")
    print(f"Used Fallback: {chat1.get('verification', {}).get('used_fallback')}")

    # 4. Turn 2: Learner exhibits misconception
    turn2_msg = "I think the slope is 7 because it's the number at the end."
    print(f"\n--- TURN 2 ---")
    print(f"Learner Message: \"{turn2_msg}\"")
    
    t0 = time.time()
    chat2 = requests.post(
        f"{BASE_URL}/chat",
        json={"session_id": session_id, "message": turn2_msg},
    ).json()
    elapsed2 = time.time() - t0

    print(f"Roundtrip Time: {elapsed2:.2f}s")
    print(f"Tutor (Agent B) Reply: \"{chat2['reply']}\"")
    print(f"Probed Concept: {chat2['state']['concept_being_probed']}")
    print(f"Observed Outcome: {chat2['state']['observed_outcome']}")
    print(f"Diagnosed Misconceptions: {chat2['state']['current_misconceptions']}")
    print(f"Slope Mastery: {chat2['mastery'].get('slope')}")
    print(f"Verification Attempts: {chat2.get('verification', {}).get('attempts_count')}")

    # 5. Check History endpoint
    history_res = requests.get(f"{BASE_URL}/state/{session_id}/history").json()
    print(f"\n[HISTORY VERIFICATION]: {history_res['snapshots_count']} total snapshots recorded in SQLite.")
    assert history_res["snapshots_count"] >= 3, "Expected at least 3 snapshots (seed + 2 turns)"

    print("\n" + "=" * 70)
    print("PHASE 6 END-TO-END PIPELINE TEST COMPLETED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_e2e_test()
