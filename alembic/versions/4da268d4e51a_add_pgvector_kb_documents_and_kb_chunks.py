"""add pgvector kb_documents and kb_chunks

Revision ID: 4da268d4e51a
Revises: 3894e0ba0973
Create Date: 2026-05-23 01:00:57.642803

Per-Company knowledge base on pgvector (ADR-0003). Enables the `vector`
extension, then creates `kb_documents` (uploaded sources) and `kb_chunks`
(chunked text + 768-dim embeddings). Hand-written so the extension is created
before the `vector` column and the HNSW index uses the cosine opclass.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '4da268d4e51a'
down_revision: Union[str, Sequence[str], None] = '3894e0ba0973'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# BAAI/bge-base-en-v1.5 embedding dimension.
EMBEDDING_DIM = 768


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        'kb_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(), nullable=True),
        sa.Column('doc_type', sa.String(), nullable=False),
        sa.Column('source_uri', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('error', sa.String(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=True,
        ),
        sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_kb_documents_id'), 'kb_documents', ['id'], unique=False
    )
    op.create_index(
        op.f('ix_kb_documents_company_id'),
        'kb_documents',
        ['company_id'],
        unique=False,
    )

    op.create_table(
        'kb_chunks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(EMBEDDING_DIM), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.ForeignKeyConstraint(['document_id'], ['kb_documents.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_kb_chunks_id'), 'kb_chunks', ['id'], unique=False
    )
    op.create_index(
        op.f('ix_kb_chunks_company_id'),
        'kb_chunks',
        ['company_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_kb_chunks_document_id'),
        'kb_chunks',
        ['document_id'],
        unique=False,
    )
    # HNSW index for approximate nearest-neighbour search. BGE embeddings are
    # normalised, so cosine distance ranks identically to inner product.
    op.execute(
        "CREATE INDEX ix_kb_chunks_embedding ON kb_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_kb_chunks_embedding', table_name='kb_chunks')
    op.drop_index(op.f('ix_kb_chunks_document_id'), table_name='kb_chunks')
    op.drop_index(op.f('ix_kb_chunks_company_id'), table_name='kb_chunks')
    op.drop_index(op.f('ix_kb_chunks_id'), table_name='kb_chunks')
    op.drop_table('kb_chunks')

    op.drop_index(
        op.f('ix_kb_documents_company_id'), table_name='kb_documents'
    )
    op.drop_index(op.f('ix_kb_documents_id'), table_name='kb_documents')
    op.drop_table('kb_documents')
    # The `vector` extension is left installed — other objects may use it.
