import json
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class SastIssue(db.Model):
    __tablename__ = "sast_issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False, index=True)
    # Semgrep rule ids can be longer than Bandit's short test ids.
    test_id: Mapped[str | None] = mapped_column(String(255))
    test_name: Mapped[str | None] = mapped_column(String(255))
    issue_severity: Mapped[str | None] = mapped_column(String(32), index=True)
    issue_confidence: Mapped[str | None] = mapped_column(String(32), index=True)
    issue_text: Mapped[str | None] = mapped_column(Text)
    filename: Mapped[str | None] = mapped_column(String(512), index=True)
    line_number: Mapped[int | None] = mapped_column(Integer)
    line_range: Mapped[str | None] = mapped_column(Text)
    code: Mapped[str | None] = mapped_column(Text)
    more_info: Mapped[str | None] = mapped_column(Text)
    cwe: Mapped[str | None] = mapped_column(String(32))
    owasp: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)

    task = relationship("Task", back_populates="sast_issues")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "test_id": self.test_id,
            "test_name": self.test_name,
            "issue_severity": self.issue_severity,
            "issue_confidence": self.issue_confidence,
            "issue_text": self.issue_text,
            "filename": self.filename,
            "line_number": self.line_number,
            "line_range": json.loads(self.line_range) if self.line_range else [],
            "code": self.code,
            "more_info": self.more_info,
            "cwe": self.cwe,
            "owasp": self.owasp,
        }
