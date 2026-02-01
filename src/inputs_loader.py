import json
import os

def load_inputs(path="data/inputs.json") -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def resolve_completed_courses(catalog, completed_raw):
    """
    Map user-provided completed course strings to exact catalog titles when possible.
    Example: "Spanish 2" -> "Spanish II (P)" (exact name from CSV)
    """
    resolved = set()

    for item in completed_raw:
        s = str(item).strip().lower()

        # normalize common patterns
        s = s.replace("spanish 1", "spanish i")
        s = s.replace("spanish 2", "spanish ii")
        s = s.replace("spanish 3", "spanish iii")
        s = s.replace("spanish 4", "spanish iv")

        best = None
        for title in catalog.keys():
            t = title.lower()
            if s == t:
                best = title
                break
            if s in t:
                best = title

        resolved.add(best if best else item)

    return resolved
