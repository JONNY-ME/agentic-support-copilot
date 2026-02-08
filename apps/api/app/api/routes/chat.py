from fastapi import APIRouter, Depends
from pydantic import BaseModel

from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.services.chat_service import handle_chat

router = APIRouter()

class ChatRequest(BaseModel):
    external_id: str | None = None
    user_id: str | None = None  # backward compatible with your earlier stub
    channel: str = "telegram"
    language: str | None = None
    conversation_ref: str | None = None
    message: str

    def resolved_external_id(self) -> str:
        return self.external_id or self.user_id or "unknown:anonymous"

@router.post("")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    return handle_chat(
        db=db,
        external_id=req.resolved_external_id(),
        channel=req.channel,
        message=req.message,
        language=req.language,
        conversation_ref=req.conversation_ref,
    )
