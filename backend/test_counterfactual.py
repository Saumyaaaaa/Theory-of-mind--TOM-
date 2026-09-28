import requests

BASE_URL = "http://127.0.0.1:8000"

def test_counterfactual_prereq_graph():
    print("=" * 70)
    print("PHASE 9: TESTING /counterfactual ENDPOINT & GRAPH AWARENESS")
    print("=" * 70)

    # 1. Create a session
    s_res = requests.post(f"{BASE_URL}/session").json()
    session_id = s_res["session_id"]
    print(f"Session Created: {session_id}")

    # 2. Learner asks about slope-intercept form
    prompt_msg = "Can you explain how y = 2x + 7 connects to slope and the intercept?"
    chat_res = requests.post(
        f"{BASE_URL}/chat",
        json={"session_id": session_id, "message": prompt_msg},
    ).json()

    real_reply = chat_res["reply"]
    print(f"\n[REAL TURN]")
    print(f"Learner Message: \"{prompt_msg}\"")
    print(f"Real Tutor Reply: \"{real_reply}\"")
    print(f"Real Locked Concepts: {chat_res['verification']['locked_concepts']}")

    # Check snapshots count before counterfactual
    hist_before = requests.get(f"{BASE_URL}/state/{session_id}/history").json()
    snapshots_before_count = hist_before["snapshots_count"]

    # 3. Counterfactual Run: Force 'slope' to mastered (0.95), but leave 'y_intercept' locked (0.15)
    print("\n--- RUNNING COUNTERFACTUAL ---")
    print("Hypothetical Change: Force 'slope' -> 0.95 (Mastered), keep 'y_intercept' -> 0.15 (Locked)")

    cf_req = {
        "session_id": session_id,
        "modified_mastery": {
            "slope": 0.95,
            # y_intercept remains locked (0.15)
        },
        "modified_state": {
            "suggested_scaffolding_strategy": "Since the learner has mastered slope, encourage them to focus on the constant term."
        }
    }

    cf_res = requests.post(f"{BASE_URL}/counterfactual", json=cf_req).json()
    cf_reply = cf_res["counterfactual_reply"]
    cf_locked = cf_res["verification"]["locked_concepts"]
    cf_mastered = cf_res["verification"]["mastered_concepts"]

    print(f"\n[COUNTERFACTUAL COMPARISON]")
    print(f"Real Reply:           \"{real_reply}\"")
    print(f"Counterfactual Reply: \"{cf_reply}\"")
    print(f"Counterfactual Mastered: {cf_mastered}")
    print(f"Counterfactual Locked:   {cf_locked}")

    # Critical Assertions:
    # 1. 'slope' is in mastered
    assert "slope" in cf_mastered, "Expected 'slope' in counterfactual mastered list"
    # 2. 'y_intercept' is STILL in locked
    assert "y_intercept" in cf_locked, "Expected 'y_intercept' to remain locked"
    # 3. 'slope_intercept_form' is STILL in locked because it requires both slope and y_intercept!
    assert "slope_intercept_form" in cf_locked, "Expected 'slope_intercept_form' to remain locked because y_intercept is unmastered"

    # 4. Verify SQLite Snapshot Immutability (no side-effects)
    hist_after = requests.get(f"{BASE_URL}/state/{session_id}/history").json()
    assert hist_after["snapshots_count"] == snapshots_before_count, "Counterfactual call must NOT add snapshots to SQLite!"

    print("\n" + "=" * 70)
    print("TEST PASSED: Counterfactual derived locked_concepts via partition_concepts.")
    print("Graph prerequisite integrity confirmed (slope_intercept_form remained locked).")
    print("SQLite state immutability confirmed (no ghost snapshots created).")
    print("=" * 70)

if __name__ == "__main__":
    test_counterfactual_prereq_graph()
