import pandas as pd
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set


@dataclass(frozen=True)
class Course:
    code: str
    title: str
    subject_section: str
    allowed_grades: Set[int]  # e.g., {9,10,11,12}
    ag: str
    notes: str


def _is_course_code(x) -> bool:
    s = str(x).strip()
    return bool(re.fullmatch(r"\d{5,}", s))


def _is_section_header(x) -> bool:
    if x is None:
        return False
    s = str(x).strip()
    if not s or s.lower() in {"course code", "nan"}:
        return False
    # section headers in your CSV appear like "MATHEMATICS", "SOCIAL SCIENCE", etc.
    return (s.upper() == s) and (not any(c.isdigit() for c in s)) and (len(s) <= 60)


def _extract_grades(row) -> Set[int]:
    out = set()
    for col in ["Unnamed: 2", "Unnamed: 3", "Unnamed: 4", "Unnamed: 5"]:
        if col in row and pd.notna(row[col]):
            try:
                g = int(float(row[col]))
                if 6 <= g <= 12:
                    out.add(g)
            except Exception:
                pass
    return out


def load_catalog(csv_path: str) -> Dict[str, Course]:
    """
    Parses the Foothill CSV into a dict keyed by exact course title.
    """
    df = pd.read_csv(csv_path)
    subject = "UNKNOWN"
    catalog: Dict[str, Course] = {}

    for _, row in df.iterrows():
        first = row.get("ENGLISH")

        if _is_section_header(first):
            subject = str(first).strip()
            continue

        if str(first).strip().lower() == "course code":
            continue

        if _is_course_code(first):
            code = str(first).strip()
            title = str(row.get("Unnamed: 1", "")).strip()
            if not title or title.lower() == "nan":
                continue

            grades = _extract_grades(row)
            ag = str(row.get("Unnamed: 6", "")).strip()
            notes = str(row.get("Unnamed: 7", "")).strip()

            catalog[title] = Course(
                code=code,
                title=title,
                subject_section=subject,
                allowed_grades=grades if grades else {9, 10, 11, 12},  # safe fallback
                ag="" if ag.lower() == "nan" else ag,
                notes="" if notes.lower() == "nan" else notes,
            )

    return catalog
