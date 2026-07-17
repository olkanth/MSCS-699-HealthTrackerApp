"""core identity tables

Revision ID: 605af560fc9e
Revises:
Create Date: 2026-07-17 13:58:43.264159

Creates the identity/profile tables:
users (logins), providers (staff profiles), patients (clinical profiles).
Run against an already-existing, empty database.
Database should be created before running these migrations.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '605af560fc9e'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("role IN ('patient', 'provider', 'admin', 'it_staff')", name="chk_users_role"),
    )

    op.create_table(
        "providers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("specialty", sa.String(100)),
        sa.Column("npi_number", sa.String(20), unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("gender", sa.String(20)),
        sa.Column("mrn", sa.String(20), nullable=False, unique=True),
        sa.Column("primary_provider_id", sa.Integer(), sa.ForeignKey("providers.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("date_of_birth <= CURRENT_DATE", name="chk_patients_dob"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("patients")
    op.drop_table("providers")
    op.drop_table("users")
