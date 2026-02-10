from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.llm_client import embed_texts, generate_answer
from app.db.models import KBDocument, KBChunk

@dataclass
class RetrievedChunk:
    sid: str
    title: str
    page_start: Optional[int]
    page_end: Optional[int]
    content: str
    distance: float

def _top_k() -> int:
    return int(os.getenv("RAG_TOP_K", "6"))

def _max_distance() -> float:
    return float(os.getenv("RAG_MAX_DISTANCE", "0.35"))

def retrieve(db: Session, query: str, language: Optional[str]) -> List[RetrievedChunk]:
    qvec = embed_texts([query])[0]
    top_k = _top_k()

    # Prefer same-language docs when possible
    base_stmt = (
        select(
            KBChunk,
            KBDocument,
            KBChunk.embedding.cosine_distance(qvec).label("distance"),
        )
        .join(KBDocument, KBChunk.document_id == KBDocument.id)
        .order_by(KBChunk.embedding.cosine_distance(qvec))
        .limit(top_k)
    )

    rows = db.execute(base_stmt.where(KBDocument.language == language)).all() if language else []
    if not rows:
        rows = db.execute(base_stmt).all()

    out: List[RetrievedChunk] = []
    for i, (chunk, doc, dist) in enumerate(rows, start=1):
        out.append(
            RetrievedChunk(
                sid=f"S{i}",
                title=doc.title,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                content=chunk.content,
                distance=float(dist),
            )
        )
    return out

def answer_from_kb(db: Session, question: str, language: str) -> Tuple[Optional[str], List[RetrievedChunk]]:
    chunks = retrieve(db, question, language=language)
    if not chunks:
        return None, []

    # If the best chunk is too far, treat as “no answer”
    if chunks[0].distance > _max_distance():
        return None, chunks

    context_lines = []
    for c in chunks:
        pg = ""
        if c.page_start is not None:
            pg = f" (page {c.page_start}" + (f"-{c.page_end}" if c.page_end and c.page_end != c.page_start else "") + ")"
        context_lines.append(f"[{c.sid}] {c.title}{pg}\n{c.content}")

    context = "\n\n".join(context_lines)

    if language == "am":
        instructions = (
            "እርስዎ የደንበኛ ድጋፍ ረዳት ነዎት። ከታች ባለው ኮንቴክስት ብቻ ተመስርተው መልስ ይስጡ። "
            "መረጃ ካልተገኘ በግልፅ 'በአሁኑ ኮንቴክስት ውስጥ አልተገኘም' ይበሉ። "
            "ማንኛውንም እውነታ ሲጠቀሙ የምንጭ መለያውን እንደ [S1] ይጨምሩ።"
        )
    else:
        instructions = (
            "You are a customer support assistant. Answer using only the CONTEXT below. "
            "If the answer is not in the context, say 'I could not find that in the provided knowledge base.' "
            "When you use a fact, cite the snippet id like [S1]."
        )

    prompt = f"{instructions}\n\nQUESTION:\n{question}\n\nCONTEXT:\n{context}\n\nANSWER:"

    text = generate_answer(prompt)

    # Append a clean sources section (mapping S-ids to titles/pages)
    sources = []
    for c in chunks:
        pg = ""
        if c.page_start is not None:
            pg = f" page {c.page_start}" + (f"-{c.page_end}" if c.page_end and c.page_end != c.page_start else "")
        sources.append(f"- [{c.sid}] {c.title}{pg}")

    return text.strip() + "\n\nSources:\n" + "\n".join(sources), chunks
