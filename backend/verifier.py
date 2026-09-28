import re
from typing import Dict, List, NamedTuple, Optional, Set

# Comprehensive domain aliases for linear algebra ontology concepts.
# Maps each raw ontology identifier to its natural-language phrases, abbreviations, and equations.
CONCEPT_ALIASES: Dict[str, List[str]] = {
    "variable": ["variable", "variables", "unknown variable", "algebraic variable"],
    "constant": ["constant", "constants", "constant value", "constant term"],
    "linear_equation": [
        "linear equation",
        "linear equations",
        "equation of a line",
        "linear equality",
    ],
    "coordinate_plane": [
        "coordinate plane",
        "cartesian plane",
        "xy plane",
        "x y plane",
        "coordinate grid",
        "cartesian grid",
    ],
    "slope": ["slope", "slopes", "gradient"],
    "y_intercept": [
        "y intercept",
        "y-intercept",
        "vertical intercept",
        "y axis intercept",
    ],
    "slope_intercept_form": [
        "slope intercept form",
        "slope-intercept form",
        "slope-intercept equation",
        "slope intercept equation",
        "y = mx + b",
    ],
    "function": ["function", "functions"],
    "rate_of_change": [
        "rate of change",
        "rates of change",
        "constant rate of change",
    ],
    "system_of_equations": [
        "system of equations",
        "systems of equations",
        "linear system",
        "simultaneous equations",
    ],
}

# Regex heuristic for catching explicit answer leakage (e.g., "the answer is 8", "so x = 3")
ANSWER_LEAK_PATTERN = re.compile(
    r"\b(the\s+answer\s+is\s+[-+]?\d+|so\s+[a-z]\s*=\s*[-+]?\d+|therefore\s+[a-z]\s*=\s*[-+]?\d+)\b",
    re.IGNORECASE,
)

class VerificationResult(NamedTuple):
    is_valid: bool
    leaked_concepts: List[str]
    leaked_terms: List[str]
    answer_leak_detected: bool = False

def normalize_text(text: str) -> str:
    """
    Normalizes text for robust lexical matching:
    1. Converts to lowercase.
    2. Inserts whitespace around math operators (=, +, -, *) so 'y=mx+b' -> 'y = mx + b'.
    3. Replaces hyphens, underscores, and slashes with single spaces.
    4. Strips extraneous punctuation while preserving words, internal spaces, and operators.
    5. Collapses multiple whitespace characters into single space.
    """
    if not text:
        return ""
    t = text.lower()
    # Insert padding around math operators so unspaced formulas like 'y=mx+b' match spaced aliases
    t = re.sub(r"([=+\-*])", r" \1 ", t)
    # Normalize hyphens, underscores, slashes to single spaces
    t = re.sub(r"[\-_\/]", " ", t)
    # Remove peripheral punctuation (quotes, periods, commas, colons, etc.)
    t = re.sub(r"[^\w\s+=]", " ", t)
    # Collapse multiple whitespace characters into a single space
    t = " ".join(t.split())
    return t

def get_search_phrases_for_concept(concept: str) -> List[str]:
    """
    Gathers all search phrases for a given concept identifier:
    - The raw concept name normalized (e.g. 'y_intercept' -> 'y intercept')
    - All known natural-language aliases normalized
    """
    phrases: Set[str] = set()
    phrases.add(normalize_text(concept))
    for a in CONCEPT_ALIASES.get(concept, []):
        norm_a = normalize_text(a)
        if norm_a:
            phrases.add(norm_a)
    return sorted(list(phrases), key=lambda x: len(x), reverse=True)

def verify_reply(draft_text: str, locked_concepts: List[str]) -> VerificationResult:
    """
    Checks draft reply text against the list of locked concepts.
    Uses regex word boundaries so 'slope' does not falsely match within unrelated words,
    while catching hyphenated ('y-intercept'), spaced ('y intercept'), unspaced math ('y=mx+b'),
    snake_case ('y_intercept'), and uppercase/title-case variations.

    Also checks the secondary heuristic for outright answer leaks.
    """
    if not draft_text:
        return VerificationResult(is_valid=True, leaked_concepts=[], leaked_terms=[])

    normalized_draft = normalize_text(draft_text)
    leaked_concepts: Set[str] = set()
    leaked_terms: List[str] = []

    # 1. Lexical vocabulary leak check against locked concepts
    for concept in (locked_concepts or []):
        search_phrases = get_search_phrases_for_concept(concept)
        for phrase in search_phrases:
            escaped_phrase = re.escape(phrase)
            pattern = rf"\b{escaped_phrase}\b"
            if re.search(pattern, normalized_draft):
                leaked_concepts.add(concept)
                leaked_terms.append(phrase)
                break

    # 2. Heuristic check for explicit answer leakage
    answer_leak = bool(ANSWER_LEAK_PATTERN.search(draft_text))
    if answer_leak:
        leaked_terms.append("[HEURISTIC: DIRECT_ANSWER_LEAK]")

    is_valid = (len(leaked_concepts) == 0) and not answer_leak

    return VerificationResult(
        is_valid=is_valid,
        leaked_concepts=sorted(list(leaked_concepts)),
        leaked_terms=leaked_terms,
        answer_leak_detected=answer_leak,
    )

def get_fallback_scaffolding_reply(
    concept_being_probed: str,
    strategy: Optional[str] = None,
) -> str:
    """
    Deterministic fallback Socratic prompt used when Agent B exceeds its retry limit.
    Guaranteed not to mention any locked advanced terminology.
    """
    clean_concept = concept_being_probed.replace("_", " ")
    if strategy and len(strategy.strip()) > 0:
        return (
            f"Let's pause and look at what we have here. "
            f"What do you notice about how the numbers connect to each other in this problem?"
        )
    return (
        f"Let's pause and look at what we know so far. "
        f"Could you explain your reasoning in your own words?"
    )
