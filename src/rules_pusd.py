from dataclasses import dataclass
from typing import List, Dict, Tuple


@dataclass(frozen=True)
class SlotRule:
    slot_name: str
    keywords: List[str]  # used to match a Foothill course title
    required: bool = True


# Grade-level core slot rules (PUSD template based)
CORE_SLOTS: Dict[int, List[SlotRule]] = {
    9: [
        SlotRule("English", ["english"]),
        SlotRule("Math", ["math", "algebra", "geometry", "precal", "calculus", "statistics"]),
        SlotRule("Ethnic Studies / Health (semester pair)", ["ethnic", "health"]),
        SlotRule("PE Course 1", ["pe", "physical education", "course 1", "freshmen"]),
    ],
    10: [
        SlotRule("English", ["english"]),
        SlotRule("Math", ["math", "algebra", "geometry", "precal", "calculus", "statistics"]),
        SlotRule("World History", ["world history", "ap world"]),
        SlotRule("Science", ["biology", "chemistry", "physics", "science"]),
        SlotRule("PE Course 2", ["pe", "physical education", "course 2"]),
    ],
    11: [
        SlotRule("English", ["english", "ap english", "language", "lit"]),
        SlotRule("U.S. History", ["u.s. history", "us history", "ap u.s.", "ap us"]),
    ],
    12: [
        SlotRule("English", ["english", "ap english", "language", "lit"]),
        SlotRule("Civics / Economics (semester pair)", ["civics", "government", "econ", "economics", "macro"]),
    ],
}

# Optional: If you want to strongly prefer these Foothill exact course titles when available.
# These are defaults; if your CSV uses slightly different names, adjust here.
PREFERRED_TITLES = {
    "g9_pe": ["PE Course 1-Freshmen"],
    "g9_ethnic_health_pair": [("Ethnic Studies (P)(sem)", "Health Education (P)")],
    "g10_world": ["World History (P)", "Honors World History (P)", "AP World History (HP)"],
    "g11_us": ["U.S. History (P)", "AP U.S. History (HP)"],
    "g12_civics_econ_pair": [("Civics (P) (sem)", "Economics (P) (sem)"), ("Civics (P) (sem)", "AP Macroeconomics (HP) (sem)")],
}
