# src/pusd_grad_audit.py

from dataclasses import dataclass
from typing import Dict, List, Tuple, Any


PUSD_CREDIT_REQ = {
    "english": 40,
    "math": 20,
    "science": 20,
    "social_science": 35,
    "pe": 20,
    "health": 5,
    "vpa_or_wl_or_cte": 10,
    "electives": 80,
    "total": 230,
}

# keyword buckets (heuristic, tuned to your Foothill titles)
KW = {
    "english": ["english", "literature", "comp"],
    "math": ["algebra", "geometry", "pre-cal", "precal", "calculus", "statistics", "math"],
    "science_life": ["biology", "life science", "ap biology"],
    "science_physical": ["chemistry", "physics", "physical science", "ap chemistry", "ap physics"],
    "science_any": ["biology", "chemistry", "physics", "science", "ap biology", "ap chemistry", "ap physics"],

    "ss_ethnic_global": ["ethnic studies", "global"],  # guide: global OR ethnic studies semester :contentReference[oaicite:1]{index=1}
    "ss_world": ["world history"],
    "ss_us": ["u.s. history", "us history"],
    "ss_civics": ["civics", "government"],
    "ss_econ": ["economics", "macroecon", "microecon"],

    "pe": ["pe", "physical education"],
    "health": ["health education"],

    # the 10-credit “one year in any of these” bucket :contentReference[oaicite:2]{index=2}
    "world_language": ["spanish", "french", "mandarin", "chinese", "japanese", "german"],
    "vpa": ["art", "drawing", "painting", "ceramics", "theater", "drama", "dance", "choir", "band", "orchestra", "music", "photography"],
    "cte": ["pltw", "engineering", "computer science", "programming", "software", "robot", "cyber", "data science"],
}

REPLACEABLE_ELECTIVES = {
    # useful if you later want optimizer to fill missing buckets
    "Publications/Yearbook (P)",
}


def _is_semester_pair(slot: Any) -> bool:
    return isinstance(slot, list) and len(slot) == 2


def _credits_for_slot(slot: Any) -> float:
    # In PUSD, each semester course = 5 credits; full-year = 10 credits.
    # Your plan uses course titles for full-year and [semA, semB] for a year split.
    return 10.0 if not _is_semester_pair(slot) else 10.0  # pair still totals 10


def _match_any(title: str, keywords: List[str]) -> bool:
    t = title.lower()
    return any(k in t for k in keywords)


def _bucket_for_course(title: str) -> str | None:
    t = title.lower()

    # English
    if _match_any(title, KW["english"]):
        return "english"

    # Math
    if _match_any(title, KW["math"]):
        return "math"

    # PE
    if _match_any(title, KW["pe"]):
        return "pe"

    # Health
    if _match_any(title, KW["health"]):
        return "health"

    # Social science (detailed)
    if _match_any(title, KW["ss_world"]) or _match_any(title, KW["ss_us"]) or _match_any(title, KW["ss_civics"]) or _match_any(title, KW["ss_econ"]) or _match_any(title, KW["ss_ethnic_global"]):
        return "social_science"

    # Science
    if _match_any(title, KW["science_any"]):
        return "science"

    # VPA/WL/CTE “either/or” bucket (we still track subtypes)
    if _match_any(title, KW["world_language"]) or _match_any(title, KW["vpa"]) or _match_any(title, KW["cte"]):
        return "vpa_or_wl_or_cte"

    # Everything else becomes electives
    return "electives"


