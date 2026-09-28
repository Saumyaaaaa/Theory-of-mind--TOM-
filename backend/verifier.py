import re
from typing import Dict, List, NamedTuple, Optional, Set

# Comprehensive domain aliases for linear algebra ontology concepts.
# Maps each raw ontology identifier to its natural-language phrases and abbreviations.
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
        "y=mx+b",
        "y = mx+b",
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

class VerificationResult(NamedTuple):
    is_valid: bool
    leaked_concepts: List[str]
    leaked_terms: List[str]

def normalize_text(text: str) -> str:
    """
    Normalizes text for robust lexical matching:
    1. Converts to lowercase
    2. Replaces underscores, hyphens, and slashes with single spaces
    3. Normalizes common math expressions like 'y = mx + b'
    4. Strips peripheral punctuation while preserving words and internal spaces
    """
    if not text:
        return ""
    # Lowercase
    t = text.lower()
    # Normalize hyphens, underscores, slashes to single spaces
    t = re.sub(r"[\-_\/]", " ", t)
    # Remove stray punctuation but keep alphanumerics, spaces, and math symbols (+, =)
    t = re.sub(r"[^\w\s+=]", " ", t)
    # Collapse multiple whitespace characters into single space
    t = " ".join(t.split())
    return t

def get_search_phrases_for_concept(concept: str) -> List[str]:
    """
    Gathers all search phrases for a given concept identifier:
    - The raw concept name normalized (e.g. 'y_intercept' -> 'y intercept')
    - All known natural-language aliases normalized
    """
    phrases: Set[str] = set()
    # Add normalized raw identifier
    phrases.add(normalize_text(concept))
    # Add all aliases
    aliases = CONCEPT_ALIASES.get(concept, [])
    for a in aliases:
        norm_a = normalize_text(a)
        if norm_a:
            phrases.add(norm_a)
    return sorted(list(phrases), key=lambda x: len(x), reverse=True)

def verify_reply(draft_text: str, locked_concepts: List[str]) -> VerificationResult:
    """
    Checks draft reply text against the list of locked concepts.
    Uses regex word boundaries so 'slope' does not falsely match within unrelated words,
    while catching hyphenated ('y-intercept'), spaced ('y intercept'),
    snake_case ('y_intercept'), and uppercase/title-case variations.

    Returns VerificationResult(is_valid, leaked_concepts, leaked_terms).
    """
    if not draft_text or not locked_concepts:
        return VerificationResult(is_valid=True, leaked_concepts=[], leaked_terms=[])

    normalized_draft = normalize_text(draft_text)
    leaked_concepts: Set[str] = set()
    leaked_terms: List[str] = []

    for concept in locked_concepts:
        search_phrases = get_search_phrases_for_concept(concept)
        for phrase in search_phrases:
            # Match using word boundaries to avoid partial word collisions
            # Escape regex special chars (like +, =) in phrases
            escaped_phrase = re.escape(phrase)
            pattern = rf"\b{escaped_phrase}\b"
            if re.search(pattern, normalized_draft):
                leaked_concepts.add(concept)
                leaked_terms.append(phrase)
                # Break to next concept once one term from this concept is found
                break

    is_valid = len(leaked_concepts) == 0
    return VerificationResult(
        is_valid=is_valid,
        leaked_concepts=sorted(list(leaked_concepts)),
        leaked_terms=leaked_terms,
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
            f"Let's take a step back and examine this step by step. "
            f"What do you notice about how the numbers connect to each other in this problem?"
        )
    return (
        f"Let's pause and look at what we know so far. "
        f"Could you explain your reasoning in your own words?"
    )
