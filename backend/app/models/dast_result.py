import json
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class DastResult(db.Model):
    __tablename__ = "dast_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False, unique=True)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    is_timeout: Mapped[bool] = mapped_column(default=False, nullable=False)
    issue_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    anomaly_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    additional_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    crawled_pages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    scan_scope: Mapped[str | None] = mapped_column(String(64))
    severity_distribution: Mapped[str | None] = mapped_column(Text)
    type_distribution: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    raw_report_path: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    task = relationship("Task", back_populates="dast_result")

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "target_url": self.target_url,
            "is_timeout": self.is_timeout,
            "issue_count": self.issue_count,
            "anomaly_count": self.anomaly_count,
            "additional_count": self.additional_count,
            "crawled_pages": self.crawled_pages,
            "scan_scope": self.scan_scope,
            "severity_distribution": json.loads(self.severity_distribution) if self.severity_distribution else {},
            "type_distribution": json.loads(self.type_distribution) if self.type_distribution else {},
            "summary": self.summary,
            "raw_report_path": self.raw_report_path,
        }