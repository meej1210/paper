import json
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class SastResult(db.Model):
    __tablename__ = "sast_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False, unique=True)
    issue_count: Mapped[int] = mapped_column(default=0, nullable=False)
    high_count: Mapped[int] = mapped_column(default=0, nullable=False)
    medium_count: Mapped[int] = mapped_column(default=0, nullable=False)
    low_count: Mapped[int] = mapped_column(default=0, nullable=False)
    severity_distribution: Mapped[str | None] = mapped_column(Text)
    confidence_distribution: Mapped[str | None] = mapped_column(Text)
    type_distribution: Mapped[str | None] = mapped_column(Text)
    file_distribution: Mapped[str | None] = mapped_column(Text)
    raw_report_path: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    task = relationship("Task", back_populates="sast_result")

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "issue_count": self.issue_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "severity_distribution": json.loads(self.severity_distribution or "{}"),
            "confidence_distribution": json.loads(self.confidence_distribution or "{}"),
            "type_distribution": json.loads(self.type_distribution or "{}"),
            "file_distribution": json.loads(self.file_distribution or "{}"),
            "raw_report_path": self.raw_report_path,
        }