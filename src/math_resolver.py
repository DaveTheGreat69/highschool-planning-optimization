def normalize(s: str) -> str:
    return (s or "").strip().lower()

def resolve_math_start_from_completed(highest_completed: str, prefer_honors: bool = True) -> str:
    """
    Returns a *desired next step key* based on highest completed course title.
    This feeds into pick_math_for_grade() or directly chooses the next course.
    """

    hc = normalize(highest_completed)

    # Geometry completed -> Algebra II next (honors if preferred)
    if "geometry" in hc:
        return "algebra2_honors" if prefer_honors else "algebra2"

    # Algebra II completed -> Precalculus next (honors if preferred)
    if "algebra ii" in hc or "algebra 2" in hc:
        return "precalc_honors" if prefer_honors else "precalc"

    # Precalc completed -> Calc AB/BC next (you can choose rules here)
    if "pre-calculus" in hc or "precalculus" in hc or "precalc" in hc:
        return "calc_ab"  # or "calc_bc" if you want aggressive

    # Calc AB completed -> Calc BC
    if "calculus ab" in hc:
        return "calc_bc"

    # Default conservative
    return "geometry"
