from typing import Dict, List, Optional, Set, Tuple

# --------
# Utilities
# --------
def _contains_all(text: str, keywords: List[str]) -> bool:
    tl = text.lower()
    return all(k.lower() in tl for k in keywords)


def find_course_by_keywords(
    catalog: Dict[str, any],
    grade: int,
    keywords: List[str],
    exclude: Set[str],
    prefer_honors: bool = False,   # <-- added for backward compatibility
    **kwargs,                      # <-- absorb any future params safely
) -> Optional[str]:
    """
    Backward compatible helper (optimizer_v1 calls prefer_honors=...).
    Finds first course in catalog that:
      - is offered in grade
      - not in exclude
      - title contains ALL keywords

    prefer_honors is accepted for compatibility; current matching is exact-title order
    determined by catalog iteration. If later you want honors-first, we can implement it.
    """
    for title, c in catalog.items():
        if title in exclude:
            continue
        if grade not in c.allowed_grades:
            continue
        if _contains_all(title, keywords):
            return title
    return None



    """
    Public on purpose (optimizer_v1 imports this).
    Finds first course in catalog that:
      - is offered in grade
      - not in exclude
      - title contains ALL keywords
    """
    for title, c in catalog.items():
        if title in exclude:
            continue
        if grade not in c.allowed_grades:
            continue
        if _contains_all(title, keywords):
            return title
    return None


# --------
# Math sequencing
# --------
# This is intentionally minimal + matches your Foothill list.
# If you later want different tracks (Math II/III/IV), we can extend safely.
REGULAR_SEQ = [
    ("geometry",        ["Geometry (P)"]),
    ("algebra2",        ["Algebra II (P)"]),
    ("precalc",         ["Pre-Calculus (P)"]),
    ("calc_ab",         ["AP Calculus AB (HP)"]),
    ("calc_bc",         ["AP Calculus BC (HP)"]),
]

HONORS_SEQ = [
    ("hon_geometry",    ["Honors Geometry (P)"]),
    ("hon_algebra2",    ["Honors Algebra II (P)"]),
    ("hon_precalc",     ["Honors Pre-Calculus (HP)"]),
    ("calc_ab",         ["AP Calculus AB (HP)"]),
    ("calc_bc",         ["AP Calculus BC (HP)"]),
]


def _normalize_completed_math_key(completed_math_title: str) -> Tuple[str, bool]:
    """
    Returns (key, is_honors_track_guess)
    """
    t = (completed_math_title or "").lower()

    is_hon = "honors" in t or "(hp)" in t

    if "geometry" in t:
        return ("geometry", is_hon)
    if "algebra" in t and ("ii" in t or "2" in t):
        return ("algebra2", is_hon)
    if "pre" in t and "cal" in t:
        return ("precalc", is_hon)
    if "calculus" in t and "bc" in t:
        return ("calc_bc", True)
    if "calculus" in t and "ab" in t:
        return ("calc_ab", True)
    if "statistics" in t or "stats" in t:
        return ("ap_stats", True)

    # default: treat as geometry
    return ("geometry", is_hon)


def _next_math_title_after_completed(catalog, grade: int, completed_math: str, exclude: Set[str]) -> Optional[str]:
    """
    Given the highest completed math title, choose the next logical course.
    Honors track if the completed course looks honors-ish.
    """
    key, is_hon = _normalize_completed_math_key(completed_math)

    # Decide sequence
    seq = HONORS_SEQ if is_hon else REGULAR_SEQ

    # Find current position in sequence (fallback to first if unknown)
    idx = 0
    for i, (k, _) in enumerate(seq):
        if k == "hon_" + key or k == key or (key == "algebra2" and k in ("hon_algebra2", "algebra2")):
            idx = i
            break

    # Next step
    next_i = min(idx + 1, len(seq) - 1)
    _, candidates = seq[next_i]

    for title in candidates:
        if title in catalog and grade in catalog[title].allowed_grades and title not in exclude:
            return title

    # Keyword fallback (rare)
    if next_i < len(seq):
        if "algebra2" in seq[next_i][0]:
            # honors-first if honors track
            if is_hon:
                return (
                    find_course_by_keywords(catalog, grade, ["honors", "algebra", "ii"], exclude)
                    or find_course_by_keywords(catalog, grade, ["honors", "algebra", "2"], exclude)
                    or find_course_by_keywords(catalog, grade, ["algebra", "ii"], exclude)
                    or find_course_by_keywords(catalog, grade, ["algebra", "2"], exclude)
                )
            return (
                find_course_by_keywords(catalog, grade, ["algebra", "ii"], exclude)
                or find_course_by_keywords(catalog, grade, ["algebra", "2"], exclude)
                or find_course_by_keywords(catalog, grade, ["honors", "algebra", "ii"], exclude)
                or find_course_by_keywords(catalog, grade, ["honors", "algebra", "2"], exclude)
            )

        if "precalc" in seq[next_i][0]:
            if is_hon:
                return (
                    find_course_by_keywords(catalog, grade, ["honors", "pre"], exclude)
                    or find_course_by_keywords(catalog, grade, ["honors", "precal"], exclude)
                    or find_course_by_keywords(catalog, grade, ["pre", "cal"], exclude)
                )
            return (
                find_course_by_keywords(catalog, grade, ["pre", "cal"], exclude)
                or find_course_by_keywords(catalog, grade, ["precal"], exclude)
                or find_course_by_keywords(catalog, grade, ["honors", "pre"], exclude)
            )

        if "calc_ab" == seq[next_i][0]:
            return (
                find_course_by_keywords(catalog, grade, ["ap", "calculus", "ab"], exclude)
                or find_course_by_keywords(catalog, grade, ["calculus", "ab"], exclude)
            )

        if "calc_bc" == seq[next_i][0]:
            return (
                find_course_by_keywords(catalog, grade, ["ap", "calculus", "bc"], exclude)
                or find_course_by_keywords(catalog, grade, ["calculus", "bc"], exclude)
            )

    return None


