from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.schemas.tools import (
    CreateTicketRequest,
    TicketResponse,
    LookupOrderResponse,
    ScheduleCallbackRequest,
    CallbackResponse,
    HandoffRequest,
)
from app.services import tools_service

router = APIRouter(prefix="/tools")

@router.post("/create_ticket", response_model=TicketResponse)
def create_ticket(req: CreateTicketRequest, db: Session = Depends(get_db)):
    ticket = tools_service.create_ticket(
        db=db,
        external_id=req.external_id,
        channel=req.channel,
        language=req.language,
        summary=req.summary,
        category=req.category,
        priority=req.priority,
        status="open",
        conversation_ref=req.conversation_ref,
    )
    return TicketResponse(ticket_id=ticket.id, status=ticket.status)

@router.get("/lookup_order/{order_id}", response_model=LookupOrderResponse)
def lookup_order(order_id: str, db: Session = Depends(get_db)):
    order = tools_service.lookup_order(db, order_id)
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
    cb = tools_service.schedule_callback(
        db=db,
        external_id=req.external_id,
        channel=req.channel,
        language=req.language,
        scheduled_time=req.scheduled_time,
    )
    return CallbackResponse(callback_id=cb.id, status=cb.status, scheduled_time=cb.scheduled_time)

@router.post("/handoff_to_human")
def handoff_to_human(req: HandoffRequest, db: Session = Depends(get_db)):
    ticket = tools_service.handoff_to_human(
        db=db,
        external_id=req.external_id,
        channel=req.channel,
        language=req.language,
        reason=req.reason,
    )
    return {"status": "escalated", "ticket_id": str(ticket.id)}
