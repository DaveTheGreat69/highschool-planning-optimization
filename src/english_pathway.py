# src/english_pathway.py
from typing import Dict, Optional, Set, List

def _norm(s: str) -> str:
    return (s or "").strip().lower()

def contains_all(title: str, keywords: List[str]) -> bool:
    t = _norm(title)
    return all(_norm(k) in t for k in keywords)

def pick_english_for_grade(
    catalog: Dict[str, any],
    grade: int,
    english_level: str,   # "regular" | "honors" | "auto"
    exclude: Set[str],
) -> Optional[str]:
    """
    Picks an English course for the grade.

    - regular: Freshman English / Sophomore English / Junior English / British Lit etc
    - honors: Honors Freshman English / Honors Sophomore English / Honors Junior English / AP English where appropriate
    - auto: try honors if available, else regular
    """

    def find(keywords: List[str]):
        candidates = []
        for title, c in catalog.items():
            if title in exclude:
                continue
            if grade not in c.allowed_grades:
                continue
            if contains_all(title, keywords):
                candidates.append(title)
        candidates.sort()
        return candidates[0] if candidates else None

    # Grade naming patterns in your Foothill CSV:
    # 9: Freshman English / Honors Freshman English
    # 10: Sophomore English / Honors Sophomore English
    # 11: Junior English / Honors Junior English / AP English Language
    # 12: British Literature / AP English Literature & Comp / CSU ERWC

    if grade == 9:
        if english_level in ("honors", "auto"):
            return find(["honors", "freshman", "english"]) or find(["honors", "english"])
        return find(["freshman", "english"]) or find(["english"])

    if grade == 10:
        if english_level in ("honors", "auto"):
            return find(["honors", "sophomore", "english"]) or find(["honors", "english"])
        return find(["sophomore", "english"]) or find(["english"])

    if grade == 11:
        if english_level in ("honors", "auto"):
            # Prefer AP English Language if available
            return (
                find(["ap", "english", "language"])
                or find(["honors", "junior", "english"])
                or find(["honors", "english"])
            )
        return find(["junior", "english"]) or find(["english"])

    if grade == 12:
        if english_level in ("honors", "auto"):
            # Prefer AP Lit
            return find(["ap", "english", "literature"]) or find(["ap", "english", "lit"])
        # Regular-ish options
        return find(["british", "literature"]) or find(["csu", "expository"]) or find(["english"])

    return None
