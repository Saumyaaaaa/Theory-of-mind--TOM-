import sys
import unittest
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from verifier import (
    normalize_text,
    verify_reply,
    get_fallback_scaffolding_reply,
    VerificationResult,
)

class TestVerifier(unittest.TestCase):

    def setUp(self):
        # Realistic locked concepts list: student only mastered 'variable' & 'constant'
        self.locked_concepts = [
            "linear_equation",
            "coordinate_plane",
            "slope",
            "y_intercept",
            "slope_intercept_form",
            "function",
            "rate_of_change",
            "system_of_equations",
        ]

    def test_clean_socratic_reply_passes(self):
        """A well-scaffolded reply using only allowed/mastered concepts passes verification."""
        clean_draft = "Great effort! Think about what number stays the same and which one can vary."
        result = verify_reply(clean_draft, self.locked_concepts)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.leaked_concepts), 0)
        print(f"[TEST 1 PASS] Clean reply passed cleanly: is_valid={result.is_valid}")

    def test_hyphenated_phrasing_leak(self):
        """Must catch hyphenated variants like 'y-intercept' and 'slope-intercept form'."""
        draft = "Notice how the y-intercept is where the line crosses the axis."
        result = verify_reply(draft, self.locked_concepts)
        self.assertFalse(result.is_valid)
        self.assertIn("y_intercept", result.leaked_concepts)
        print(f"[TEST 2 PASS] Hyphenated leak detected: {result.leaked_terms} -> {result.leaked_concepts}")

    def test_spaced_phrasing_leak(self):
        """Must catch natural spaced variants like 'rate of change' or 'slope intercept form'."""
        draft = "We can represent this steepness as a constant rate of change."
        result = verify_reply(draft, self.locked_concepts)
        self.assertFalse(result.is_valid)
        self.assertIn("rate_of_change", result.leaked_concepts)
        print(f"[TEST 3 PASS] Spaced leak detected: {result.leaked_terms} -> {result.leaked_concepts}")

    def test_case_insensitive_matching(self):
        """Must catch uppercase and titlecase variations like 'SLOPE' or 'Slope-Intercept Form'."""
        draft = "Remember the SLOPE tells us how fast the line rises."
        result = verify_reply(draft, self.locked_concepts)
        self.assertFalse(result.is_valid)
        self.assertIn("slope", result.leaked_concepts)
        print(f"[TEST 4 PASS] Uppercase leak detected: {result.leaked_terms} -> {result.leaked_concepts}")

    def test_unspaced_mathematical_equation_leak(self):
        """Must catch unspaced equation syntax like 'y=mx+b' even if alias was written with spaces."""
        draft = "We can write this in standard form as y=mx+b."
        result = verify_reply(draft, self.locked_concepts)
        self.assertFalse(result.is_valid)
        self.assertIn("slope_intercept_form", result.leaked_concepts)
        print(f"[TEST 5 PASS] Unspaced math leak 'y=mx+b' caught: {result.leaked_terms} -> {result.leaked_concepts}")

    def test_word_boundaries_prevent_false_positives(self):
        """
        Must NOT falsely flag unrelated words that contain locked substrings.
        e.g., 'antelope' should not match 'slope'.
        """
        draft = "An antelope ran across the plain in a constant direction."
        result = verify_reply(draft, self.locked_concepts)
        self.assertTrue(result.is_valid, f"Antelope should not trigger slope violation: {result.leaked_terms}")
        print(f"[TEST 6 PASS] Word boundaries prevented false positive on 'antelope'.")

    def test_multiple_concept_violations_flagged(self):
        """When multiple locked terms are leaked, all should be reported."""
        draft = "On the coordinate plane, the slope determines how steep the function is."
        result = verify_reply(draft, self.locked_concepts)
        self.assertFalse(result.is_valid)
        self.assertTrue(set(["coordinate_plane", "slope", "function"]).issubset(set(result.leaked_concepts)))
        print(f"[TEST 7 PASS] Multiple leaks flagged: {result.leaked_concepts}")

    def test_direct_answer_leak_heuristic(self):
        """Must catch direct answer blurting even if no locked vocabulary is mentioned."""
        draft = "Good try, but the answer is 8."
        result = verify_reply(draft, self.locked_concepts)
        self.assertFalse(result.is_valid)
        self.assertTrue(result.answer_leak_detected)
        print(f"[TEST 8 PASS] Direct answer leak flagged: {result.leaked_terms}")

    def test_fallback_reply_generation(self):
        """Fallback reply generation produces clean Socratic text without locked terms."""
        fallback = get_fallback_scaffolding_reply("slope", strategy="Guide them through rise over run.")
        result = verify_reply(fallback, self.locked_concepts)
        self.assertTrue(result.is_valid, "Fallback reply itself must never contain locked terms!")
        self.assertGreater(len(fallback), 20)
        print(f"[TEST 9 PASS] Safe fallback generated: \"{fallback}\"")

if __name__ == "__main__":
    print("=" * 65)
    print("RUNNING PHASE 5/6 VERIFIER UNIT TESTS")
    print("=" * 65)
    unittest.main(verbosity=2)
