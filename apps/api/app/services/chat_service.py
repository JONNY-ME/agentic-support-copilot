from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.language import detect_language
from app.core.memory import MemoryStore
from app.core.safety import is_payment_or_credentials_request, payment_refusal
from app.services import tools_service
from app.services.rag_service import answer_from_kb


ORDER_ID_RE = re.compile(r"\bETH-\d+\b", re.IGNORECASE)

ORDER_KEYWORDS_EN = ["order", "status", "track", "delivery status"]
ORDER_KEYWORDS_AM = ["ትዕዛዝ", "ኦርደር", "ሁኔታ", "ትራክ", "መድረስ"]

TICKET_KEYWORDS_EN = ["complaint", "issue", "problem", "return", "refund", "broken", "wrong item"]
TICKET_KEYWORDS_AM = ["ቅሬታ", "ችግር", "ችግኝ", "መመለስ", "ተሳሳተ", "ተሰብሯል"]

CALLBACK_KEYWORDS_EN = ["call me", "callback", "phone", "ring me"]
CALLBACK_KEYWORDS_AM = ["ደውሉልኝ", "መመለሻ ጥሪ", "ስልክ", "ይደውሉ"]

HUMAN_KEYWORDS_EN = ["human", "agent", "representative", "support person"]
HUMAN_KEYWORDS_AM = ["ሰው", "ሰራተኛ", "ኤጀንት", "ተወካይ"]

def _contains_any(text: str, keywords: list[str]) -> bool:
    t = text.lower()
    return any(k.lower() in t for k in keywords)

def _default_callback_time_utc() -> datetime:
    tz = ZoneInfo("Africa/Addis_Ababa")
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(tz)

    candidate = now_local.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    # Business hours 09:00 to 18:00 local time
    if candidate.hour < 9:
        candidate = candidate.replace(hour=9)
    if candidate.hour >= 18:
        candidate = (candidate + timedelta(days=1)).replace(hour=9)

    return candidate.astimezone(timezone.utc)

