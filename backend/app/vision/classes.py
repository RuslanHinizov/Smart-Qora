"""Canonical livestock class names.

Different model checkpoints label the same animal differently (Open Images uses
"Cattle", the bundled YOLOE checkpoint uses "cow"). Everything inside Smart Qora
stores and compares the canonical name; the detector maps both the model's own
class list and the configured allow-list through :func:`canonical`.
"""

CANONICAL: tuple[str, ...] = ("sheep", "cattle", "goat", "horse")

SYNONYMS = {
    "sheep": "sheep", "lamb": "sheep", "ewe": "sheep", "ram": "sheep",
    "cattle": "cattle", "cow": "cattle", "bull": "cattle", "ox": "cattle", "calf": "cattle", "bovine": "cattle",
    "goat": "goat", "kid": "goat",
    "horse": "horse", "pony": "horse", "foal": "horse", "mare": "horse", "stallion": "horse",
}


def canonical(name: str) -> str | None:
    """Return the canonical class for a raw class name, or None if unknown."""
    return SYNONYMS.get(name.strip().lower())


def display(name: str) -> str:
    """Human label for a canonical (or raw) class name."""
    return (canonical(name) or name).capitalize()
