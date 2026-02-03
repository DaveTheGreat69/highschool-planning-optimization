# src/optimizer_v1.py
from __future__ import annotations

from typing import Any, Dict, Set, Tuple, Optional

from src.math_pathway import find_course_by_keywords


def _first_open_slot_idx(courses) -> Optional[int]:
    for i, s in enumerate(courses):
        if s is None:
            return i
    return None


def _try_add_course(plan, grade: int, title: str, used: Set[str]) -> bool:
    """
    Adds title into the first open slot of the given grade year, if possible.
    """
    for yr in plan["plan"]:
        if yr["grade"] != grade:
            continue
        idx = _first_open_slot_idx(yr["courses"])
        if idx is None:
            return False
        yr["courses"][idx] = title
        used.add(title)
        return True
    return False


def optimize_ag_gaps_v1(
    plan: Dict[str, Any],
    catalog: Dict[str, Any],
    ag_counts: Dict[str, float],
    cfg: Dict[str, Any],
    used_global: Set[str],
) -> Dict[str, Any]:
    """
    Very small heuristic optimizer:
      - If World Language (e) missing: add Spanish III / ASL I / French I, etc. in a free slot
      - If VPA (f) missing: add Art 1 / Drama 1 / etc. in a free slot
      - If College-prep elective (g) missing: add an Area G course
    This is not meant to be perfect — just closes common gaps.
    """
    # Your ag_mapper uses keys: a,b,c,d,e,f,g
    missing_e = ag_counts.get("e", 0.0) < 2.0
    missing_f = ag_counts.get("f", 0.0) < 1.0
    missing_g = ag_counts.get("g", 0.0) < 1.0

    # Try to place missing items in grades 10-12 first (often have more flexibility)
    grades_to_try = [10, 11, 12, 9]

    for g in grades_to_try:
        if missing_e:
            # Prefer continuing Spanish if user said prefer_spanish or completed Spanish II
            prefer_spanish = bool(cfg.get("prefer_spanish", False))
            completed = " | ".join([c.lower() for c in cfg.get("completed_courses", [])])

            wl_title = None
            if prefer_spanish or ("spanish ii" in completed or "spanish 2" in completed):
                wl_title = find_course_by_keywords(catalog, g, ["spanish", "iii"], used_global, prefer_honors=False) \
                    or find_course_by_keywords(catalog, g, ["ap", "spanish"], used_global, prefer_honors=True)
            if not wl_title:
                # fallback: any WL area (E) course keywords
                wl_title = (
                    find_course_by_keywords(catalog, g, ["american", "sign", "language"], used_global, prefer_honors=False)
                    or find_course_by_keywords(catalog, g, ["french", "i"], used_global, prefer_honors=False)
                    or find_course_by_keywords(catalog, g, ["japanese", "i"], used_global, prefer_honors=False)
                )

            if wl_title and _try_add_course(plan, g, wl_title, used_global):
                missing_e = False

        if missing_f:
            vpa_title = (
                find_course_by_keywords(catalog, g, ["art", "1"], used_global, prefer_honors=False)
                or find_course_by_keywords(catalog, g, ["drama", "1"], used_global, prefer_honors=False)
                or find_course_by_keywords(catalog, g, ["photography", "1"], used_global, prefer_honors=False)
                or find_course_by_keywords(catalog, g, ["concert", "choir"], used_global, prefer_honors=False)
            )
            if vpa_title and _try_add_course(plan, g, vpa_title, used_global):
                missing_f = False

        if missing_g:
            g_title = (
                find_course_by_keywords(catalog, g, ["debate"], used_global, prefer_honors=False)
                or find_course_by_keywords(catalog, g, ["student", "leadership"], used_global, prefer_honors=False)
                or find_course_by_keywords(catalog, g, ["psychology"], used_global, prefer_honors=True)
                or find_course_by_keywords(catalog, g, ["ap", "psychology"], used_global, prefer_honors=True)
            )
            if g_title and _try_add_course(plan, g, g_title, used_global):
                missing_g = False

    return plan
