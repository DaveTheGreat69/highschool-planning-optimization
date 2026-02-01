from typing import Any, List


def contains_any(text: str, keywords: List[str]) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)


def slot_to_texts(slot: Any) -> List[str]:
    if isinstance(slot, list):
        return [str(x) for x in slot]
    return [str(slot)]
