from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class CreateTicketRequest(BaseModel):
    external_id: str = Field(..., examples=["telegram:12345"])
    channel: str = Field(default="telegram")
    language: str = Field(default="en")
    category: str = Field(default="general")
    priority: str = Field(default="normal")
    summary: str
    conversation_ref: str | None = None

class TicketResponse(BaseModel):
    ticket_id: UUID
    status: str

class LookupOrderResponse(BaseModel):
    order_id: str
    status: str
    delivery_area: str | None = None
    items: dict | None = None

class ScheduleCallbackRequest(BaseModel):
    external_id: str
    channel: str = Field(default="telegram")
    language: str = Field(default="en")
    scheduled_time: datetime

class CallbackResponse(BaseModel):
    callback_id: UUID
    status: str
    scheduled_time: datetime

class HandoffRequest(BaseModel):
    external_id: str
    channel: str = Field(default="telegram")
    language: str = Field(default="en")
    reason: str | None = None