# Backward compatible track map (your old approach)
MATH_TRACK = {
    "honors_geometry": ["algebra2", "precalc", "calc_ab", "calc_bc"],
    "algebra2":        ["precalc", "calc_ab", "calc_bc", "calc_bc"],
    "honors_algebra2": ["precalc", "calc_ab", "calc_bc", "calc_bc"],
}


def pick_math_for_grade(
    catalog,
    grade: int,
    year_index: int,
    exclude: Set[str],
    completed_math: Optional[str] = None,
    starting_math: str = "honors_algebra2",
) -> Optional[str]:
    """
    D) Preferred behavior:
      - If completed_math is provided -> pick NEXT course after that
      - Else -> use starting_math legacy behavior

    year_index: 0 for grade 9, 1 for grade 10, 2 for grade 11, 3 for grade 12
    """
    # If completed_math exists, always use it to pick "next"
    if completed_math:
        return _next_math_title_after_completed(catalog, grade, completed_math, exclude)

    # Legacy behavior
    track = MATH_TRACK.get(starting_math, MATH_TRACK["honors_geometry"])
    desired = track[min(year_index, len(track) - 1)]

    # IMPORTANT: honors-first ordering when starting_math implies honors
    honors_expected = (starting_math == "honors_algebra2")

    if desired == "algebra2":
        if honors_expected:
            return (
                find_course_by_keywords(catalog, grade, ["honors", "algebra", "ii"], exclude)
                or find_course_by_keywords(catalog, grade, ["honors", "algebra", "2"], exclude)
                or find_course_by_keywords(catalog, grade, ["algebra", "ii"], exclude)
                or find_course_by_keywords(catalog, grade, ["algebra", "2"], exclude)
            )
        return (
            find_course_by_keywords(catalog, grade, ["algebra", "ii"], exclude)
            or find_course_by_keywords(catalog, grade, ["algebra", "2"], exclude)
            or find_course_by_keywords(catalog, grade, ["honors", "algebra", "ii"], exclude)
            or find_course_by_keywords(catalog, grade, ["honors", "algebra", "2"], exclude)
        )

    if desired == "precalc":
        if honors_expected:
            return (
                find_course_by_keywords(catalog, grade, ["honors", "pre"], exclude)
                or find_course_by_keywords(catalog, grade, ["honors", "precal"], exclude)
                or find_course_by_keywords(catalog, grade, ["pre", "cal"], exclude)
            )
        return (
            find_course_by_keywords(catalog, grade, ["pre", "cal"], exclude)
            or find_course_by_keywords(catalog, grade, ["precal"], exclude)
            or find_course_by_keywords(catalog, grade, ["honors", "pre"], exclude)
        )

    if desired == "calc_ab":
        return (
            find_course_by_keywords(catalog, grade, ["ap", "calculus", "ab"], exclude)
            or find_course_by_keywords(catalog, grade, ["calculus", "ab"], exclude)
        )

    if desired == "calc_bc":
        return (
            find_course_by_keywords(catalog, grade, ["ap", "calculus", "bc"], exclude)
            or find_course_by_keywords(catalog, grade, ["calculus", "bc"], exclude)
        )

    return None