def audit_pusd_graduation(plan_json: dict) -> dict:
    """
    Returns:
      - credit_totals by bucket
      - detail flags for required subcomponents:
          * algebra_year_done
          * life_science_done
          * physical_science_done
          * ethnic_or_global_done (semester)
          * world_history_done
          * us_history_done
          * civics_done (semester)
          * econ_done (semester)
      - gaps list
    """

    totals = {k: 0.0 for k in PUSD_CREDIT_REQ.keys() if k != "total"}
    sub = {
        "algebra_year_done": False,        # guide: successful completion of a full year of Algebra or equivalent :contentReference[oaicite:3]{index=3}
        "life_science_done": False,        # guide: life science 1 year :contentReference[oaicite:4]{index=4}
        "physical_science_done": False,    # guide: physical science 1 year :contentReference[oaicite:5]{index=5}

        "ethnic_or_global_done": False,    # guide: global or ethnic studies – 1 semester :contentReference[oaicite:6]{index=6}
        "world_history_done": False,       # guide: 1 year :contentReference[oaicite:7]{index=7}
        "us_history_done": False,          # guide: 1 year :contentReference[oaicite:8]{index=8}
        "civics_done": False,              # guide: 1 semester :contentReference[oaicite:9]{index=9}
        "econ_done": False,                # guide: 1 semester :contentReference[oaicite:10]{index=10}

        "freshman_pe_done": False,         # guide: grade 9 PE required :contentReference[oaicite:11]{index=11}
    }

    # Track the either/or bucket credits separately by subtype (for insight)
    subtype = {"vpa": 0.0, "wl": 0.0, "cte": 0.0}

    for year in plan_json["plan"]:
        g = year["grade"]
        for slot in year["courses"]:
            if _is_semester_pair(slot):
                # Each semester is 5 credits.
                for sem_course in slot:
                    bucket = _bucket_for_course(sem_course)
                    if bucket:
                        totals[bucket] += 5.0

                    # subcomponent checks (semester-level)
                    if _match_any(sem_course, KW["ss_ethnic_global"]):
                        sub["ethnic_or_global_done"] = True
                    if _match_any(sem_course, KW["ss_civics"]):
                        sub["civics_done"] = True
                    if _match_any(sem_course, KW["ss_econ"]):
                        sub["econ_done"] = True

            else:
                bucket = _bucket_for_course(slot)
                totals[bucket] += 10.0

                # subcomponent checks (year-level)
                if bucket == "math" and _match_any(slot, ["algebra"]):
                    # treat any Algebra I/II as satisfying "full year of algebra"
                    sub["algebra_year_done"] = True

                if bucket == "science":
                    if _match_any(slot, KW["science_life"]):
                        sub["life_science_done"] = True
                    if _match_any(slot, KW["science_physical"]):
                        sub["physical_science_done"] = True

                if bucket == "social_science":
                    if _match_any(slot, KW["ss_world"]):
                        sub["world_history_done"] = True
                    if _match_any(slot, KW["ss_us"]):
                        sub["us_history_done"] = True

                if bucket == "pe" and g == 9:
                    sub["freshman_pe_done"] = True

                # subtype counts for the 10-credit either/or bucket
                if bucket == "vpa_or_wl_or_cte":
                    if _match_any(slot, KW["vpa"]):
                        subtype["vpa"] += 10.0
                    elif _match_any(slot, KW["world_language"]):
                        subtype["wl"] += 10.0
                    elif _match_any(slot, KW["cte"]):
                        subtype["cte"] += 10.0

    # Total credits earned in this plan
    total_earned = sum(totals.values())

    # Electives are "leftover credits" beyond required minimums (not a separate course bucket)
    required_min_sum = (
        PUSD_CREDIT_REQ["english"] +
        PUSD_CREDIT_REQ["math"] +
        PUSD_CREDIT_REQ["science"] +
        PUSD_CREDIT_REQ["social_science"] +
        PUSD_CREDIT_REQ["pe"] +
        PUSD_CREDIT_REQ["health"] +
        PUSD_CREDIT_REQ["vpa_or_wl_or_cte"]
    )

    electives_earned = max(0.0, total_earned - required_min_sum)


    # Build gaps
    gaps = []

    for k in ["english", "math", "science", "social_science", "pe", "health", "vpa_or_wl_or_cte"]:
        req = PUSD_CREDIT_REQ[k]
        have = totals.get(k, 0.0)
        if have + 1e-9 < req:
            gaps.append(f"Credits short in {k}: have {have:.0f}, need {req}")

    # Check total credits
    if total_earned + 1e-9 < PUSD_CREDIT_REQ["total"]:
        gaps.append(f"Total credits short: have {total_earned:.0f}, need {PUSD_CREDIT_REQ['total']}")

    # Check elective credits (leftover)
    if electives_earned + 1e-9 < 80:
        gaps.append(f"Electives short (leftover credits): have {electives_earned:.0f}, need 80")


    # Required subcomponents
    if not sub["algebra_year_done"]:
        gaps.append("Missing: successful completion of 1 year Algebra (or equivalent).")

    if not sub["life_science_done"]:
        gaps.append("Missing: 1 year Life Science.")

    if not sub["physical_science_done"]:
        gaps.append("Missing: 1 year Physical Science.")

    if not sub["ethnic_or_global_done"]:
        gaps.append("Missing: Global or Ethnic Studies (1 semester).")

    if not sub["world_history_done"]:
        gaps.append("Missing: World History (1 year).")

    if not sub["us_history_done"]:
        gaps.append("Missing: U.S. History (1 year).")

    if not sub["civics_done"]:
        gaps.append("Missing: Civics (1 semester).")

    if not sub["econ_done"]:
        gaps.append("Missing: Economics (1 semester).")

    if not sub["freshman_pe_done"]:
        gaps.append("Missing: Grade 9 PE (freshman PE required).")

    # The either/or 10-credit bucket: at least 10 credits in VPA or WL or CTE
    if totals.get("vpa_or_wl_or_cte", 0.0) + 1e-9 < PUSD_CREDIT_REQ["vpa_or_wl_or_cte"]:
        gaps.append("Missing: 10 credits in Visual/Performing Arts OR World Language OR CTE.")

    required_min_sum = (
        PUSD_CREDIT_REQ["english"] +
        PUSD_CREDIT_REQ["math"] +
        PUSD_CREDIT_REQ["science"] +
        PUSD_CREDIT_REQ["social_science"] +
        PUSD_CREDIT_REQ["pe"] +
        PUSD_CREDIT_REQ["health"] +
        PUSD_CREDIT_REQ["vpa_or_wl_or_cte"]
    )

    electives_earned = max(0.0, total_earned - required_min_sum)

    return {
        "pusd_credit_totals": totals,
        "pusd_total_earned": total_earned,

        # NEW — how many credits are minimum required (150)
        "pusd_required_min_sum": required_min_sum,

        # NEW — leftover credits that count as electives
        "pusd_electives_earned": electives_earned,

        "pusd_subcomponents": sub,
        "pusd_vpa_wl_cte_breakdown": subtype,
        "pusd_gaps": gaps,
    }

