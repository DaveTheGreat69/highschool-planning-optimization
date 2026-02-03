# src/report_print.py

from src.ag_mapper import pretty_ag_counts, pretty_ag_gaps

PUSD_LABELS = {
    "english": "English",
    "math": "Math",
    "science": "Science",
    "social_science": "Social Science",
    "pe": "Physical Education",
    "health": "Health",
    "vpa_or_wl_or_cte": "VPA / World Language / CTE",
}

def _check(have: float, need: float) -> str:
    return "✅" if have + 1e-9 >= need else "❌"

def print_uc_ag_report(ag_counts: dict, ag_gaps_list: list[str], title="UC A–G"):
    print(f"\n=== {title} ===")
    decoded = pretty_ag_counts(ag_counts)
    for k, v in decoded.items():
        print(f"{k:<35} : {v:.1f}")

    if ag_gaps_list:
        print("\nGaps:")
        for g in pretty_ag_gaps(ag_gaps_list):
            print("-", g)
    else:
        print("\n✅ No UC A–G gaps found.")

def print_pusd_report(pusd: dict, pusd_req: dict, title="PUSD Graduation Requirements"):
    print(f"\n=== {title} ===")

    totals = pusd["pusd_credit_totals"]
    total_earned = pusd["pusd_total_earned"]
    required_min_sum = pusd.get("pusd_required_min_sum", None)
    electives_earned = pusd.get("pusd_electives_earned", None)

    # Required subject buckets
    for key, label in PUSD_LABELS.items():
        have = totals.get(key, 0.0)
        need = pusd_req[key]
        print(f"{label:<28} : {have:>4.0f}/{need:<3} {_check(have, need)}")

    # Total credits
    print(f"\n{'Total credits':<28} : {total_earned:>4.0f}/{pusd_req['total']:<3} {_check(total_earned, pusd_req['total'])}")

    # Electives (leftover)
    if required_min_sum is not None and electives_earned is not None:
        print(f"{'Electives (leftover)':<28} : {electives_earned:>4.0f}/80  {_check(electives_earned, 80)}")
        print(f"{'Required mins sum':<28} : {required_min_sum:>4.0f} (informational)")

    # Subcomponent flags
    sub = pusd.get("pusd_subcomponents", {})
    if sub:
        print("\nSub-requirements:")
        lines = [
            ("algebra_year_done", "1 year Algebra (or equivalent)"),
            ("life_science_done", "1 year Life Science"),
            ("physical_science_done", "1 year Physical Science"),
            ("ethnic_or_global_done", "Ethnic/Global Studies (1 semester)"),
            ("world_history_done", "World History (1 year)"),
            ("us_history_done", "U.S. History (1 year)"),
            ("civics_done", "Civics (1 semester)"),
            ("econ_done", "Economics (1 semester)"),
            ("freshman_pe_done", "Grade 9 PE"),
        ]
        for key, label in lines:
            ok = bool(sub.get(key, False))
            print(f"{label:<40} : {'✅' if ok else '❌'}")

    # Gaps list
    gaps = pusd.get("pusd_gaps", [])
    if gaps:
        print("\nGaps:")
        for g in gaps:
            print("-", g)
    else:
        print("\n✅ No PUSD graduation gaps found.")