def handle_chat(
    db: Session,
    external_id: str,
    channel: str,
    message: str,
    language: str | None = None,
    conversation_ref: str | None = None,
) -> dict:
    mem = MemoryStore.from_env()

    detected_lang = detect_language(message)
    lang = language or detected_lang or "en"

    now = datetime.now(timezone.utc)
    mem.append_turn(external_id, role="user", content=message, ts=now)
    mem.set_profile_field(external_id, "language", lang)

    # Safety gate
    if is_payment_or_credentials_request(message):
        reply = payment_refusal(lang)
        mem.append_turn(external_id, role="assistant", content=reply, ts=datetime.now(timezone.utc))
        return {"external_id": external_id, "reply": reply, "routed_to": "safety"}

    # Human handoff
    if _contains_any(message, HUMAN_KEYWORDS_EN) or _contains_any(message, HUMAN_KEYWORDS_AM):
        ticket = tools_service.handoff_to_human(
            db=db,
            external_id=external_id,
            channel=channel,
            language=lang,
            reason=message,
        )
        if lang == "am":
            reply = f"ወደ ሰው ድጋፍ ተላልፏል። የትኬት መለያ: {ticket.id}"
        else:
            reply = f"Escalated to a human agent. Ticket id: {ticket.id}"
        mem.append_turn(external_id, role="assistant", content=reply, ts=datetime.now(timezone.utc))
        return {"external_id": external_id, "reply": reply, "routed_to": "handoff"}

    # Order lookup (explicit or via memory)
    m = ORDER_ID_RE.search(message)
    order_id = m.group(0).upper() if m else None

    order_intent = (
        _contains_any(message, ORDER_KEYWORDS_EN) or _contains_any(message, ORDER_KEYWORDS_AM)
    )
    if not order_id and order_intent:
        order_id = mem.get_profile_field(external_id, "last_order_id")

    if order_id:
        order = tools_service.lookup_order(db, order_id)
        if not order:
            reply = (
                f"Order {order_id} not found."
                if lang != "am"
                else f"ትዕዛዝ {order_id} አልተገኘም።"
            )
        else:
            mem.set_profile_field(external_id, "last_order_id", order.order_id)
            if lang == "am":
                reply = (
                    f"ትዕዛዝዎ {order.order_id} ሁኔታ: {order.status}."
                    + (f" የመድረሻ ቦታ: {order.delivery_area}." if order.delivery_area else "")
                )
            else:
                reply = (
                    f"Your order {order.order_id} status is: {order.status}."
                    + (f" Delivery area: {order.delivery_area}." if order.delivery_area else "")
                )

        mem.append_turn(external_id, role="assistant", content=reply, ts=datetime.now(timezone.utc))
        return {"external_id": external_id, "reply": reply, "routed_to": "lookup_order"}

    if order_intent and not order_id:
        reply = (
            "Please share your order id (example: ETH-1001)."
            if lang != "am"
            else "እባክዎ የትዕዛዝ መለያዎን ይላኩ (ለምሳሌ: ETH-1001)።"
        )
        mem.append_turn(external_id, role="assistant", content=reply, ts=datetime.now(timezone.utc))
        return {"external_id": external_id, "reply": reply, "routed_to": "order_missing_id"}

    # Callback scheduling
    callback_intent = (
        _contains_any(message, CALLBACK_KEYWORDS_EN) or _contains_any(message, CALLBACK_KEYWORDS_AM)
    )
    if callback_intent:
        scheduled_time = _default_callback_time_utc()
        cb = tools_service.schedule_callback(
            db=db,
            external_id=external_id,
            channel=channel,
            language=lang,
            scheduled_time=scheduled_time,
        )

        local = cb.scheduled_time.astimezone(ZoneInfo("Africa/Addis_Ababa"))
        local_str = local.strftime("%Y-%m-%d %H:%M")
        if lang == "am":
            reply = f"መመለሻ ጥሪ ተይዟል: {local_str} (EAT). መለያ: {cb.id}"
        else:
            reply = f"Callback scheduled for {local_str} (EAT). Id: {cb.id}"

        mem.append_turn(external_id, role="assistant", content=reply, ts=datetime.now(timezone.utc))
        return {"external_id": external_id, "reply": reply, "routed_to": "schedule_callback"}

    # Ticket creation
    ticket_intent = (
        _contains_any(message, TICKET_KEYWORDS_EN) or _contains_any(message, TICKET_KEYWORDS_AM)
    )
    if ticket_intent:
        ticket = tools_service.create_ticket(
            db=db,
            external_id=external_id,
            channel=channel,
            language=lang,
            summary=message,
            category="support",
            priority="normal",
            status="open",
            conversation_ref=conversation_ref,
        )
        if lang == "am":
            reply = f"ትኬት ተከፍቷል። መለያ: {ticket.id}"
        else:
            reply = f"Ticket created. Id: {ticket.id}"

        mem.append_turn(external_id, role="assistant", content=reply, ts=datetime.now(timezone.utc))
        return {"external_id": external_id, "reply": reply, "routed_to": "create_ticket"}

    # RAG fallback (until you move to LangGraph orchestration)
    rag_answer, _chunks = answer_from_kb(db, message, lang)
    if rag_answer:
        mem.append_turn(external_id, role="assistant", content=rag_answer, ts=datetime.now(timezone.utc))
        return {"external_id": external_id, "reply": rag_answer, "routed_to": "rag"}

    # If nothing found, graceful fallback
    if lang == "am":
        reply = (
            "በአሁኑ የኩባንያ መረጃ ውስጥ ይህን አላገኘሁትም። "
            "ተጨማሪ ዝርዝር ቢሰጡኝ እሞክራለሁ፣ ወይም ወደ ሰው ድጋፍ ልላክዎ እችላለሁ።"
        )
    else:
        reply = (
            "I could not find that in the provided knowledge base. "
            "If you share a bit more detail, I can try again, or I can escalate you to a human."
        )

    mem.append_turn(external_id, role="assistant", content=reply, ts=datetime.now(timezone.utc))
    return {"external_id": external_id, "reply": reply, "routed_to": "no_answer"}
