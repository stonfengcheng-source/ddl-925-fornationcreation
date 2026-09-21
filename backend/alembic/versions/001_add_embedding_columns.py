"""Add embedding columns to tasks and datasets tables

Revision ID: 001
Create Date: 2026-02-23

Enable pgvector extension and add vector embedding columns to Task and Dataset models.

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade: Add pgvector extension, embedding columns and indexes"""

    # Try to enable pgvector extension and add embedding support
    try:
        # 1. Enable pgvector extension
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

        # 2. Add embedding column to tasks table
        op.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS embedding vector(1536)")

        # 3. Add embedding column to datasets table
        op.execute("ALTER TABLE datasets ADD COLUMN IF NOT EXISTS embedding vector(1536)")

        # 4. Create HNSW index on tasks table for cosine similarity search
        op.execute(
            "CREATE INDEX idx_tasks_embedding ON tasks "
            "USING hnsw (embedding vector_cosine_ops) "
            "WITH (m = 16, ef_construction = 64)"
        )

        # 5. Create HNSW index on datasets table
        op.execute(
            "CREATE INDEX idx_datasets_embedding ON datasets "
            "USING hnsw (embedding vector_cosine_ops) "
            "WITH (m = 16, ef_construction = 64)"
        )

        print("pgvector extension and embedding columns added successfully")

    except Exception as e:
        # pgvector not available, skip embedding-related migrations
        print(f"Note: pgvector extension not available, skipping embedding columns")
        print(f"Error: {e}")


def downgrade() -> None:
    """Downgrade: Remove embedding columns and indexes"""

    try:
        # 1. Drop indexes
        op.execute("DROP INDEX IF EXISTS idx_datasets_embedding")
        op.execute("DROP INDEX IF EXISTS idx_tasks_embedding")

        # 2. Drop columns
        op.execute("ALTER TABLE datasets DROP COLUMN IF EXISTS embedding")
        op.execute("ALTER TABLE tasks DROP COLUMN IF EXISTS embedding")

        # 3. Optional: Drop pgvector extension (use with caution)
        # op.execute("DROP EXTENSION IF EXISTS vector")

        print("pgvector columns and indexes removed successfully")

    except Exception as e:
        print(f"Note: Error during downgrade, skipping: {e}")
