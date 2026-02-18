# Agentic Support Copilot

## Setup

1. Copy `.env.example` to `.env` and set required variables (e.g. `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`).
2. Start services: `make dev`
3. Run migrations: `make migrate`
4. (Optional) Seed demo data: `make seed`

For **RAG (knowledge-base answers)** to work, you must run migrations and then ingest the knowledge base:

- `make migrate` — creates the `kb_documents` and `kb_chunks` tables.
- `make ingest-kb` — ingests content from the `kb/` folder (FAQs, PDFs, catalog CSVs) into the database. Run this after the API (and `kb` volume) are up.

Without `make ingest-kb`, RAG has no chunks and the bot will fall back to "I could not find that in the provided knowledge base" for FAQ-style questions.

## Commands

- `make dev` — start all services
- `make migrate` — run database migrations
- `make seed` — seed demo customer and orders
- `make ingest-kb` — ingest knowledge base from `kb/` for RAG
- `make api-shell` / `make worker-shell` — shell into API or worker container
