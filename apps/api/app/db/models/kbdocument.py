import os

from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import VECTOR  # pgvector-python supports SQLAlchemy VECTOR :contentReference[oaicite:6]{index=6}
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))


class KBDocument(Base):
    __tablename__ = "kb_documents"

    id = Column(UUID(as_uuid=True), primary_key=True)
    source_type = Column(String(32), nullable=False)  # pdf|faq|csv
    title = Column(String(256), nullable=False)
    source_path = Column(Text, nullable=False, unique=True)
    language = Column(String(8), nullable=False, default="en")
    meta = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False)


class KBChunk(Base):
    __tablename__ = "kb_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("kb_documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)

    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=False, default=0)

    page_start = Column(Integer, nullable=True)
    page_end = Column(Integer, nullable=True)
    meta = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False)

    # Keep in sync with migration vector dimension
    embedding = Column(VECTOR(EMBEDDING_DIM), nullable=False)
