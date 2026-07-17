"""clinical data tables

Revision ID: 32fadc579546
Revises: 605af560fc9e
Create Date: 2026-07-17 13:58:45.002045

Builds on 605af560fc9e (core identity tables): everything here hangs off
patients.id -- vital signs, activity data, alert thresholds, alerts, risk
scores plus audit_log, which hangs off users.id. 
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32fadc579546'
down_revision: Union[str, Sequence[str], None] = '605af560fc9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "vital_signs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("heart_rate", sa.SmallInteger()),
        sa.Column("systolic_bp", sa.SmallInteger()),
        sa.Column("diastolic_bp", sa.SmallInteger()),
        sa.Column("spo2", sa.SmallInteger()),
        sa.Column("temperature", sa.Numeric(4, 1)),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(50), server_default="device"),
        sa.CheckConstraint("heart_rate IS NULL OR heart_rate BETWEEN 20 AND 300", name="chk_vitals_hr"),
        sa.CheckConstraint("spo2 IS NULL OR spo2 BETWEEN 0 AND 100", name="chk_vitals_spo2"),
        sa.CheckConstraint(
            "systolic_bp IS NULL OR diastolic_bp IS NULL OR systolic_bp > diastolic_bp",
            name="chk_vitals_bp",
        ),
    )
    op.create_index("idx_vitals_patient_time", "vital_signs", ["patient_id", sa.text("recorded_at DESC")])

    op.create_table(
        "activity_data",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("steps", sa.Integer()),
        sa.Column("active_minutes", sa.Integer()),
        sa.Column("distance_km", sa.Numeric(5, 2)),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(50), server_default="device"),
        sa.CheckConstraint("steps IS NULL OR steps >= 0", name="chk_activity_steps"),
    )
    op.create_index("idx_activity_patient_time", "activity_data", ["patient_id", sa.text("recorded_at DESC")])

    op.create_table(
        "alert_thresholds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric_name", sa.String(50), nullable=False),
        sa.Column("min_value", sa.Numeric(6, 2)),
        sa.Column("max_value", sa.Numeric(6, 2)),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("patient_id", "metric_name", name="uq_threshold_patient_metric"),
        sa.CheckConstraint(
            "min_value IS NULL OR max_value IS NULL OR min_value < max_value",
            name="chk_threshold_range",
        ),
    )

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric_name", sa.String(50), nullable=False),
        sa.Column("value", sa.Numeric(6, 2), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("status", sa.String(15), nullable=False, server_default="open"),
        sa.Column("triggered_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("acknowledged_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("acknowledged_at", sa.DateTime()),
        sa.Column("resolved_at", sa.DateTime()),
        sa.CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name="chk_alert_severity"),
        sa.CheckConstraint("status IN ('open', 'acknowledged', 'resolved')", name="chk_alert_status"),
    )
    op.create_index("idx_alerts_patient_status", "alerts", ["patient_id", "status"])

    op.create_table(
        "risk_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("risk_level", sa.String(10), nullable=False),
        sa.Column("contributing_factors", sa.Text()),
        sa.Column("calculated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("risk_level IN ('low', 'medium', 'high')", name="chk_risk_level"),
    )
    op.create_index("idx_risk_patient_time", "risk_scores", ["patient_id", sa.text("calculated_at DESC")])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("table_name", sa.String(50), nullable=False),
        sa.Column("record_id", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("action IN ('create', 'read', 'update', 'delete')", name="chk_audit_action"),
    )
    op.create_index("idx_audit_table_record", "audit_log", ["table_name", "record_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("audit_log")
    op.drop_table("risk_scores")
    op.drop_table("alerts")
    op.drop_table("alert_thresholds")
    op.drop_table("activity_data")
    op.drop_table("vital_signs")
