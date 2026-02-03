# src/rigor_selector.py
from typing import Dict, Any, List, Optional, Set

def is_ap(title: str) -> bool:
    return title.strip().startswith("AP ")

def is_hp(title: str) -> bool:
    return "(HP)" in title

def level(title: str) -> str:
    if is_ap(title):
        return "AP"
    if is_hp(title):
        return "HP"
    return "P"

def level_score(title: str) -> int:
    return {"P": 1, "HP": 2, "AP": 3}[level(title)]

def _matches_subject(title: str, subject: str) -> bool:
    t = title.lower()
    if subject == "english":
        return "english" in t
    if subject == "history":
        return any(k in t for k in ["world history", "u.s. history", "us history", "civics", "economics", "ethnic studies"])
    if subject == "science":
        return any(k in t for k in ["biology", "chemistry", "physics", "science"])
    return False

def _grade_allowed(info: Any, grade: int) -> bool:
    allowed = getattr(info, "allowed_grades", None)
    if allowed is None:
        return True
    return grade in allowed

def choose_course(
    catalog: Dict[str, Any],
    grade: int,
    subject: str,
    rigor_pref: str,
    exclude: Set[str],
    ap_used_this_grade: int,
    ap_cap_this_grade: int,
) -> Optional[str]:
    """
    rigor_pref: 'regular_only' | 'honors_ok' | 'maximize'
    """
    candidates: List[str] = []
    for title, info in catalog.items():
        if title in exclude:
            continue
        if not _grade_allowed(info, grade):
            continue
        if not _matches_subject(title, subject):
            continue
        candidates.append(title)

    if not candidates:
        return None

    # Enforce AP cap by filtering AP if cap reached
    if ap_cap_this_grade is not None and ap_used_this_grade >= ap_cap_this_grade:
        candidates = [c for c in candidates if not is_ap(c)]

    # Apply preference
    if rigor_pref == "regular_only":
        p = [c for c in candidates if level(c) == "P"]
        if p:
            candidates = p

    elif rigor_pref == "honors_ok":
        # Prefer HP, then P; avoid AP unless only option
        hp = [c for c in candidates if level(c) == "HP"]
        p = [c for c in candidates if level(c) == "P"]
        if hp:
            candidates = hp
        elif p:
            candidates = p
        # else leave AP-only candidates

    # 'maximize' (or unknown) => sort by highest rigor

    # Deterministic best pick
    candidates.sort(key=lambda x: (-level_score(x), x))
    return candidates[0]
