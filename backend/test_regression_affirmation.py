import requests

BASE_URL = "http://127.0.0.1:8000"

def test_no_false_affirmation():
    # 1. Create session
    s_res = requests.post(f"{BASE_URL}/session").json()
    sid = s_res["session_id"]
    
    # 2. Send incorrect answer: learner confuses slope with intercept
    msg = "In y = 3x + 4, I think the slope is 4 because it's at the end."
    chat_res = requests.post(
        f"{BASE_URL}/chat",
        json={"session_id": sid, "message": msg},
    ).json()

    print("=" * 60)
    print("REGRESSION TEST: NO FALSE AFFIRMATION ON INCORRECT TURNS")
    print(f"Learner Message: \"{msg}\"")
    print(f"Diagnosed Outcome: {chat_res['state']['observed_outcome']}")
    print(f"Diagnosed Misconceptions: {chat_res['state']['current_misconceptions']}")
    print(f"Agent B Reply: \"{chat_res['reply']}\"")
    print("=" * 60)

    reply_lower = chat_res["reply"].lower()
    forbidden_affirmations = ["good thought", "nice try", "great thinking", "you're on the right track", "almost"]
    for phrase in forbidden_affirmations:
        assert phrase not in reply_lower, f"Violation: Found false praise '{phrase}' in tutor reply!"

    print("VERIFICATION SUCCESS: No false affirmation was used. Tutor addressed student neutrally.")

if __name__ == "__main__":
    test_no_false_affirmation()
