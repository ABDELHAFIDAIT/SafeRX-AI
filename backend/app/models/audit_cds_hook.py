from __future__ import annotations
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from backend.app.db.base import Base


class AuditCdsHook(Base):
    __tablename__ = "audit_cds_hooks"

    id = Column(Integer, primary_key=True, index=True)

    alert_id = Column(
        Integer,
        ForeignKey("cds_alerts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    prescription_id = Column(
        Integer,
        ForeignKey("prescriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    doctor_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    decision = Column(String(20), nullable=False)

    alert_type = Column(String(50), nullable=True)
    alert_severity = Column(String(20), nullable=True)
    alert_title = Column(String(255), nullable=True)

    justification = Column(Text, nullable=True)

    justification_valid = Column(String(10), nullable=True)

    justification_feedback = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self):
        return (
            f"<AuditCdsHook id={self.id} "
            f"decision={self.decision} "
            f"alert_id={self.alert_id}>"
        )
