import re

# Basic A–G categories
AG = ["a", "b", "c", "d", "e", "f", "g"]

AG_DECODE = {
    "a": "History / Social Science",
    "b": "English",
    "c": "Mathematics",
    "d": "Laboratory Science",
    "e": "World Language",
    "f": "Visual & Performing Arts",
    "g": "College-Prep Elective",
}


def infer_ag_category(course_title: str) -> str | None:
    """
    Heuristic mapping from title -> UC A–G category.
    You can refine this over time (or replace with explicit mapping file later).
    """
    t = course_title.lower()

    # a: history / social science
    if any(k in t for k in ["world history", "u.s. history", "us history", "civics", "economics", "government", "ethnic studies"]):
        return "a"

    # b: english
    if "english" in t or "literature" in t or "comp" in t:
        return "b"

    # c: math
    if any(k in t for k in ["algebra", "geometry", "pre-cal", "precal", "calculus", "statistics", "math"]):
        return "c"

    # d: lab science
    if any(k in t for k in ["biology", "chemistry", "physics", "environmental", "earth science", "ap bio", "ap chem", "ap physics"]):
        return "d"

    # e: language other than english
    if any(k in t for k in ["spanish", "french", "mandarin", "chinese", "japanese", "german"]):
        return "e"

    # f: visual & performing arts
    if any(k in t for k in ["art", "drawing", "painting", "ceramics", "theater", "drama", "dance", "choir", "band", "orchestra", "music"]):
        return "f"

    # g: college-prep elective (often CS/engineering count here, but varies)
    # We'll classify most CS/engineering electives as "g" for planning,
    # and later optionally refine with Foothill's official A–G list.
    if any(k in t for k in ["computer science", "program", "software", "engineering", "pltw", "data", "ai", "machine learning", "cyber"]):
        return "g"

    return None


def is_semester_pair(slot) -> bool:
    return isinstance(slot, list) and len(slot) == 2


def count_years_from_plan(plan_json: dict) -> dict:
    """
    Count A–G years. Assumptions:
    - A normal course counts as 1 year.
    - A [semA, semB] pair counts as 1 year total, but each semester counts 0.5.
    - PE/Health is not A–G unless it matches a category (health usually doesn't).
    """
    counts = {k: 0.0 for k in AG}

    for year in plan_json["plan"]:
        for slot in year["courses"]:
            if is_semester_pair(slot):
                # 0.5 per semester
                for sem_course in slot:
                    cat = infer_ag_category(sem_course)
                    if cat:
                        counts[cat] += 0.5
            else:
                cat = infer_ag_category(slot)
                if cat:
                    counts[cat] += 1.0

    return counts


def ag_gaps(counts: dict) -> list[str]:
    """
    UC A–G minimums (baseline):
      a: 2, b: 4, c: 3, d: 2, e: 2, f: 1, g: 1

    IMPORTANT:
    UC 'g' can be satisfied by:
      - explicit 'g' electives, OR
      - surplus coursework beyond the minimum in a–f.
    """
    req = {"a": 2, "b": 4, "c": 3, "d": 2, "e": 2, "f": 1, "g": 1}

    # Surplus from a–f can count toward g
    surplus_af = 0.0
    for k in ["a", "b", "c", "d", "e", "f"]:
        surplus_af += max(0.0, counts.get(k, 0.0) - req[k])

    effective_g = counts.get("g", 0.0) + surplus_af

    gaps = []
    for k in ["a", "b", "c", "d", "e", "f"]:
        if counts.get(k, 0.0) + 1e-9 < req[k]:
            gaps.append(f"Missing {k}: have {counts.get(k,0):.1f}, need {req[k]}")

    if effective_g + 1e-9 < req["g"]:
        gaps.append(
            f"Missing g: effective_g={effective_g:.1f} "
            f"(counted_g={counts.get('g',0.0):.1f} + surplus_a-f={surplus_af:.1f}), need {req['g']}"
        )

    return gaps

def pretty_ag_counts(counts: dict) -> dict:
    """
    Converts {'a': 3.5, ...} into readable form.
    """
    return {
        AG_DECODE.get(k, k): round(v, 1)
        for k, v in counts.items()
    }


def pretty_ag_gaps(gaps: list[str]) -> list[str]:
    readable = []
    for g in gaps:
        for code, name in AG_DECODE.items():
            g = g.replace(f"Missing {code}:", f"Missing {name}:")
        readable.append(g)
    return readable


