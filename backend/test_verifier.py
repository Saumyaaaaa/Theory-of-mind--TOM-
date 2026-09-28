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

    def test_alias_mathematical_notation_leak(self):
        """Must catch alias formulas like 'y = mx + b' when slope_intercept_form is locked."""
        draft = "Let's plug our values into y = mx + b to see what happens."
        result = verify_reply(draft, self.locked_concepts)
        self.assertFalse(result.is_valid)
        self.assertIn("slope_intercept_form", result.leaked_concepts)
        print(f"[TEST 5 PASS] Mathematical alias leak detected: {result.leaked_terms} -> {result.leaked_concepts}")

    def test_word_boundaries_prevent_false_positives(self):
        """
        Must NOT falsely flag unrelated words that contain locked substrings.
        e.g., 'antelope' should not match 'slope', 'invariable' should not match 'variable'.
        """
        draft = "An antelope ran across the plain in a constant direction."
        # 'constant' is NOT in locked_concepts, 'slope' is locked.
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

    def test_fallback_reply_generation(self):
        """Fallback reply generation produces clean Socratic text without locked terms."""
        fallback = get_fallback_scaffolding_reply("slope", strategy="Guide them through rise over run.")
        result = verify_reply(fallback, self.locked_concepts)
        self.assertTrue(result.is_valid, "Fallback reply itself must never contain locked terms!")
        self.assertGreater(len(fallback), 20)
        print(f"[TEST 8 PASS] Safe fallback generated: \"{fallback}\"")

if __name__ == "__main__":
    print("=" * 65)
    print("RUNNING PHASE 5 VERIFIER UNIT TESTS")
    print("=" * 65)
    unittest.main(verbosity=2)
