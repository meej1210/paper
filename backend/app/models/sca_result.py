import json
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class ScaResult(db.Model):
    __tablename__ = "sca_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False, unique=True)
    dependency_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vulnerability_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fixable_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    raw_report_path: Mapped[str | None] = mapped_column(Text)
    package_distribution: Mapped[str | None] = mapped_column(Text)
    severity_distribution: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    task = relationship("Task", back_populates="sca_result")

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "dependency_count": self.dependency_count,
            "vulnerability_count": self.vulnerability_count,
            "fixable_count": self.fixable_count,
            "summary": self.summary,
            "raw_report_path": self.raw_report_path,
            "package_distribution": json.loads(self.package_distribution or "{}"),
            "severity_distribution": json.loads(self.severity_distribution or "{}"),
        }
