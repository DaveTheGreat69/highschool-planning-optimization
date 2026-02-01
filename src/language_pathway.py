from math_pathway import find_course_by_keywords

def detect_spanish_next_level(completed_courses):
    text = " | ".join([str(c).lower() for c in completed_courses])
    if "ap spanish" in text:
        return None
    if "spanish iv" in text or "spanish 4" in text:
        return "ap"
    if "spanish iii" in text or "spanish 3" in text:
        return "iv"
    if "spanish ii" in text or "spanish 2" in text:
        return "iii"
    if "spanish i" in text or "spanish 1" in text:
        return "ii"
    return "i"

def pick_spanish_for_grade(catalog, grade, completed_courses, exclude):
    nxt = detect_spanish_next_level(completed_courses)
    if not nxt:
        return None

    if nxt == "iii":
        return (find_course_by_keywords(catalog, grade, ["spanish", "iii"], exclude) or
                find_course_by_keywords(catalog, grade, ["spanish", "3"], exclude))
    if nxt == "iv":
        return (find_course_by_keywords(catalog, grade, ["spanish", "iv"], exclude) or
                find_course_by_keywords(catalog, grade, ["spanish", "4"], exclude))
    if nxt == "ii":
        return (find_course_by_keywords(catalog, grade, ["spanish", "ii"], exclude) or
                find_course_by_keywords(catalog, grade, ["spanish", "2"], exclude))
    if nxt == "i":
        return (find_course_by_keywords(catalog, grade, ["spanish", "i"], exclude) or
                find_course_by_keywords(catalog, grade, ["spanish", "1"], exclude))
    if nxt == "ap":
        return find_course_by_keywords(catalog, grade, ["ap", "spanish"], exclude)

    return None
