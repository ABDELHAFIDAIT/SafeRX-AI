from sqlalchemy import Column, Integer, String, Text, Numeric, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.app.db.base import Base


class CdsAlert(Base):
    __tablename__ = "cds_alerts"

    id = Column(Integer, primary_key=True, index=True)

    prescription_line_id = Column(
        Integer,
        ForeignKey("prescription_lines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    alert_type = Column(String(50), nullable=False)

    severity = Column(String(20), nullable=False)

    title = Column(String(255), nullable=False)

    detail = Column(Text, nullable=True)

    rag_explanation = Column(Text, nullable=True)

    ai_ignore_proba = Column(Numeric(4, 3), nullable=True)

    created_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    prescription_line = relationship("PrescriptionLine", back_populates="alerts")

    def __repr__(self):
        return (
            f"<CdsAlert id={self.id} type={self.alert_type} "
            f"severity={self.severity} title={self.title[:40]}>"
        )
