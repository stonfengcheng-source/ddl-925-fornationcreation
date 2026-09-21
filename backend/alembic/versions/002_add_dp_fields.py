"""Add differential privacy fields to tasks table

Revision ID: 002
Create Date: 2026-02-28

Add DP configuration columns to support differential privacy in federated learning.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add differential privacy columns to tasks table"""
    try:
        op.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dp_enabled INTEGER DEFAULT 0")
        op.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dp_epsilon FLOAT")
        op.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dp_delta FLOAT")
        op.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dp_noise_multiplier FLOAT")
        op.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dp_clipping_norm FLOAT")
        op.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dp_adaptive INTEGER DEFAULT 0")
        op.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dp_epsilon_consumed FLOAT DEFAULT 0.0")
        print("Differential privacy columns added successfully")
    except Exception as e:
        print(f"Error adding DP columns: {e}")


def downgrade() -> None:
    """Remove differential privacy columns from tasks table"""
    try:
        op.execute("ALTER TABLE tasks DROP COLUMN IF EXISTS dp_epsilon_consumed")
        op.execute("ALTER TABLE tasks DROP COLUMN IF EXISTS dp_adaptive")
        op.execute("ALTER TABLE tasks DROP COLUMN IF EXISTS dp_clipping_norm")
        op.execute("ALTER TABLE tasks DROP COLUMN IF EXISTS dp_noise_multiplier")
        op.execute("ALTER TABLE tasks DROP COLUMN IF EXISTS dp_delta")
        op.execute("ALTER TABLE tasks DROP COLUMN IF EXISTS dp_epsilon")
        op.execute("ALTER TABLE tasks DROP COLUMN IF EXISTS dp_enabled")
        print("Differential privacy columns removed successfully")
    except Exception as e:
        print(f"Error removing DP columns: {e}")
