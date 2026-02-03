from __future__ import annotations

from typing import Dict, Any, List, Tuple, Optional


# ---------------------------
# Letter grade -> grade points
# ---------------------------
LETTER_POINTS = {
    "A": 4.0,
    "B": 3.0,
    "C": 2.0,
    "D": 1.0,
    "F": 0.0,
}


def _is_semester_title(title: str) -> bool:
    t = (title or "").lower()
    return "(sem" in t or " semester" in t


def _slot_to_courses_with_units(slot) -> List[Tuple[str, float]]:
    """
    Convert a plan slot into [(title, units)] where units are:
      - full year course: 1.0
      - semester course: 0.5
    Slot can be:
      - "Course Title"
      - ["Sem A", "Sem B"]  (each counts as 0.5)
    """
    if slot is None:
        return []

    if isinstance(slot, list):
        out = []
        for s in slot:
            if not s:
                continue
            out.append((s, 0.5))
        return out

    title = slot
    units = 0.5 if _is_semester_title(title) else 1.0
    return [(title, units)]


def _get_letter_for_course(title: str, gpa_cfg: Dict[str, Any]) -> str:
    """
    Parent-controlled grading inputs.
    Supports:
      gpa_cfg = {
        "default_letter": "A",
        "overrides": {
          "AP Calculus BC (HP)": "A",
          "Chemistry (P)": "B"
        }
      }
    """
    default_letter = (gpa_cfg or {}).get("default_letter", "A")
    overrides = (gpa_cfg or {}).get("overrides", {}) or {}
    letter = overrides.get(title, default_letter)
    letter = str(letter).strip().upper()
    return letter if letter in LETTER_POINTS else default_letter


def _ag_letter_from_catalog(title: str, catalog: Dict[str, Any]) -> Optional[str]:
    """
    Uses Foothill CSV A–G mapping already parsed into Course.ag_area (e.g. "B").
    Returns lowercase 'a'..'g' or None if not A–G.
    """
    c = catalog.get(title)
    if not c:
        return None
    area = getattr(c, "ag_area", None)
    if not area:
        return None
    return str(area).strip().lower()


def _is_uc_honors_eligible(title: str, catalog: Dict[str, Any], uc_cfg: Dict[str, Any]) -> bool:
    """
    UC "weighted" bonus applies to *UC-approved* honors/AP/IB courses (A–G only)
    in grades 10–11, but capped to 8 semesters total.

    We do not have the official UC-approved honors list here, so we approximate:
      - AP courses: "AP " in title
      - Honors/HP courses: "(HP)" in title
      - "Honors " in title
    If you later add an explicit per-course override list, plug it in here.

    uc_cfg supports:
      {
        "honors_keywords": ["(HP)", "AP ", "Honors "]
      }
    """
    # must be A–G
    if _ag_letter_from_catalog(title, catalog) is None:
        return False

    t = title or ""
    keys = (uc_cfg or {}).get("honors_keywords") or ["(HP)", "AP ", "Honors "]
    return any(k in t for k in keys)


def _compute_uc_unweighted(plan: Dict[str, Any],
                           catalog: Dict[str, Any],
                           gpa_cfg: Dict[str, Any],
                           grades_included: set[int]) -> Dict[str, Any]:
    """
    UC unweighted GPA = average of A–G course grade points.
    Uses only grades in grades_included (e.g., {9,10,11} or {10,11}).
    """
    included = []
    excluded = []

    total_points = 0.0
    total_units = 0.0

    for yr in plan.get("plan", []):
        grade = int(yr.get("grade"))
        if grade not in grades_included:
            continue

        for slot in yr.get("courses", []):
            for title, units in _slot_to_courses_with_units(slot):
                ag = _ag_letter_from_catalog(title, catalog)
                if ag is None:
                    excluded.append({"grade": grade, "course": title, "reason": "not a-g"})
                    continue

                letter = _get_letter_for_course(title, gpa_cfg)
                pts = LETTER_POINTS[letter]

                included.append({
                    "grade": grade,
                    "course": title,
                    "units": units,
                    "ag": ag,
                    "letter": letter,
                    "points": pts
                })

                total_points += pts * units
                total_units += units

    gpa = round(total_points / total_units, 3) if total_units > 0 else 0.0
    return {
        "gpa": gpa,
        "course_units": round(total_units, 3),
        "included": included,
        "excluded": excluded,
    }


