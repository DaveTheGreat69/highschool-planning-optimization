import json
import os
from typing import Set

from src.catalog_parser import load_catalog
from src.skeleton_builder import build_empty_plan
from src.elective_picker import fill_electives
from src.validator import validate_no_backtracking, validate_plan_offered_by_grade
from src.rules_pusd import PREFERRED_TITLES
from src.report_print import print_uc_ag_report, print_pusd_report
from src.pusd_grad_audit import PUSD_CREDIT_REQ
from src.inputs_loader import load_inputs, resolve_completed_courses
from src.math_pathway import pick_math_for_grade
from src.science_pathway import pick_science_for_grade
from src.language_pathway import pick_spanish_for_grade
from src.ag_mapper import count_years_from_plan, ag_gaps
from src.rigor_report import rigor_summary
from src.optimizer_v1 import optimize_ag_gaps_v1
from src.pusd_grad_audit import audit_pusd_graduation
from src.gpa_calc import compute_hs_gpa
from src.rigor_selector import choose_course, is_ap
from src.uc_gpa_calc import compute_uc_gpas
from src.ag_mapper import (
    count_years_from_plan,
    ag_gaps,
    pretty_ag_counts,
    pretty_ag_gaps
)


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

def pick_history_with_rigor(catalog, grade, key_candidates, rigor_pref, exclude):
    """
    key_candidates: list of titles (include AP and non-AP variants)
    rigor_pref: regular_only | honors_ok | maximize
    """
    # filter to available
    avail = [t for t in key_candidates if t in catalog and grade in catalog[t].allowed_grades and t not in exclude]
    if not avail:
        return None

    def score(t):
        if t.startswith("AP "): return 3
        if "(HP)" in t: return 2
        return 1

    if rigor_pref == "regular_only":
        p = [t for t in avail if not t.startswith("AP ") and "(HP)" not in t]
        if p: avail = p
    elif rigor_pref == "honors_ok":
        # prefer (HP) then (P); avoid AP unless only option
        hp = [t for t in avail if "(HP)" in t and not t.startswith("AP ")]
        p = [t for t in avail if not t.startswith("AP ") and "(HP)" not in t]
        if hp: avail = hp
        elif p: avail = p

    avail.sort(key=lambda t: (-score(t), t))
    return avail[0]

def pick_english_for_grade(catalog, grade, prefer_honors, exclude):
    """
    Prefer exact Foothill titles first, then fallback to keyword search.
    """
    # Exact title preferences based on your Foothill CSV
    preferred_exact = {
        9:  ["Honors Freshman English (P)", "Freshman English (P)"],
        10: ["Honors Sophomore English (P)", "Sophomore English (P)"],
        11: ["AP English Language (HP)", "Honors Junior English (HP)", "Junior English (P)"],
        12: ["AP English Literature & Comp (HP)", "CSU Expository Reading & Writing (P)", "British Literature (P)"]
    }

    # If prefer_honors=False, flip priority for 9/10/11 (12 is usually choice-based anyway)
    if not prefer_honors:
        if grade in [9, 10]:
            preferred_exact[grade] = list(reversed(preferred_exact[grade]))
        if grade == 11:
            preferred_exact[grade] = ["Junior English (P)", "Honors Junior English (HP)", "AP English Language (HP)"]

    # Try exact first
    for t in preferred_exact.get(grade, []):
        if t in catalog and grade in catalog[t].allowed_grades and t not in exclude:
            return t

    # Fallback: any english course that matches grade
    for title, c in catalog.items():
        if grade in c.allowed_grades and "english" in title.lower() and title not in exclude:
            return title

    return None

