from __future__ import annotations

import argparse
import csv
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import tiktoken
from pypdf import PdfReader
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.language import detect_language
from app.core.llm_client import embed_texts
from app.db.models import KBDocument, KBChunk
from app.db.session import SessionLocal

EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))

def utcnow():
    return datetime.now(timezone.utc)

def normalize_text(s: str) -> str:
    s = s.replace("\x00", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def chunk_by_tokens(text: str, max_tokens: int = 450, overlap: int = 60):
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    if not tokens:
        return []

    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        piece = enc.decode(tokens[start:end]).strip()
        if piece:
            chunks.append((piece, end - start))
        if end == len(tokens):
            break
        start = max(0, end - overlap)
    return chunks

def upsert_document(db: Session, source_type: str, title: str, source_path: str, language: str, meta: dict):
    existing = db.scalar(select(KBDocument).where(KBDocument.source_path == source_path))
    if existing:
        existing.title = title
        existing.source_type = source_type
        existing.language = language
        existing.meta = meta
        db.commit()
        db.refresh(existing)
        return existing

    doc = KBDocument(
        id=uuid4(),
        source_type=source_type,
        title=title,
        source_path=source_path,
        language=language,
        meta=meta,
        created_at=utcnow(),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc

def ingest_pdf(db: Session, path: Path):
    reader = PdfReader(str(path))
    title = path.stem
    source_path = str(path)

    # detect language from first pages
    sample = ""
    for i, page in enumerate(reader.pages[:3]):
        sample += (page.extract_text() or "") + "\n"
    language = detect_language(sample)

    doc = upsert_document(
        db=db,
        source_type="pdf",
        title=title,
        source_path=source_path,
        language=language,
        meta={"filename": path.name},
    )

    # delete old chunks for this document
    db.execute(delete(KBChunk).where(KBChunk.document_id == doc.id))
    db.commit()

    rows_to_embed = []
    chunk_records = []

    chunk_index = 0
    for page_idx, page in enumerate(reader.pages, start=1):
        text = normalize_text(page.extract_text() or "")
        if not text:
            continue

        for piece, tok_count in chunk_by_tokens(text):
            chunk_index += 1
            chunk_id = uuid4()
            chunk_records.append(
                KBChunk(
                    id=chunk_id,
                    document_id=doc.id,
                    chunk_index=chunk_index,
                    content=piece,
                    token_count=tok_count,
                    page_start=page_idx,
                    page_end=page_idx,
                    meta={"type": "pdf", "page": page_idx},
                    created_at=utcnow(),
                    embedding=[0.0] * EMBEDDING_DIM,  # placeholder, replaced after embedding
                )
            )
            rows_to_embed.append((chunk_id, piece))

    # batch embed and insert
    batch_size = 64
    for i in range(0, len(rows_to_embed), batch_size):
        batch = rows_to_embed[i : i + batch_size]
        texts = [t for _, t in batch]
        vecs = embed_texts(texts)
        id_to_vec = {cid: v for (cid, _), v in zip(batch, vecs)}

        for rec in chunk_records:
            if rec.id in id_to_vec:
                rec.embedding = id_to_vec[rec.id]

    db.add_all(chunk_records)
    db.commit()

def ingest_faq(db: Session, path: Path):
    title = path.stem
    source_path = str(path)
    raw = normalize_text(path.read_text(encoding="utf-8", errors="ignore"))
    if not raw:
        return

    language = detect_language(raw)
    doc = upsert_document(
        db=db,
        source_type="faq",
        title=title,
        source_path=source_path,
        language=language,
        meta={"filename": path.name},
    )

    db.execute(delete(KBChunk).where(KBChunk.document_id == doc.id))
    db.commit()

    chunk_records = []
    rows_to_embed = []

    chunk_index = 0
    for piece, tok_count in chunk_by_tokens(raw):
        chunk_index += 1
        chunk_id = uuid4()
        chunk_records.append(
            KBChunk(
                id=chunk_id,
                document_id=doc.id,
                chunk_index=chunk_index,
                content=piece,
                token_count=tok_count,
                page_start=None,
                page_end=None,
                meta={"type": "faq"},
                created_at=utcnow(),
                embedding=[0.0] * EMBEDDING_DIM,
            )
        )
        rows_to_embed.append((chunk_id, piece))

    batch_size = 64
    for i in range(0, len(rows_to_embed), batch_size):
        batch = rows_to_embed[i : i + batch_size]
        texts = [t for _, t in batch]
        vecs = embed_texts(texts)
        id_to_vec = {cid: v for (cid, _), v in zip(batch, vecs)}
        for rec in chunk_records:
            if rec.id in id_to_vec:
                rec.embedding = id_to_vec[rec.id]

    db.add_all(chunk_records)
    db.commit()

def ingest_csv(db: Session, path: Path):
    title = path.stem
    source_path = str(path)

    rows = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    if not rows:
        return

    # detect language from a sample of row strings
    sample = " ".join([" ".join([str(v) for v in rows[0].values()])])
    language = detect_language(sample)

    doc = upsert_document(
        db=db,
        source_type="csv",
        title=title,
        source_path=source_path,
        language=language,
        meta={"filename": path.name},
    )

    db.execute(delete(KBChunk).where(KBChunk.document_id == doc.id))
    db.commit()

    chunk_records = []
    rows_to_embed = []

    chunk_index = 0
    for r in rows:
        # turn a row into a searchable chunk
        parts = []
        for k, v in r.items():
            if v is None:
                continue
            v = str(v).strip()
            if v:
                parts.append(f"{k}: {v}")
        text = normalize_text("\n".join(parts))
        if not text:
            continue

        chunk_index += 1
        chunk_id = uuid4()
        tok_count = len(text.split())
        chunk_records.append(
            KBChunk(
                id=chunk_id,
                document_id=doc.id,
                chunk_index=chunk_index,
                content=text,
                token_count=tok_count,
                page_start=None,
                page_end=None,
                meta={"type": "csv", "row": chunk_index},
                created_at=utcnow(),
                embedding=[0.0] * EMBEDDING_DIM,
            )
        )
        rows_to_embed.append((chunk_id, text))

    batch_size = 64
    for i in range(0, len(rows_to_embed), batch_size):
        batch = rows_to_embed[i : i + batch_size]
        texts = [t for _, t in batch]
        vecs = embed_texts(texts)
        id_to_vec = {cid: v for (cid, _), v in zip(batch, vecs)}
        for rec in chunk_records:
            if rec.id in id_to_vec:
                rec.embedding = id_to_vec[rec.id]

    db.add_all(chunk_records)
    db.commit()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb-path", default="kb", help="Path to kb/ folder")
    args = ap.parse_args()

    kb = Path(args.kb_path)
    pdf_dir = kb / "pdfs"
    faq_dir = kb / "faqs"
    csv_dir = kb / "catalog"

    with SessionLocal() as db:
        for p in sorted(pdf_dir.glob("*.pdf")):
            ingest_pdf(db, p)
            print(f"Ingested PDF: {p}")

        for p in sorted(list(faq_dir.glob("*.md")) + list(faq_dir.glob("*.txt"))):
            ingest_faq(db, p)
            print(f"Ingested FAQ: {p}")

        for p in sorted(csv_dir.glob("*.csv")):
            ingest_csv(db, p)
            print(f"Ingested CSV: {p}")

    print("Done.")

if __name__ == "__main__":
    main()