def _compute_uc_weighted_capped_10_11(plan: Dict[str, Any],
                                      catalog: Dict[str, Any],
                                      gpa_cfg: Dict[str, Any],
                                      uc_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    UC Weighted & Capped GPA (10–11):
      - Start with UC unweighted (10–11) over A–G courses
      - Add +1.0 per *year* (or +0.5 per semester) for UC honors/AP (A–G) courses in 10–11
      - Cap bonus to 8 semesters total (4.0 points)

    Implementation:
      - Compute base (unweighted) GPA over A–G course-units
      - Compute bonus units for eligible courses, cap to 4.0 points
      - Weighted capped GPA = (base_points + bonus_points) / total_units
    """
    included = []
    excluded = []

    total_base_points = 0.0
    total_units = 0.0

    bonus_units_applied = 0.0  # each semester = 0.5, each full-year = 1.0
    bonus_courses_applied = []  # track course titles that got bonus

    max_bonus_semesters = float((uc_cfg or {}).get("max_bonus_semesters", 8))
    max_bonus_units = max_bonus_semesters * 0.5  # 8 semesters => 4.0 units => 4.0 points

    for yr in plan.get("plan", []):
        grade = int(yr.get("grade"))
        if grade not in {10, 11}:
            continue

        for slot in yr.get("courses", []):
            for title, units in _slot_to_courses_with_units(slot):
                ag = _ag_letter_from_catalog(title, catalog)
                if ag is None:
                    excluded.append({"grade": grade, "course": title, "reason": "not a-g"})
                    continue

                letter = _get_letter_for_course(title, gpa_cfg)
                pts = LETTER_POINTS[letter]

                # base
                total_base_points += pts * units
                total_units += units

                # bonus (capped)
                eligible = _is_uc_honors_eligible(title, catalog, uc_cfg)
                bonus_added = 0.0
                if eligible and bonus_units_applied < max_bonus_units:
                    # apply only remaining amount up to cap
                    remaining = max_bonus_units - bonus_units_applied
                    apply_units = min(units, remaining)
                    bonus_units_applied += apply_units
                    bonus_added = apply_units  # 1 unit => +1 point; 0.5 => +0.5 point
                    bonus_courses_applied.append({"grade": grade, "course": title, "bonus_units": apply_units})

                included.append({
                    "grade": grade,
                    "course": title,
                    "units": units,
                    "ag": ag,
                    "letter": letter,
                    "base_points": pts,
                    "honors_eligible": eligible,
                    "bonus_units_added": bonus_added,
                })

    base_gpa = (total_base_points / total_units) if total_units > 0 else 0.0
    bonus_points_total = bonus_units_applied  # 1 unit corresponds to +1.0 GPA point contribution per unit
    weighted_capped_gpa = ((total_base_points + bonus_points_total) / total_units) if total_units > 0 else 0.0

    return {
        "weighted_capped_gpa": round(weighted_capped_gpa, 3),
        "base_unweighted_gpa": round(base_gpa, 3),
        "bonus_points_total": round(bonus_points_total, 3),
        "bonus_units_applied": round(bonus_units_applied, 3),
        "bonus_courses_applied_count": len(bonus_courses_applied),
        "course_units": round(total_units, 3),
        "included": included,
        "excluded": excluded,
        "bonus_courses_applied": bonus_courses_applied,
    }


def compute_uc_gpas(plan: Dict[str, Any],
                    gpa_cfg: Dict[str, Any],
                    uc_cfg: Dict[str, Any],
                    catalog: Dict[str, Any],
                    debug: bool = False) -> Dict[str, Any]:
    """
    Main entry point used by main.py.

    Returns a dict that your main.py can print like:
      - UC Unweighted GPA (9-11)
      - UC Unweighted GPA (10-11)
      - UC Weighted & Capped GPA (10-11)
    """
    unweighted_9_11 = _compute_uc_unweighted(plan, catalog, gpa_cfg, grades_included={9, 10, 11})
    unweighted_10_11 = _compute_uc_unweighted(plan, catalog, gpa_cfg, grades_included={10, 11})
    weighted_capped_10_11 = _compute_uc_weighted_capped_10_11(plan, catalog, gpa_cfg, uc_cfg)

    if debug:
        print("[DEBUG UC] Included count (9-11):", len(unweighted_9_11["included"]),
              "Excluded:", len(unweighted_9_11["excluded"]))
        print("[DEBUG UC] Sample excluded (9-11):", unweighted_9_11["excluded"][:5])

        print("[DEBUG UC] Included count (10-11):", len(unweighted_10_11["included"]),
              "Excluded:", len(unweighted_10_11["excluded"]))
        print("[DEBUG UC] Sample excluded (10-11):", unweighted_10_11["excluded"][:5])

    return {
        "unweighted_9_11": {
            "gpa": unweighted_9_11["gpa"],
            "course_units": unweighted_9_11["course_units"],
            "included": unweighted_9_11["included"],
            "excluded": unweighted_9_11["excluded"],
        },
        "unweighted_10_11": {
            "gpa": unweighted_10_11["gpa"],
            "course_units": unweighted_10_11["course_units"],
            "included": unweighted_10_11["included"],
            "excluded": unweighted_10_11["excluded"],
        },
        "weighted_capped_10_11": weighted_capped_10_11,
    }
