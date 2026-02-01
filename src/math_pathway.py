# src/math_pathway.py

def find_course_by_keywords(catalog, grade, keywords, exclude):
    """
    Find first course title offered in 'grade' whose title contains ALL keywords.
    catalog: dict[title] -> Course
    """
    for title, c in catalog.items():
        if title in exclude:
            continue
        if grade not in c.allowed_grades:
            continue
        t = title.lower()
        if all(k in t for k in keywords):
            return title
    return None


# A small, deterministic track definition.
# "honors_algebra2" means Grade 9 starts in Algebra 2, then Precalc, then Calc AB, then Calc BC (or Stats).
MATH_TRACK = {
    "honors_geometry": ["geometry", "algebra2", "precalc", "calc_ab"],
    "honors_algebra2": ["algebra2", "precalc", "calc_ab", "calc_bc"],
    "honors_precalc": ["precalc", "calc_ab", "calc_bc", "ap_stats"],
    "calc_ab": ["calc_ab", "calc_bc", "ap_stats", "ap_stats"],
}


def pick_math_for_grade(catalog, grade, starting_math, year_index, exclude):
    """
    Returns an exact Foothill course title from catalog matching the desired step.
    year_index: 0 for grade 9, 1 for grade 10, 2 for grade 11, 3 for grade 12
    """
    track = MATH_TRACK.get(starting_math, MATH_TRACK["honors_geometry"])
    desired = track[year_index]

    # --- Matchers for typical Foothill naming patterns ---
    if desired == "geometry":
        return find_course_by_keywords(catalog, grade, ["geometry"], exclude) or \
               find_course_by_keywords(catalog, grade, ["honors", "geometry"], exclude)

    if desired == "algebra2":
        # Some catalogs use "Algebra II", some "Algebra 2", sometimes "Honors Algebra II"
        return (
            find_course_by_keywords(catalog, grade, ["algebra", "ii"], exclude) or
            find_course_by_keywords(catalog, grade, ["algebra", "2"], exclude) or
            find_course_by_keywords(catalog, grade, ["honors", "algebra", "ii"], exclude) or
            find_course_by_keywords(catalog, grade, ["honors", "algebra", "2"], exclude)
        )

    if desired == "precalc":
        # "Pre-Calculus", "Precalculus"
        return (
            find_course_by_keywords(catalog, grade, ["pre", "cal"], exclude) or
            find_course_by_keywords(catalog, grade, ["precal"], exclude) or
            find_course_by_keywords(catalog, grade, ["honors", "pre"], exclude)
        )

    if desired == "calc_ab":
        return (
            find_course_by_keywords(catalog, grade, ["calculus", "ab"], exclude) or
            find_course_by_keywords(catalog, grade, ["ap", "calculus", "ab"], exclude)
        )

    if desired == "calc_bc":
        return (
            find_course_by_keywords(catalog, grade, ["calculus", "bc"], exclude) or
            find_course_by_keywords(catalog, grade, ["ap", "calculus", "bc"], exclude)
        )

    if desired == "ap_stats":
        # "AP Statistics" or "Statistics"
        return (
            find_course_by_keywords(catalog, grade, ["ap", "statistics"], exclude) or
            find_course_by_keywords(catalog, grade, ["statistics"], exclude) or
            find_course_by_keywords(catalog, grade, ["stats"], exclude)
        )

    return None
