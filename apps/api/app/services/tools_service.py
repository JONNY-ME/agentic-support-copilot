from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Customer, Ticket, Order, Callback

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def get_or_create_customer(db: Session, external_id: str, channel: str, language: str) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.external_id == external_id))
    if customer:
        # Update language/channel if needed
        changed = False
        if language and customer.language_pref != language:
            customer.language_pref = language
            changed = True
        if channel and customer.channel != channel:
            customer.channel = channel
            changed = True
        if changed:
            db.commit()
        return customer

    customer = Customer(
        id=uuid4(),
        external_id=external_id,
        channel=channel or "unknown",
        language_pref=language or "en",
        created_at=utcnow(),
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer

def create_ticket(
    db: Session,
    external_id: str,
    channel: str,
    language: str,
    summary: str,
    category: str = "general",
    priority: str = "normal",
    status: str = "open",
    conversation_ref: str | None = None,
) -> Ticket:
    customer = get_or_create_customer(db, external_id, channel, language)

    ticket = Ticket(
        id=uuid4(),
        customer_id=customer.id,
        category=category,
        priority=priority,
        status=status,
        summary=summary,
        conversation_ref=conversation_ref,
        created_at=utcnow(),
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket

def lookup_order(db: Session, order_id: str) -> Order | None:
    return db.scalar(select(Order).where(Order.order_id == order_id))

def schedule_callback(
    db: Session,
    external_id: str,
    channel: str,
    language: str,
    scheduled_time: datetime,
) -> Callback:
    customer = get_or_create_customer(db, external_id, channel, language)

    cb = Callback(
        id=uuid4(),
        customer_id=customer.id,
        scheduled_time=scheduled_time,
        status="scheduled",
        created_at=utcnow(),
    )
    db.add(cb)
    db.commit()
    db.refresh(cb)
    return cb

def handoff_to_human(
    db: Session,
    external_id: str,
    channel: str,
    language: str,
    reason: str | None = None,
) -> Ticket:
    return create_ticket(
        db=db,
        external_id=external_id,
        channel=channel,
        language=language,
        summary=reason or "Handoff requested",
        category="handoff",
        priority="high",
        status="escalated",
    )
