# src/gpa_calc.py

from dataclasses import dataclass
from typing import Dict, Any, List, Tuple

# PUSD School Profile scale:
# A+/A/A- = 4.0, B+/B/B- = 3.0, C+/C/C- = 2.0, D+/D/D- = 1.0, F = 0.0
# Weighted courses (AP and some honors designated (HP)): A=5, B=4, C=3
# Source: Amador Valley School Profile (PUSD) :contentReference[oaicite:3]{index=3}

LETTER_TO_BAND = {
    "A+": "A", "A": "A", "A-": "A",
    "B+": "B", "B": "B", "B-": "B",
    "C+": "C", "C": "C", "C-": "C",
    "D+": "D", "D": "D", "D-": "D",
    "F": "F",
}

UNWEIGHTED_POINTS = {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}

# Weighted A/B/C are +1 (A=5, B=4, C=3); D/F remain 1/0 typically.
def weighted_points_from_band(band: str) -> float:
    base = UNWEIGHTED_POINTS[band]
    if band in ("A", "B", "C"):
        return base + 1.0
    return base


def is_semester_pair(slot: Any) -> bool:
    return isinstance(slot, list) and len(slot) == 2


def course_is_weighted(title: str) -> bool:
    t = title.strip()
    return t.startswith("AP ") or "(HP)" in t


def normalize_letter(letter: str) -> str:
    l = letter.strip().upper()
    if l not in LETTER_TO_BAND:
        raise ValueError(f"Unsupported letter grade: {letter}")
    return LETTER_TO_BAND[l]


def points_for_course(letter: str, weighted: bool) -> float:
    band = normalize_letter(letter)
    if weighted:
        return weighted_points_from_band(band)
    return UNWEIGHTED_POINTS[band]


def infer_level(title: str) -> str:
    t = title.strip()
    if t.startswith("AP "):
        return "AP"
    if "(HP)" in t:
        return "HP"
    return "P"

def build_gradebook(plan_json: dict, gpa_cfg: dict) -> Dict[str, str]:
    """
    New format:
      gpa_cfg = {
        "by_level": {"P":"A","HP":"A-","AP":"B+"},
        "overrides": {"Course Title":"B", ...}
      }
    """
    by_level = (gpa_cfg.get("by_level") or {"P":"A","HP":"A","AP":"A"})
    overrides = (gpa_cfg.get("overrides") or {})

    gradebook = {}
    for year in plan_json["plan"]:
        for slot in year["courses"]:
            titles = slot if is_semester_pair(slot) else [slot]
            for t in titles:
                if t in overrides:
                    gradebook[t] = overrides[t]
                else:
                    lvl = infer_level(t)
                    gradebook[t] = by_level.get(lvl, "A")
    return gradebook



def compute_hs_gpa(plan_json: dict, gpa_cfg: dict) -> dict:
    """
    Computes HS GPA on the PUSD scale from the plan's courses.
    - Uses plan courses only (grades 9-12).
    - Does NOT include 'completed courses' outside HS plan (e.g., middle school),
      matching PUSD profile statement that MS HS-level courses are not calculated into GPA. :contentReference[oaicite:4]{index=4}
    """
    include_grade9 = bool(gpa_cfg.get("include_grade9_in_hs_gpa", True))

    gradebook = build_gradebook(plan_json, gpa_cfg)

    total_points_unw = 0.0
    total_points_w = 0.0
    total_courses_equiv = 0.0  # full-year=1, each semester=0.5

    breakdown = []  # useful for debugging / later UI

    for year in plan_json["plan"]:
        grade = year["grade"]
        if grade == 9 and not include_grade9:
            continue

        for slot in year["courses"]:
            if is_semester_pair(slot):
                # each semester counts as 0.5 course
                for t in slot:
                    letter = gradebook[t]
                    w = course_is_weighted(t)
                    p_unw = points_for_course(letter, weighted=False)
                    p_w = points_for_course(letter, weighted=w)

                    total_points_unw += 0.5 * p_unw
                    total_points_w += 0.5 * p_w
                    total_courses_equiv += 0.5

                    breakdown.append({
                        "grade": grade,
                        "course": t,
                        "letter": letter,
                        "weighted_course": w,
                        "points_unweighted": p_unw,
                        "points_weighted": p_w,
                        "course_weight": 0.5
                    })
            else:
                t = slot
                letter = gradebook[t]
                w = course_is_weighted(t)
                p_unw = points_for_course(letter, weighted=False)
                p_w = points_for_course(letter, weighted=w)

                total_points_unw += p_unw
                total_points_w += p_w
                total_courses_equiv += 1.0

                breakdown.append({
                    "grade": grade,
                    "course": t,
                    "letter": letter,
                    "weighted_course": w,
                    "points_unweighted": p_unw,
                    "points_weighted": p_w,
                    "course_weight": 1.0
                })

    unweighted_gpa = (total_points_unw / total_courses_equiv) if total_courses_equiv else 0.0
    weighted_gpa = (total_points_w / total_courses_equiv) if total_courses_equiv else 0.0

    return {
        "hs_unweighted_gpa": round(unweighted_gpa, 3),
        "hs_weighted_gpa": round(weighted_gpa, 3),
        "courses_count_equiv": round(total_courses_equiv, 2),
        "assumptions": [
            "PUSD profile scale: A(+/-)=4, B(+/-)=3, C(+/-)=2, D(+/-)=1, F=0.",
            "Weighted courses: AP and courses designated (HP) get +1 for A/B/C (A=5, B=4, C=3).",
            "Only plan courses (grades 9–12) are included; completed middle school HS-level courses are excluded from GPA."
        ],
        "breakdown": breakdown,
    }
