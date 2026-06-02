from datetime import UTC, datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class AiIssueInsight(db.Model):
    __tablename__ = "ai_issue_insights"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    issue_id: Mapped[int] = mapped_column(nullable=False, index=True)
    issue_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    model_name: Mapped[str | None] = mapped_column(String(128))
    meaning: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[str] = mapped_column(Text, nullable=False)
    fix: Mapped[str] = mapped_column(Text, nullable=False)
    verify: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    task = relationship("Task")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "issue_id": self.issue_id,
            "issue_fingerprint": self.issue_fingerprint,
            "model_name": self.model_name,
            "meaning": self.meaning,
            "impact": self.impact,
            "fix": self.fix,
            "verify": self.verify,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
