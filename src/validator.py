from typing import Any, Dict, List
from catalog_parser import Course


def validate_plan_offered_by_grade(plan_json: Dict[str, Any], catalog: Dict[str, Course]) -> List[str]:
    errors: List[str] = []

    for year in plan_json.get("plan", []):
        grade = year["grade"]
        courses = year["courses"]
        if len(courses) != 6:
            errors.append(f"Grade {grade}: expected 6 slots, found {len(courses)}")

        for slot in courses:
            if slot is None:
                errors.append(f"Grade {grade}: has empty slot (None)")
                continue

            titles = slot if isinstance(slot, list) else [slot]
            for t in titles:
                if t not in catalog:
                    errors.append(f"Grade {grade}: course not found in catalog: '{t}'")
                else:
                    if grade not in catalog[t].allowed_grades:
                        errors.append(f"Grade {grade}: course '{t}' not offered in grade {grade}")

    return errors
