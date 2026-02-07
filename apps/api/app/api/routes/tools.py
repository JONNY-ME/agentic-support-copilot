from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.db.models import Customer, Ticket, Order, Callback
from app.schemas.tools import (
    CreateTicketRequest,
    TicketResponse,
    LookupOrderResponse,
    ScheduleCallbackRequest,
    CallbackResponse,
    HandoffRequest,
)

router = APIRouter(prefix="/tools")

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

def _get_or_create_customer(db: Session, external_id: str, channel: str, language: str) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.external_id == external_id))
    if customer:
        return customer

    customer = Customer(
        id=uuid4(),
        external_id=external_id,
        channel=channel,
        language_pref=language,
        created_at=_utcnow(),
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer

@router.post("/create_ticket", response_model=TicketResponse)
def create_ticket(req: CreateTicketRequest, db: Session = Depends(get_db)):
    customer = _get_or_create_customer(db, req.external_id, req.channel, req.language)

    ticket = Ticket(
        id=uuid4(),
        customer_id=customer.id,
        category=req.category,
        priority=req.priority,
        status="open",
        summary=req.summary,
        conversation_ref=req.conversation_ref,
        created_at=_utcnow(),
    )
    db.add(ticket)
    db.commit()
    return TicketResponse(ticket_id=ticket.id, status=ticket.status)

@router.get("/lookup_order/{order_id}", response_model=LookupOrderResponse)
def lookup_order(order_id: str, db: Session = Depends(get_db)):
    order = db.scalar(select(Order).where(Order.order_id == order_id))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return LookupOrderResponse(
        order_id=order.order_id,
        status=order.status,
        delivery_area=order.delivery_area,
        items=order.items,
    )

@router.post("/schedule_callback", response_model=CallbackResponse)
def schedule_callback(req: ScheduleCallbackRequest, db: Session = Depends(get_db)):
    customer = _get_or_create_customer(db, req.external_id, req.channel, req.language)

    cb = Callback(
        id=uuid4(),
        customer_id=customer.id,
        scheduled_time=req.scheduled_time,
        status="scheduled",
        created_at=_utcnow(),
    )
    db.add(cb)
    db.commit()
    return CallbackResponse(callback_id=cb.id, status=cb.status, scheduled_time=cb.scheduled_time)

@router.post("/handoff_to_human")
def handoff_to_human(req: HandoffRequest, db: Session = Depends(get_db)):
    # MVP behavior: create a ticket marked escalated
    customer = _get_or_create_customer(db, req.external_id, channel="telegram", language="en")
    ticket = Ticket(
        id=uuid4(),
        customer_id=customer.id,
        category="handoff",
        priority="high",
        status="escalated",
        summary=req.reason or "Handoff requested",
        created_at=_utcnow(),
    )
    db.add(ticket)
    db.commit()
    return {"status": "escalated", "ticket_id": str(ticket.id)}
