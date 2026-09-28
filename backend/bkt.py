from typing import Dict, List, Literal, Tuple

MASTERY_THRESHOLD = 0.85

# Standard BKT Default Parameters
DEFAULT_P_SLIP = 0.1     # Probability of making a mistake despite knowing the concept
DEFAULT_P_GUESS = 0.2    # Probability of guessing correctly without knowing the concept
DEFAULT_P_TRANSIT = 0.3  # Probability of learning/transitioning into mastery after the turn
DEFAULT_PARTIAL_WEIGHT = 0.5  # Credit assigned to 'partially_correct' answers

def update_mastery(
    p_l_prev: float,
    observed_outcome: str,
    p_slip: float = DEFAULT_P_SLIP,
    p_guess: float = DEFAULT_P_GUESS,
    p_transit: float = DEFAULT_P_TRANSIT,
    partial_weight: float = DEFAULT_PARTIAL_WEIGHT,
) -> float:
    """
    Updates the probability of mastery p(L) using Bayesian Knowledge Tracing (BKT)
    with a soft-evidence blend for 3-state outcomes: 'correct', 'partially_correct', 'incorrect'.

    Formula:
    1. Posterior under correct:
       P(L | correct) = (P_prev * (1 - P_slip)) / (P_prev * (1 - P_slip) + (1 - P_prev) * P_guess)
    2. Posterior under incorrect:
       P(L | incorrect) = (P_prev * P_slip) / (P_prev * P_slip + (1 - P_prev) * (1 - P_guess))
    3. Soft-evidence blend:
       P(L | observation) = credit * P(L | correct) + (1 - credit) * P(L | incorrect)
    4. Transition step (learning that occurs from the interaction):
       P(L_next) = P(L | observation) + (1 - P(L | observation)) * P_transit
    """
    # Clamp prior to valid probability interval (avoid divide-by-zero edges)
    p_l_prev = max(0.0001, min(0.9999, p_l_prev))

    # 1. Hard outcome posteriors
    num_correct = p_l_prev * (1.0 - p_slip)
    den_correct = num_correct + (1.0 - p_l_prev) * p_guess
    p_given_correct = num_correct / den_correct

    num_incorrect = p_l_prev * p_slip
    den_incorrect = num_incorrect + (1.0 - p_l_prev) * (1.0 - p_guess)
    p_given_incorrect = num_incorrect / den_incorrect

    # 2. Credit assignment based on observation
    outcome = observed_outcome.strip().lower()
    if outcome == "correct":
        credit = 1.0
    elif outcome == "partially_correct":
        credit = partial_weight
    else:  # 'incorrect' or any unmastered signal
        credit = 0.0

    # 3. Soft-evidence blend
    p_l_given_o = credit * p_given_correct + (1.0 - credit) * p_given_incorrect

    # 4. Knowledge transition (learning opportunity)
    p_l_next = p_l_given_o + (1.0 - p_l_given_o) * p_transit

    # Clamp output to [0.0, 1.0] and round to 4 decimals for clean storage
    return round(max(0.0, min(1.0, p_l_next)), 4)

def update_concept_mastery_map(
    current_mastery_map: Dict[str, float],
    concept_being_probed: str,
    observed_outcome: str,
    threshold: float = MASTERY_THRESHOLD,
) -> Dict[str, float]:
    """
    Takes the full concept mastery dictionary, updates the single probed concept,
    and leaves all other concepts unchanged.
    """
    updated_map = dict(current_mastery_map)
    prev_prob = updated_map.get(concept_being_probed, 0.15)
    new_prob = update_mastery(prev_prob, observed_outcome)
    updated_map[concept_being_probed] = new_prob
    return updated_map

def partition_concepts(
    mastery_map: Dict[str, float],
    threshold: float = MASTERY_THRESHOLD,
) -> Tuple[List[str], List[str]]:
    """
    Deterministic partition into:
    - mastered_concepts: p >= threshold
    - locked_concepts: p < threshold
    Computed purely in Python, never delegated to an LLM.
    """
    mastered = [concept for concept, prob in mastery_map.items() if prob >= threshold]
    locked = [concept for concept, prob in mastery_map.items() if prob < threshold]
    return mastered, locked
