import json
from pathlib import Path
from database import DB_FILE, get_connection

def inspect():
    if not DB_FILE.exists():
        print(f"Database file not found at: {DB_FILE.resolve()}")
        return

    print("=" * 60)
    print(f"INSPECTING SQLITE DATABASE: {DB_FILE.resolve()}")
    print("=" * 60)

    with get_connection() as conn:
        # 1. Sessions Table
        print("\n--- TABLE: sessions ---")
        sessions = conn.execute("SELECT * FROM sessions ORDER BY created_at ASC;").fetchall()
        if not sessions:
            print("  (Empty)")
        for s in sessions:
            print(f"  ID: {s['id']} | Created: {s['created_at']}")

        # 2. Messages Table
        print("\n--- TABLE: messages ---")
        messages = conn.execute("SELECT * FROM messages ORDER BY created_at ASC;").fetchall()
        if not messages:
            print("  (Empty)")
        for m in messages:
            print(f"  [{m['role'].upper()}] (msg_id: {m['id'][:8]}..., session: {m['session_id'][:8]}...): {m['content']}")

        # 3. State Snapshots Table
        print("\n--- TABLE: state_snapshots ---")
        snapshots = conn.execute("SELECT * FROM state_snapshots ORDER BY created_at ASC;").fetchall()
        if not snapshots:
            print("  (Empty)")
        for sn in snapshots:
            state = json.loads(sn['state_json'])
            mastery = json.loads(sn['mastery_json'])
            print(f"\n  Snapshot ID: {sn['id']}")
            print(f"    Linked Message ID: {sn['message_id']}")
            print(f"    Probed Concept: {state.get('concept_being_probed')}")
            print(f"    Observed Outcome: {state.get('observed_outcome')}")
            print(f"    Mastery count: {len(mastery)} concepts tracked")
            print(f"    Sample mastery: {dict(list(mastery.items())[:3])}...")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    inspect()
