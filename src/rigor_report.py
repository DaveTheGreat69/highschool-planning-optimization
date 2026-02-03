def course_level(title: str) -> str:
    t = title.lower()
    if t.startswith("ap ") or " ap " in t:
        return "AP"
    if "honors" in t or "(hp)" in t:
        return "Honors"
    return "P"

def rigor_summary(plan_json: dict) -> dict:
    counts = {"AP": 0, "Honors": 0, "P": 0}
    for year in plan_json["plan"]:
        for slot in year["courses"]:
            titles = slot if isinstance(slot, list) else [slot]
            for t in titles:
                lvl = course_level(t)
                counts[lvl] += 0.5 if isinstance(slot, list) else 1
    return counts
