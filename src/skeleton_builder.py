from typing import Dict, Any, List
from rules_pusd import CORE_SLOTS


def build_empty_plan(goal: str) -> Dict[str, Any]:
    """
    6 slots per year (some slots are semester pairs but count as 1 slot).
    We keep plan["courses"] as list of 6 slots for Phase 1.
    """
    return {
        "goal": goal,
        "assumptions": [],
        "plan": [
            {"grade": 9, "courses": [None, None, None, None, None, None]},
            {"grade": 10, "courses": [None, None, None, None, None, None]},
            {"grade": 11, "courses": [None, None, None, None, None, None]},
            {"grade": 12, "courses": [None, None, None, None, None, None]},
        ],
        "rationale": [],
        "next_steps": [],
    }


def core_slot_count(grade: int) -> int:
    return len(CORE_SLOTS.get(grade, []))


def elective_slots_for_grade(grade: int) -> int:
    return 6 - core_slot_count(grade)
