import json
import os
from typing import Set

from catalog_parser import load_catalog
from skeleton_builder import build_empty_plan
from elective_picker import fill_electives
from validator import validate_plan_offered_by_grade
from rules_pusd import PREFERRED_TITLES

from inputs_loader import load_inputs, resolve_completed_courses
from math_pathway import pick_math_for_grade
from science_pathway import pick_science_for_grade
from language_pathway import pick_spanish_for_grade

def load_inputs(path="data/inputs.json") -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def choose_preferred(title_candidates, catalog, grade, exclude):
    for t in title_candidates:
        if t in catalog and grade in catalog[t].allowed_grades and t not in exclude:
            return t
    return None


def choose_semester_pair(pair_candidates, catalog, grade, exclude):
    for a, b in pair_candidates:
        if a in catalog and b in catalog and grade in catalog[a].allowed_grades and grade in catalog[b].allowed_grades:
            if a not in exclude and b not in exclude:
                return [a, b]
    return None


def fill_core_slots(plan, catalog, starting_math, science_pathway, completed_courses, prefer_spanish=False):
    """
    Fill core slots using preferred Foothill titles when possible.
    Keeps 6 slots per grade.
    """
    used: Set[str] = set()

    for year in plan["plan"]:
        g = year["grade"]
        slots = year["courses"]
        idx = 0

        # English (best-effort: pick first course with "English" in title for that grade)
        english = None
        for title, c in catalog.items():
            if g in c.allowed_grades and "english" in title.lower():
                english = title
                break
        if english:
            slots[idx] = english; used.add(english); idx += 1

        # --- Math (forced by starting_math progression) ---
        year_index = {9: 0, 10: 1, 11: 2, 12: 3}[g]

        m = pick_math_for_grade(catalog, g, starting_math, year_index, used | completed_courses)
        if m:
            slots[idx] = m; used.add(m); idx += 1

        sci = pick_science_for_grade(catalog, g, science_pathway, year_index, used | completed_courses)
        if sci and idx < 6:
            slots[idx] = sci; used.add(sci); idx += 1

        if prefer_spanish:
            sp = pick_spanish_for_grade(catalog, g, completed_courses, used | completed_courses)
            if sp:
                for i in range(6):
                    if slots[i] is None:
                        slots[i] = sp
                        used.add(sp)
                        break

        # Grade-specific cores
        if g == 9:
            # Ethnic/Health semester pair preferred
            pair = choose_semester_pair(PREFERRED_TITLES["g9_ethnic_health_pair"], catalog, g, used)
            if pair:
                slots[idx] = pair; used.update(pair); idx += 1

            pe = choose_preferred(PREFERRED_TITLES["g9_pe"], catalog, g, used)
            if pe:
                slots[idx] = pe; used.add(pe); idx += 1

        elif g == 10:
            wh = choose_preferred(PREFERRED_TITLES["g10_world"], catalog, g, used)
            if wh:
                slots[idx] = wh; used.add(wh); idx += 1

            # PE Course 2 (best effort: any course with "PE Course 2" prefix)
            pe2 = None
            for title, c in catalog.items():
                if g in c.allowed_grades and title.lower().startswith("pe course 2"):
                    pe2 = title
                    break
            if pe2:
                slots[idx] = pe2; used.add(pe2); idx += 1

        elif g == 11:
            us = choose_preferred(PREFERRED_TITLES["g11_us"], catalog, g, used)
            if us:
                slots[idx] = us; used.add(us); idx += 1

        elif g == 12:
            pair = choose_semester_pair(PREFERRED_TITLES["g12_civics_econ_pair"], catalog, g, used)
            if pair:
                slots[idx] = pair; used.update(pair); idx += 1

        # Fill remaining slots as electives deterministically
        remaining = sum(1 for s in slots if s is None)
        electives = fill_electives(
            catalog=catalog,
            grade=g,
            num_slots=remaining,
            goal=plan["goal"],
            prefer_spanish=prefer_spanish,
            exclude=used | completed_courses,   # ✅ IMPORTANT
        )

        for i in range(6):
            if slots[i] is None and electives:
                chosen = electives.pop(0)
                slots[i] = chosen
                used.add(chosen)

    return plan

def main():
    # --- Inputs (Phase 1) ---
    cfg = load_inputs()
    goal = cfg.get("goal", "cs")
    starting_math = cfg.get("starting_math", "honors_geometry")
    science_pathway = cfg.get("science_pathway", "standard_stem")
    prefer_spanish = bool(cfg.get("prefer_spanish", True))

    # Load catalog before using it
    catalog = load_catalog("data/foothill_catalog.csv")

    completed_raw = cfg.get("completed_courses", [])
    completed_courses = resolve_completed_courses(catalog, completed_raw)

    print("Inputs:")
    print("  goal =", goal)
    print("  starting_math =", starting_math)
    print("  science_pathway =", science_pathway)
    print("  prefer_spanish =", prefer_spanish)
    print("Resolved completed courses:")
    for c in sorted(completed_courses):
        print(" -", c)

    plan = build_empty_plan(goal)
    plan = fill_core_slots(
    plan, catalog,
    starting_math=starting_math,
    science_pathway=science_pathway,
    completed_courses=completed_courses,
    prefer_spanish=prefer_spanish
    )

    # Validate offered-by-grade + existence
    errors = validate_plan_offered_by_grade(plan, catalog)
    if errors:
        print("\n=== Validation errors ===")
        for e in errors:
            print("-", e)
    else:
        print("\n✅ Plan passes Phase 1 validation (exists + offered-by-grade).")

    # Save output
    os.makedirs("data/outputs", exist_ok=True)
    out_path = os.path.join("data", "outputs", f"phase1_plan_{goal}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)

    print("Saved:", out_path)


if __name__ == "__main__":
    main()
