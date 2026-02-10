from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_kb_rag"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "kb_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),  # pdf|faq|csv
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False, unique=True),
        sa.Column("language", sa.String(length=8), nullable=False, server_default="en"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Use raw SQL for VECTOR type so we do not depend on SQLAlchemy type plumbing in migration
    op.execute(
        """
        CREATE TABLE kb_chunks (
            id uuid PRIMARY KEY,
            document_id uuid NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
            chunk_index integer NOT NULL,
            content text NOT NULL,
            token_count integer NOT NULL DEFAULT 0,
            page_start integer,
            page_end integer,
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL,
            embedding vector(3072) NOT NULL
        );
        """
    )

    op.execute("CREATE INDEX ix_kb_chunks_document_id ON kb_chunks(document_id);")
    op.execute("CREATE INDEX ix_kb_chunks_language_doc ON kb_documents(language);")

    # HNSW index for cosine distance
    op.execute(
        "CREATE INDEX ix_kb_chunks_embedding_hnsw ON kb_chunks USING hnsw (embedding vector_cosine_ops);"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_kb_chunks_embedding_hnsw;")
    op.execute("DROP TABLE IF EXISTS kb_chunks;")
    op.drop_table("kb_documents")
