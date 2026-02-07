from datetime import datetime

from sqlalchemy import String, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(64), primary_key=True)  # user-facing order id
    customer_id: Mapped["UUID"] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)

    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    delivery_area: Mapped[str | None] = mapped_column(String(128), nullable=True)
    items: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # list or dict, keep flexible

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
