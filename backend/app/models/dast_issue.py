from datetime import UTC, datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class DastIssue(db.Model):
    __tablename__ = "dast_issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(255), index=True)
    level: Mapped[str | None] = mapped_column(String(32), index=True)
    method: Mapped[str | None] = mapped_column(String(16))
    path: Mapped[str | None] = mapped_column(Text)
    parameter: Mapped[str | None] = mapped_column(String(255))
    info: Mapped[str | None] = mapped_column(Text)
    module: Mapped[str | None] = mapped_column(String(128))
    referer: Mapped[str | None] = mapped_column(Text)
    http_request: Mapped[str | None] = mapped_column(Text)
    curl_command: Mapped[str | None] = mapped_column(Text)
    wstg: Mapped[str | None] = mapped_column(Text)
    cwe: Mapped[str | None] = mapped_column(String(32))
    owasp: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)

    task = relationship("Task", back_populates="dast_issues")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "category": self.category,
            "level": self.level,
            "method": self.method,
            "path": self.path,
            "parameter": self.parameter,
            "info": self.info,
            "module": self.module,
            "referer": self.referer,
            "http_request": self.http_request,
            "curl_command": self.curl_command,
            "wstg": self.wstg,
            "cwe": self.cwe,
            "owasp": self.owasp,
        }