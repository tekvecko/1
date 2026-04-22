
ORDER_STATES = {
    "draft": {"submitted", "cancelled"},
    "submitted": {"locked", "cancelled"},
    "locked": {"sent_to_vendor"},
    "sent_to_vendor": {"delivered", "invoiced", "paid"},
    "delivered": {"invoiced", "paid"},
    "invoiced": {"paid"},
    "paid": set(),
    "cancelled": set(),
}


def can_transition(old: str, new: str) -> bool:
    return new in ORDER_STATES.get(old, set())
