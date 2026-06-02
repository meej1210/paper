import json
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class ScaIssue(db.Model):
    __tablename__ = "sca_issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False, index=True)
    package_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    installed_version: Mapped[str | None] = mapped_column(String(128))
    vulnerability_id: Mapped[str | None] = mapped_column(String(128), index=True)
    aliases: Mapped[str | None] = mapped_column(Text)
    fix_versions: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str | None] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)

    task = relationship("Task", back_populates="sca_issues")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "package_name": self.package_name,
            "installed_version": self.installed_version,
            "vulnerability_id": self.vulnerability_id,
            "aliases": json.loads(self.aliases or "[]"),
            "fix_versions": json.loads(self.fix_versions or "[]"),
            "description": self.description,
            "severity": self.severity,
        }
