from dataclasses import dataclass
from typing import Dict, Set, Optional
import pandas as pd
import re


@dataclass
class Course:
    title: str
    allowed_grades: Set[int]
    ag_area: Optional[str] = None  # "A".."G" or None
    subject_section: Optional[str] = None  # e.g., "ENGLISH"


SECTION_TOKENS = {
    "ENGLISH",
    "ENGLISH ELECTIVES",
    "MATHEMATICS",
    "HISTORY/SOCIAL SCIENCE",
    "SCIENCE",
    "VISUAL AND PERFORMING ARTS",
    "VISUAL ARTS",
    "PERFORMING ARTS",
    "WORLD LANGUAGE",
    "ADDITIONAL COURSES",
    "PHYSICAL EDUCATION",
    "CAREER AND TECHNICAL EDUCATION",
}


def parse_ag_area(raw) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip()
    m = re.search(r"Area\s*([A-G])", s, flags=re.IGNORECASE)
    return m.group(1).upper() if m else None


def _norm_title(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _is_header_row(row0: str, row1: str) -> bool:
    a = (row0 or "").strip()
    b = (row1 or "").strip().lower()
    if not a and not b:
        return True
    if a.strip().lower() == "course code":
        return True
    if b == "course title":
        return True
    if a.startswith("*") or "students will be placed" in a.lower():
        return True
    return False


def _is_course_code(x: str) -> bool:
    s = (x or "").strip()
    if not s:
        return False
    if s.lower() == "pending":
        return True
    return s.isdigit()


def _allowed_grades_from_cols(c2, c3, c4, c5) -> Set[int]:
    allowed = set()
    cols = [c2, c3, c4, c5]
    for idx, g in enumerate([9, 10, 11, 12]):
        v = cols[idx]
        if v is None:
            continue
        if str(v).strip() != "":
            allowed.add(g)
    return allowed


def load_catalog(csv_path: str) -> Dict[str, Course]:
    df = pd.read_csv(csv_path, header=None, dtype=str, keep_default_na=False)

    catalog: Dict[str, Course] = {}
    current_section: Optional[str] = None

    for _, r in df.iterrows():
        row0 = r.iloc[0] if len(r) > 0 else ""
        row1 = r.iloc[1] if len(r) > 1 else ""

        row0_clean = (row0 or "").strip().upper()

        # Section header?
        if row0_clean in SECTION_TOKENS:
            current_section = row0_clean
            continue

        # Skip non-data rows
        if _is_header_row(row0, row1):
            continue

        code = (row0 or "").strip()
        if not _is_course_code(code):
            continue

        title = _norm_title(row1)
        if not title:
            continue

        # Grades: columns 2-5 correspond to 9-12 markers
        c2 = r.iloc[2] if len(r) > 2 else ""
        c3 = r.iloc[3] if len(r) > 3 else ""
        c4 = r.iloc[4] if len(r) > 4 else ""
        c5 = r.iloc[5] if len(r) > 5 else ""
        allowed_grades = _allowed_grades_from_cols(c2, c3, c4, c5)
        if not allowed_grades:
            continue

        # A-G is column 6
        ag_raw = r.iloc[6] if len(r) > 6 else ""
        ag_area = parse_ag_area(ag_raw)

        catalog[title] = Course(
            title=title,
            allowed_grades=allowed_grades,
            ag_area=ag_area,
            subject_section=current_section
        )

    return catalog
