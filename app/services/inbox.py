"""Newsletter signups and contact messages."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ContactMessage, Subscriber


def subscribe(session: Session, email: str) -> bool:
    """Add an address to the list. Returns True when it was already there.

    Re-subscribing is a no-op rather than an error, and the unique index is the
    real guard: two requests racing with the same address leave one row.
    """
    normalised = email.strip().lower()

    existing = session.scalar(select(Subscriber.id).where(Subscriber.email == normalised))
    if existing is not None:
        return True

    session.add(Subscriber(email=normalised))
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return True

    return False


def save_contact_message(
    session: Session, *, name: str, email: str, subject: str | None, message: str
) -> ContactMessage:
    record = ContactMessage(
        name=name.strip(),
        email=email.strip().lower(),
        subject=(subject or "").strip() or None,
        message=message.strip(),
    )

    session.add(record)
    session.commit()
    session.refresh(record)
    return record
