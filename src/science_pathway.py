from math_pathway import find_course_by_keywords

SCI_TRACK = {
    "standard_stem": ["biology", "chemistry", "physics", "ap_science"],
    "finish_fast":   ["earth", "biology", "optional", "optional"],
    "delayed":       ["none", "biology", "chemistry", "physics"],
}

def pick_science_for_grade(catalog, grade, science_pathway, year_index, exclude):
    track = SCI_TRACK.get(science_pathway, SCI_TRACK["standard_stem"])
    desired = track[year_index]

    if desired == "none":
        return None

    if desired == "biology":
        return (find_course_by_keywords(catalog, grade, ["bio"], exclude) or
                find_course_by_keywords(catalog, grade, ["biology"], exclude))

    if desired == "chemistry":
        return (find_course_by_keywords(catalog, grade, ["chem"], exclude) or
                find_course_by_keywords(catalog, grade, ["chemistry"], exclude))

    if desired == "physics":
        return (find_course_by_keywords(catalog, grade, ["phys"], exclude) or
                find_course_by_keywords(catalog, grade, ["physics"], exclude))

    if desired == "earth":
        return (find_course_by_keywords(catalog, grade, ["earth"], exclude) or
                find_course_by_keywords(catalog, grade, ["environment"], exclude))

    if desired == "ap_science":
        return (find_course_by_keywords(catalog, grade, ["ap", "bio"], exclude) or
                find_course_by_keywords(catalog, grade, ["ap", "chem"], exclude) or
                find_course_by_keywords(catalog, grade, ["ap", "physics"], exclude))

    # optional
    return (find_course_by_keywords(catalog, grade, ["ap", "bio"], exclude) or
            find_course_by_keywords(catalog, grade, ["ap", "chem"], exclude) or
            find_course_by_keywords(catalog, grade, ["ap", "physics"], exclude))
