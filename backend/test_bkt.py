import sys
import unittest
from pathlib import Path

# Add backend directory to module search path
sys.path.insert(0, str(Path(__file__).parent))

from bkt import (
    MASTERY_THRESHOLD,
    update_mastery,
    update_concept_mastery_map,
    get_effective_mastery,
    partition_concepts,
)

class TestBayesianKnowledgeTracing(unittest.TestCase):

    def test_single_correct_answer(self):
        """A correct answer should sharply increase mastery probability."""
        prior = 0.15
        post = update_mastery(prior, observed_outcome="correct")
        self.assertGreater(post, prior, "Mastery must increase after a correct answer.")
        self.assertAlmostEqual(post, 0.6098, places=3)
        print(f"[TEST 1 PASS] Correct update: {prior} -> {post}")

    def test_single_incorrect_answer(self):
        """An incorrect answer should penalize belief of mastery."""
        prior = 0.50
        post = update_mastery(prior, observed_outcome="incorrect")
        self.assertLess(post, prior, "Mastery must decrease after an incorrect answer when prior is high.")
        self.assertAlmostEqual(post, 0.3778, places=3)
        print(f"[TEST 2 PASS] Incorrect update: {prior} -> {post}")

    def test_partially_correct_soft_evidence_blend(self):
        """
        Partially correct must land strictly between incorrect and correct posteriors.
        With weight 0.5, the blended pre-transit belief should be the exact midpoint.
        """
        prior = 0.40
        post_correct = update_mastery(prior, "correct")
        post_partial = update_mastery(prior, "partially_correct")
        post_incorrect = update_mastery(prior, "incorrect")

        self.assertLess(post_incorrect, post_partial, "Partial must be higher than incorrect.")
        self.assertLess(post_partial, post_correct, "Partial must be lower than correct.")

        midpoint = (post_correct + post_incorrect) / 2.0
        diff = abs(post_partial - midpoint)
        self.assertLess(diff, 0.05, f"Partial ({post_partial}) should be close to midpoint ({midpoint}).")

        print(f"[TEST 3 PASS] Soft-Evidence Blend (Prior={prior}):")
        print(f"   Incorrect:         {post_incorrect}")
        print(f"   Partially Correct: {post_partial}  (Midpoint={round(midpoint, 4)})")
        print(f"   Correct:           {post_correct}")

    def test_consecutive_correct_crosses_mastery_threshold(self):
        """Simulate a learner answering correctly multiple times until crossing 0.85 threshold."""
        prob = 0.15
        history = [prob]
        turns = 0

        while prob < MASTERY_THRESHOLD and turns < 10:
            prob = update_mastery(prob, "correct")
            turns += 1
            history.append(prob)

        self.assertGreaterEqual(prob, MASTERY_THRESHOLD, "Learner must reach mastery.")
        self.assertLessEqual(turns, 3, "From 0.15, standard BKT reaches 0.85 in 2-3 correct turns.")
        print(f"[TEST 4 PASS] Multi-turn progression to mastery ({turns} turns):")
        print("   " + " -> ".join([f"{p:.4f}" for p in history]))

    def test_consecutive_incorrect_stays_unmastered(self):
        """Simulate consecutive errors: mastery stays well below the 0.85 threshold."""
        prob = 0.15
        for _ in range(5):
            prob = update_mastery(prob, "incorrect")
        self.assertLess(prob, MASTERY_THRESHOLD)
        self.assertLess(prob, 0.40)
        print(f"[TEST 5 PASS] 5 consecutive failures plateau at: {prob:.4f}")

    def test_partition_concepts_locked_and_mastered(self):
        """Tests deterministic segregation into mastered and locked concepts."""
        mastery_map = {
            "variable": 0.95,
            "constant": 0.88,
            "linear_equation": 0.85,
            "coordinate_plane": 0.8499,
            "slope": 0.42,
            "y_intercept": 0.15,
        }

        mastered, locked = partition_concepts(mastery_map, threshold=0.85)

        self.assertEqual(sorted(mastered), sorted(["variable", "constant", "linear_equation"]))
        self.assertEqual(sorted(locked), sorted(["coordinate_plane", "slope", "y_intercept"]))
        print(f"[TEST 6 PASS] Partition test:")
        print(f"   Mastered (>= 0.85): {mastered}")
        print(f"   Locked   (<  0.85): {locked}")

    def test_boundary_and_numerical_stability(self):
        """Verifies no divide-by-zero or NaN on boundary values."""
        for edge in [0.0, 0.0001, 0.5, 0.9999, 1.0]:
            for outcome in ["correct", "incorrect", "partially_correct", "unknown"]:
                res = update_mastery(edge, outcome)
                self.assertTrue(0.0 <= res <= 1.0, f"Value out of bounds: {res} for prior={edge}, outcome={outcome}")
        print("[TEST 7 PASS] Numerical stability and boundary tests passed.")

    def test_structural_prerequisite_effective_mastery_gating(self):
        """
        Structural safeguard:
        A composite concept's effective mastery can NEVER exceed the minimum mastery
        of its prerequisites.
        If slope_intercept_form has raw 0.90 but y_intercept has raw 0.15,
        its effective mastery must be 0.15 and it must remain locked!
        """
        concept_graph = {
            "variable": {"prereqs": []},
            "constant": {"prereqs": []},
            "linear_equation": {"prereqs": ["variable", "constant"]},
            "coordinate_plane": {"prereqs": []},
            "slope": {"prereqs": ["linear_equation", "coordinate_plane"]},
            "y_intercept": {"prereqs": ["linear_equation", "coordinate_plane"]},
            "slope_intercept_form": {"prereqs": ["slope", "y_intercept"]},
        }

        raw_mastery = {
            "variable": 0.95,
            "constant": 0.95,
            "linear_equation": 0.95,
            "coordinate_plane": 0.95,
            "slope": 0.92,
            "y_intercept": 0.15,
            "slope_intercept_form": 0.90,
        }

        eff_slope_intercept = get_effective_mastery("slope_intercept_form", raw_mastery, concept_graph)
        self.assertEqual(eff_slope_intercept, 0.15, "Effective mastery of slope_intercept_form must be capped at 0.15 by unmastered y_intercept!")

        mastered, locked = partition_concepts(raw_mastery, concept_graph=concept_graph, threshold=0.85)

        self.assertIn("slope_intercept_form", locked, "slope_intercept_form must remain locked despite 0.90 raw probability!")
        self.assertNotIn("slope_intercept_form", mastered)
        print(f"[TEST 8 PASS] Structural prerequisite safeguard verified: effective mastery = {eff_slope_intercept}, locked = {locked}")

if __name__ == "__main__":
    print("=" * 65)
    print("RUNNING BKT UNIT TESTS WITH STRUCTURAL PREREQUISITE GATING")
    print("=" * 65)
    unittest.main(verbosity=2)
