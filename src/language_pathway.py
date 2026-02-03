from src.math_pathway import find_course_by_keywords

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

def spanish_sequence_from_completed(completed_courses):
    text = " | ".join([str(c).lower() for c in completed_courses])

    # Completed Spanish II -> start Spanish III
    if "spanish ii" in text or "spanish 2" in text:
        return ["spanish iii", "spanish iv", "ap spanish language", "ap spanish literature"]

    # Completed Spanish III -> start Spanish IV
    if "spanish iii" in text or "spanish 3" in text:
        return ["spanish iv", "ap spanish language", "ap spanish literature", None]

    # Completed Spanish IV -> start AP Spanish Language
    if "spanish iv" in text or "spanish 4" in text:
        return ["ap spanish language", "ap spanish literature", None, None]

    return ["spanish i", "spanish ii", "spanish iii", "spanish iv"]


def pick_spanish_for_grade(catalog, grade, completed_courses, year_index, exclude):
    seq = spanish_sequence_from_completed(completed_courses)
    desired = seq[year_index]
    if not desired:
        return None

    desired_l = desired.lower()
    # match by keywords
    if "spanish iii" in desired_l:
        return find_course_by_keywords(catalog, grade, ["spanish", "iii"], exclude) or \
               find_course_by_keywords(catalog, grade, ["spanish", "3"], exclude)

    if "spanish iv" in desired_l:
        return find_course_by_keywords(catalog, grade, ["spanish", "iv"], exclude) or \
               find_course_by_keywords(catalog, grade, ["spanish", "4"], exclude)

    if "ap spanish language" in desired_l:
        return find_course_by_keywords(catalog, grade, ["ap", "spanish", "language"], exclude)

    if "ap spanish literature" in desired_l:
        return find_course_by_keywords(catalog, grade, ["ap", "spanish", "literature"], exclude)

    if "spanish ii" in desired_l:
        return find_course_by_keywords(catalog, grade, ["spanish", "ii"], exclude) or \
               find_course_by_keywords(catalog, grade, ["spanish", "2"], exclude)

    if "spanish i" in desired_l:
        return find_course_by_keywords(catalog, grade, ["spanish", "i"], exclude) or \
               find_course_by_keywords(catalog, grade, ["spanish", "1"], exclude)

    return None