def fill_core_slots(plan, catalog, starting_math, science_pathway, completed_courses, cfg, prefer_spanish=False):
    """
    Fill core slots using preferred Foothill titles when possible.
    Keeps 6 slots per grade.
    """
    used: Set[str] = set()
    rigor_preferences = rigor_preferences or {}
    max_ap_per_year = max_ap_per_year or {"9": 0, "10": 1, "11": 2, "12": 3}


    for year in plan["plan"]:
        g = year["grade"]
        ap_used_this_grade = 0
        #ap_cap = int(max_ap_per_year.get(str(g), max_ap_per_year.get(g, 0)))
        ap_cap = None
        
        slots = year["courses"]
        idx = 0

        # --- English ---
        prefer_honors = cfg.get("prefer_honors", {})
        prefer_honors_english = bool(prefer_honors.get("english", False))

        english = pick_english_for_grade(catalog, g, prefer_honors_english, used | completed_courses)
        if english:
            slots[idx] = english
            used.add(english)
            idx += 1
        print(f"[DEBUG] Chosen English for grade {g}: {english}")


        # --- Math (forced by starting_math progression) ---
        year_index = {9: 0, 10: 1, 11: 2, 12: 3}[g]

        m = pick_math_for_grade(catalog, g, starting_math, year_index, used | completed_courses)
        if m:
            slots[idx] = m; used.add(m); idx += 1

        # Science: keep your pathway logic first (it encodes sequencing),
        # but if you later add honors/AP variants, the pathway can be extended.
        sci = pick_science_for_grade(catalog, g, science_pathway, year_index, used | completed_courses)
        if not sci:
            sci_pref = rigor_preferences.get("science", "honors_ok")
            sci = choose_course(
                catalog=catalog,
                grade=g,
                subject="science",
                rigor_pref=sci_pref,
                exclude=(used | completed_courses),
                ap_used_this_grade=ap_used_this_grade,
                ap_cap_this_grade=ap_cap,
            )
        if sci and idx < 6:
            slots[idx] = sci
            used.add(sci)
            if is_ap(sci):
                ap_used_this_grade += 1
            idx += 1

        print(f"[DEBUG] Grade {g} AP used {ap_used_this_grade}/{ap_cap}")

        # Spanish (if preferred)
        if prefer_spanish:
            sp = pick_spanish_for_grade(catalog, g, completed_courses, year_index, used | completed_courses)
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
       
        def block_lower_spanish(completed_courses):
            text = " | ".join([str(c).lower() for c in completed_courses])
            blocked = set()
            if "spanish ii" in text or "spanish 2" in text:
                blocked.update(["Spanish I (P)", "Spanish II (P)"])
            if "spanish iii" in text or "spanish 3" in text:
                blocked.update(["Spanish I (P)", "Spanish II (P)", "Spanish III (P)"])
            if "spanish iv" in text or "spanish 4" in text:
                blocked.update(["Spanish I (P)", "Spanish II (P)", "Spanish III (P)", "Spanish IV (P)"])
            return blocked

        blocked = block_lower_spanish(completed_courses)

        electives = fill_electives(
            catalog=catalog,
            grade=g,
            num_slots=remaining,
            goal=plan["goal"],
            prefer_spanish=False,
            exclude=(used | completed_courses | blocked)
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

    # New math input handling
    math_cfg = cfg.get("math", {})
    highest_completed_math = math_cfg.get("highest_completed")
    prefer_honors_math = bool(math_cfg.get("prefer_honors", True))

    if highest_completed_math:
        from math_resolver import resolve_math_start_from_completed
        derived_math_start = resolve_math_start_from_completed(highest_completed_math, prefer_honors_math)
    else:
        # fallback to old input if UI not migrated yet
        derived_math_start = cfg.get("starting_math", "honors_geometry")
    
    # Load catalog before using it
    catalog = load_catalog("data/foothill_catalog.csv")
    print("[DEBUG] Freshman English ag_area:", catalog.get("Freshman English (P)").ag_area)
    print("[DEBUG] Algebra II ag_area:", catalog.get("Algebra II (P)").ag_area)
    print("[DEBUG] Biology ag_area:", catalog.get("Biology (P)").ag_area)
    print("[DEBUG] PE Course 1 ag_area:", catalog.get("PE Course 1-Freshmen").ag_area)

    completed_raw = cfg.get("completed_courses", [])
    completed_courses = resolve_completed_courses(catalog, completed_raw)

    print("Inputs:")
    print("  goal =", goal)
    print("  starting_math =", derived_math_start)
    print("  science_pathway =", science_pathway)
    print("  prefer_spanish =", prefer_spanish)
    print("Resolved completed courses:")
    for c in sorted(completed_courses):
        print(" -", c)

    plan = build_empty_plan(goal)
    rigor_preferences = cfg.get("rigor_preferences", {})
    max_ap_per_year = cfg.get("max_ap_per_year", {"9": 0, "10": 1, "11": 2, "12": 3})

    plan = fill_core_slots(
        plan, catalog,
        starting_math=derived_math_start,
        science_pathway=science_pathway,
        completed_courses=completed_courses,
        cfg=cfg,
        prefer_spanish=prefer_spanish
    )
    print("\n=== Initial Plan after filling core slots ===")


    # Validate offered-by-grade + existence
    errors = validate_no_backtracking(plan, completed_courses)
    if errors:
        print("\n=== Validation errors ===")
        for e in errors:
            print("-", e)
    else:
        print("\n✅ Plan passes Backtracking validation.")

    errors = validate_plan_offered_by_grade(plan, catalog)
    if errors:
        print("\n=== Validation errors ===")
        for e in errors:
            print("-", e)
    else:
        print("\n✅ Plan passes Phase 1 validation (exists + offered-by-grade).")

    # --- A–G audit ---
    ag_counts = count_years_from_plan(plan)
    gaps = ag_gaps(ag_counts)
    rigor = rigor_summary(plan)

    print_uc_ag_report(ag_counts, gaps, title="UC A–G audit (decoded)")
    print("\n=== Rigor summary ===")
    print(rigor)

    pusd = audit_pusd_graduation(plan)
    print_pusd_report(pusd, PUSD_CREDIT_REQ, title="PUSD graduation audit")

    if pusd["pusd_gaps"]:
        print("\n=== PUSD gaps ===")
        for g in pusd["pusd_gaps"]:
            print("-", g)
    else:
        print("\nNo PUSD graduation gaps found (heuristic).")

    # Save alongside other outputs
    with open("data/outputs/pusd_audit.json", "w", encoding="utf-8") as f:
        import json
        json.dump(pusd, f, indent=2)

    print("\nSaved PUSD audit to data/outputs/pusd_audit.json")

    # Build a global used set from current plan
    used_global = set()
    for yr in plan["plan"]:
        for slot in yr["courses"]:
            if isinstance(slot, list):
                for s in slot:
                    used_global.add(s)
            else:
                used_global.add(slot)

    # If there are gaps, try to optimize
    if gaps:
        print("\n=== Running Optimizer v1 to close A–G gaps ===")
        plan = optimize_ag_gaps_v1(plan, catalog, ag_counts, cfg, used_global)

        # Recompute audit after optimization
        ag_counts = count_years_from_plan(plan)
        gaps = ag_gaps(ag_counts)
        rigor = rigor_summary(plan)
        print_uc_ag_report(ag_counts, gaps, title="UC A–G audit AFTER optimization (decoded)")
        print("\n=== Rigor summary AFTER optimization ===")
        print(rigor)
        pusd = audit_pusd_graduation(plan)
        print_pusd_report(pusd, PUSD_CREDIT_REQ, title="PUSD graduation audit AFTER optimization")

    # --- GPA Calculation ---
    gpa_cfg = cfg.get("grades", {"by_level": {"P":"A","HP":"A","AP":"A"}, "overrides": {}})
    hs_gpa = compute_hs_gpa(plan, gpa_cfg)

    print("\n=== HS GPA (PUSD scale) ===")
    print("HS Unweighted GPA:", hs_gpa["hs_unweighted_gpa"])
    print("HS Weighted GPA  :", hs_gpa["hs_weighted_gpa"])
    print("Course count eqv :", hs_gpa["courses_count_equiv"])

    # UC GPA Calculation
    # --- UC GPA Calculation ---
    uc_cfg = cfg.get("uc_gpa", {})
    uc_gpas = compute_uc_gpas(plan, gpa_cfg=gpa_cfg, uc_cfg=uc_cfg, catalog=catalog, debug=True)

    print("[DEBUG] Freshman English ag_area:", getattr(catalog.get("Freshman English (P)"), "ag_area", None))
    print("[DEBUG] PE Course 1 ag_area:", getattr(catalog.get("PE Course 1-Freshmen"), "ag_area", None))

    print("\n=== UC GPA Summary (A–G only) ===")
    print(f"UC Unweighted GPA (9-11): {uc_gpas['unweighted_9_11']['gpa']} | course eqv: {uc_gpas['unweighted_9_11']['course_units']}")
    print(f"UC Unweighted GPA (10-11): {uc_gpas['unweighted_10_11']['gpa']} | course eqv: {uc_gpas['unweighted_10_11']['course_units']}")

    w = uc_gpas["weighted_capped_10_11"]
    print(f"\nUC Weighted & Capped GPA (10-11): {w['weighted_capped_gpa']}")
    print(f"  Base (unweighted) (10-11):      {w['base_unweighted_gpa']}")
    print(f"  Bonus points total:             {w['bonus_points_total']}")
    print(f"  Bonus courses applied:          {w['bonus_courses_applied_count']}")

    with open("data/outputs/uc_gpa.json", "w", encoding="utf-8") as f:
        json.dump(uc_gpas, f, indent=2)
    print("Saved UC GPA to data/outputs/uc_gpa.json")

    # Save as JSON artifact
    import json
    with open("data/outputs/hs_gpa.json", "w", encoding="utf-8") as f:
        json.dump(hs_gpa, f, indent=2)
    print("Saved HS GPA to data/outputs/hs_gpa.json")

    # Save audit as JSON alongside plan
    audit = {"ag_counts": ag_counts, "ag_gaps": gaps, "rigor": rigor}
    import os, json
    os.makedirs("data/outputs", exist_ok=True)
    with open("data/outputs/audit.json", "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2)
    print("\nSaved audit to data/outputs/audit.json")

    final_report = {
    "goal": goal,
    "uc_ag": {
        "counts": ag_counts,
        "gaps": gaps,
        "rigor": rigor,
    },
    "pusd_grad": pusd,
    "gpa": {
        "pusd_hs": {
            "unweighted": hs_gpa["hs_unweighted_gpa"],
            "weighted": hs_gpa["hs_weighted_gpa"]
        },
        "uc": uc_gpas
        }
    }

    with open("data/outputs/final_report.json", "w", encoding="utf-8") as f:
        import json
        json.dump(final_report, f, indent=2)

    print("\nSaved merged report to data/outputs/final_report.json")
    # Save output
    os.makedirs("data/outputs", exist_ok=True)
    out_path = os.path.join("data", "outputs", f"phase1_plan_{goal}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)

    print("Saved:", out_path)


if __name__ == "__main__":
    main()

