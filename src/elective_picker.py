from typing import Dict, List, Set, Optional
from catalog_parser import Course
from utils import contains_any


def pick_course_by_keywords(
    catalog: Dict[str, Course],
    grade: int,
    keywords: List[str],
    exclude: Set[str],
) -> Optional[str]:
    """
    Return the first course title matching keywords and grade.
    """
    for title, c in catalog.items():
        if title in exclude:
            continue
        if grade not in c.allowed_grades:
            continue
        if contains_any(title, keywords) or contains_any(c.subject_section, keywords):
            return title
    return None


def fill_electives(
    catalog: Dict[str, Course],
    grade: int,
    num_slots: int,
    goal: str,
    prefer_spanish: bool,
    exclude: Set[str],
) -> List[str]:
    chosen: List[str] = []

    # Priority 1: Spanish sequence if requested
    if prefer_spanish and num_slots > 0:
        for kw in [["spanish 3"], ["spanish 4"], ["spanish 5"], ["spanish"]]:
            if len(chosen) >= num_slots:
                break
            t = pick_course_by_keywords(catalog, grade, kw, exclude | set(chosen))
            if t:
                chosen.append(t)

    # Priority 2: CS/CTE electives for CS goal
    if goal == "cs" and len(chosen) < num_slots:
        cs_keywords = [
            ["computer science"],
            ["programming"],
            ["ap computer"],
            ["data structures"],
            ["robotics"],
            ["engineering"],
            ["ct", "cte"],  # sometimes appears in notes/sections
        ]
        for kw in cs_keywords:
            if len(chosen) >= num_slots:
                break
            t = pick_course_by_keywords(catalog, grade, kw, exclude | set(chosen))
            if t:
                chosen.append(t)

    # Fill remaining with anything offered in grade (last resort)
    for title, c in catalog.items():
        if len(chosen) >= num_slots:
            break
        if title in exclude or title in chosen:
            continue
        if grade not in c.allowed_grades:
            continue
        chosen.append(title)

    return chosen
