from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from fastapi.middleware.cors import CORSMiddleware

from src.catalog_parser import load_catalog
from src.skeleton_builder import build_empty_plan
from src.validator import validate_no_backtracking, validate_plan_offered_by_grade
from src.inputs_loader import resolve_completed_courses
from src.elective_picker import fill_electives
from src.rules_pusd import PREFERRED_TITLES
from src.pusd_grad_audit import audit_pusd_graduation
from src.ag_mapper import count_years_from_plan, ag_gaps
from src.rigor_report import rigor_summary
from src.optimizer_v1 import optimize_ag_gaps_v1
from src.gpa_calc import compute_hs_gpa
from src.uc_gpa_calc import compute_uc_gpas

from src.math_pathway import pick_math_for_grade
from src.science_pathway import pick_science_for_grade
from src.language_pathway import pick_spanish_for_grade
from src.english_pathway import pick_english_for_grade


app = FastAPI(title="High School Planning Optimizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later restrict to your web URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------
# Inputs schema
# -------------------------
class Inputs(BaseModel):
    catalog_path: str = "data/foothill_catalog.csv"
    goal: str = "cs"  # cs | pre_med | biotech

    # D) new: completed_math (preferred), keep starting_math for backward compat
    completed_math: Optional[str] = None
    starting_math: str = "honors_algebra2"  # fallback only

    science_pathway: str = "standard_stem"
    prefer_spanish: bool = True
    completed_courses: List[str] = []

    gpa: Dict[str, Any] = {"default_letter": "A", "overrides": {}}
    uc_cfg: Dict[str, Any] = {
        "max_bonus_semesters": 8,
        "honors_keywords": ["(HP)", "AP ", "Honors "],
    }

    # C) new: course level prefs (regular|honors|ap)
    course_level_prefs: Dict[str, str] = {
        "english": "regular",
        "history": "regular",
        "science": "regular",
    }
    
    # NEW:
    english_level: str = "regular"   # regular | honors | auto
    starting_math: str = "auto"      # auto | honors_geometry | algebra2 | honors_algebra2



# -------------------------
# Small helpers (C)
# -------------------------
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


def _first_match_by_keywords(catalog, grade: int, keywords: List[str], exclude: set) -> Optional[str]:
    kw = [k.lower() for k in keywords]
    for title, c in catalog.items():
        if title in exclude:
            continue
        if grade not in c.allowed_grades:
            continue
        tl = title.lower()
        if all(k in tl for k in kw):
            return title
    return None


def pick_english_for_grade(catalog, grade: int, level_pref: str, exclude: set) -> Optional[str]:
    """
    level_pref: regular|honors|ap
    Exact-title first, then keyword fallbacks.
    """
    level_pref = (level_pref or "regular").lower()

    # Exact titles by grade
    exact = {
        9: {
            "regular": ["Freshman English (P)"],
            "honors":  ["Honors Freshman English (P)"],
            "ap":      [],  # none in 9
        },
        10: {
            "regular": ["Sophomore English (P)"],
            "honors":  ["Honors Sophomore English (P)"],
            "ap":      [],  # none in 10 per your CSV
        },
        11: {
            "regular": ["Junior English (P)"],
            "honors":  ["Honors Junior English (HP)"],
            "ap":      ["AP English Language (HP)"],
        },
        12: {
            # There isn't an explicit "Honors Senior English" in your CSV; AP Lit is the rigorous option.
            "regular": ["British Literature (P)", "CSU Expository Reading & Writing (P)"],
            "honors":  [],  # will fall back to regular (unless you want honors->AP behavior)
            "ap":      ["AP English Literature & Comp (HP)"],
        },
    }

    # Try exact, respecting preference + safe fallbacks:
    # ap -> ap -> honors -> regular
    # honors -> honors -> regular
    # regular -> regular
    order = []
    if level_pref == "ap":
        order = ["ap", "honors", "regular"]
    elif level_pref == "honors":
        order = ["honors", "regular"]
    else:
        order = ["regular"]

    for lvl in order:
        for t in exact.get(grade, {}).get(lvl, []):
            if t in catalog and grade in catalog[t].allowed_grades and t not in exclude:
                return t

    # keyword fallback (very conservative)
    if level_pref == "ap":
        cand = _first_match_by_keywords(catalog, grade, ["ap", "english"], exclude)
        if cand:
            return cand
        cand = _first_match_by_keywords(catalog, grade, ["honors", "english"], exclude)
        if cand:
            return cand

    if level_pref == "honors":
        cand = _first_match_by_keywords(catalog, grade, ["honors", "english"], exclude)
        if cand:
            return cand

    return _first_match_by_keywords(catalog, grade, ["english"], exclude)


def pick_history_for_grade(catalog, grade: int, level_pref: str, exclude: set) -> Optional[str] | List[str]:
    """
    Handles:
      grade 10 World
      grade 11 US
      grade 12 Civics + Econ (semester pair)
    Returns either a string course title or a [a,b] semester-pair list for grade 12.
    """
    level_pref = (level_pref or "regular").lower()

    # Grade 10 World History
    if grade == 10:
        if level_pref == "ap":
            t = choose_preferred(["AP World History (HP)"], catalog, grade, exclude)
            if t:
                return t
            # fallback honors then regular
            t = choose_preferred(["Honors World History (P)"], catalog, grade, exclude)
            if t:
                return t
            return choose_preferred(["World History (P)"], catalog, grade, exclude)

        if level_pref == "honors":
            t = choose_preferred(["Honors World History (P)"], catalog, grade, exclude)
            if t:
                return t
            return choose_preferred(["World History (P)"], catalog, grade, exclude)

        return choose_preferred(["World History (P)"], catalog, grade, exclude)

    # Grade 11 US History
    if grade == 11:
        if level_pref == "ap":
            t = choose_preferred(["AP U.S. History (HP)"], catalog, grade, exclude)
            if t:
                return t
            return choose_preferred(["U.S. History (P)"], catalog, grade, exclude)

        return choose_preferred(["U.S. History (P)", "AP U.S. History (HP)"], catalog, grade, exclude)

    # Grade 12 Civics + Econ (pair)
    if grade == 12:
        if level_pref == "ap":
            # AP Gov (A) + AP Macro (G) is a solid rigorous pair
            pair = choose_semester_pair(
                [("AP Govt & Politics (HP) (sem)", "AP Macroeconomics (HP) (sem)")],
                catalog,
                grade,
                exclude,
            )
            if pair:
                return pair

        # honors doesn't really exist here besides APs; keep safe default
        pair = choose_semester_pair(
            [
                ("Civics (P) (sem)", "Economics (P) (sem)"),
                ("Civics (P) (sem)", "AP Macroeconomics (HP) (sem)"),
            ],
            catalog,
            grade,
            exclude,
        )
        return pair

    return None


# -------------------------
# Core slot fill (EDIT ONLY ENGLISH/HISTORY/MATH wiring)
# -------------------------
def fill_core_slots(plan, catalog, inputs: Inputs, completed_courses: set):
    used = set()

    prefs = inputs.course_level_prefs or {}
    english_pref = (prefs.get("english") or "regular").lower()
    history_pref = (prefs.get("history") or "regular").lower()

    for year in plan["plan"]:
        g = year["grade"]
        slots = year["courses"]
        idx = 0
        year_index = {9: 0, 10: 1, 11: 2, 12: 3}[g]

        # ---- ENGLISH (C) ----
        eng = pick_english_for_grade(catalog, g, english_pref, used | completed_courses)
        if eng and idx < 6:
            slots[idx] = eng
            used.add(eng)
            idx += 1

        # ---- MATH (D) ----
        m = pick_math_for_grade(
            catalog=catalog,
            grade=g,
            year_index=year_index,
            exclude=(used | completed_courses),
            completed_math=inputs.completed_math,
            starting_math=inputs.starting_math,  # fallback only
        )
        if m and idx < 6:
            slots[idx] = m
            used.add(m)
            idx += 1

        # ---- SCIENCE (unchanged) ----
        sci = pick_science_for_grade(
            catalog, g, inputs.science_pathway, year_index, used | completed_courses
        )
        if sci and idx < 6:
            slots[idx] = sci
            used.add(sci)
            idx += 1

        # ---- Spanish (unchanged) ----
        if inputs.prefer_spanish:
            sp = pick_spanish_for_grade(catalog, g, completed_courses, year_index, used | completed_courses)
            if sp:
                for i in range(6):
                    if slots[i] is None:
                        slots[i] = sp
                        used.add(sp)
                        break

        # ---- HISTORY / SOCIAL SCIENCE (C) ----
        if g in (10, 11, 12):
            hx = pick_history_for_grade(catalog, g, history_pref, used | completed_courses)
            if hx and idx < 6:
                slots[idx] = hx
                if isinstance(hx, list):
                    used.update(hx)
                else:
                    used.add(hx)
                idx += 1

        # Grade-specific cores that are NOT history:
        if g == 9:
            pair = choose_semester_pair(PREFERRED_TITLES["g9_ethnic_health_pair"], catalog, g, used)
            if pair and idx < 6:
                slots[idx] = pair
                used.update(pair)
                idx += 1

            pe = choose_preferred(PREFERRED_TITLES["g9_pe"], catalog, g, used)
            if pe and idx < 6:
                slots[idx] = pe
                used.add(pe)
                idx += 1

        elif g == 10:
            # PE Course 2 unchanged
            pe2 = None
            for title, c in catalog.items():
                if g in c.allowed_grades and title.lower().startswith("pe course 2"):
                    pe2 = title
                    break
            if pe2 and idx < 6:
                slots[idx] = pe2
                used.add(pe2)
                idx += 1

        # Fill remaining electives unchanged
        remaining = sum(1 for s in slots if s is None)
        electives = fill_electives(
            catalog=catalog,
            grade=g,
            num_slots=remaining,
            goal=plan["goal"],
            prefer_spanish=False,
            exclude=(used | completed_courses),
        )
        for i in range(6):
            if slots[i] is None and electives:
                chosen = electives.pop(0)
                slots[i] = chosen
                used.add(chosen)

    return plan


# -------------------------
# Endpoints
# -------------------------
@app.get("/")
def root():
    return {"ok": True, "service": "highschool-planning-optimizer"}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/generate")
def generate(inputs: Inputs):
    catalog = load_catalog(inputs.catalog_path)
    completed = resolve_completed_courses(catalog, inputs.completed_courses)

    plan = build_empty_plan(inputs.goal)
    plan = fill_core_slots(plan=plan, catalog=catalog, inputs=inputs, completed_courses=completed)

    # validations
    backtracking_errors = validate_no_backtracking(plan, completed)
    offered_errors = validate_plan_offered_by_grade(plan, catalog)

    # audits
    ag_counts = count_years_from_plan(plan)
    gaps = ag_gaps(ag_counts)
    pusd = audit_pusd_graduation(plan)
    rigor = rigor_summary(plan)

    # global used set (for optimizer)
    used_global = set()
    for yr in plan["plan"]:
        for slot in yr["courses"]:
            if isinstance(slot, list):
                used_global.update(slot)
            else:
                used_global.add(slot)

    # optimizer closes A–G gaps
    if gaps:
        plan = optimize_ag_gaps_v1(plan, catalog, ag_counts, inputs.model_dump(), used_global)
        ag_counts = count_years_from_plan(plan)
        gaps = ag_gaps(ag_counts)
        pusd = audit_pusd_graduation(plan)
        rigor = rigor_summary(plan)

    # GPAs
    hs_gpa = compute_hs_gpa(plan, inputs.gpa)
    uc_gpa = compute_uc_gpas(plan, inputs.gpa, inputs.uc_cfg, catalog, debug=False)

    return {
        "inputs": inputs.model_dump(),
        "plan": plan,
        "validation": {
            "backtracking_errors": backtracking_errors,
            "offered_by_grade_errors": offered_errors,
        },
        "uc_ag": {"counts": ag_counts, "gaps": gaps, "rigor": rigor},
        "pusd_grad": pusd,
        "hs_gpa": hs_gpa,
        "uc_gpa": uc_gpa,
    }
