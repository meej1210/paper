import enum
from datetime import UTC, datetime
from pathlib import PurePosixPath

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text, event, func, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from ..utils.task_display import format_beijing_datetime, localize_task_summary


class TaskType(enum.StrEnum):
    SAST = "SAST"
    DAST = "DAST"
    SCA = "SCA"


class TaskStatus(enum.StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class Task(db.Model):
    __tablename__ = "tasks"
    __table_args__ = (db.UniqueConstraint("user_id", "user_task_no", name="uq_tasks_user_id_user_task_no"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    user_task_no: Mapped[int] = mapped_column(Integer, nullable=False)
    task_type: Mapped[TaskType] = mapped_column(Enum(TaskType), nullable=False, index=True)
    task_name: Mapped[str | None] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    target_path: Mapped[str | None] = mapped_column(String(512))
    target_url: Mapped[str | None] = mapped_column(String(2048))
    authorization_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    target_host: Mapped[str | None] = mapped_column(String(255))
    target_ip: Mapped[str | None] = mapped_column(String(64))
    target_policy: Mapped[str | None] = mapped_column(String(64))
    scanner_engine: Mapped[str | None] = mapped_column(String(32), index=True)
    report_path: Mapped[str | None] = mapped_column(String(512))
    result_summary: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    queue_task_id: Mapped[str | None] = mapped_column(String(128), index=True)
    timeout_seconds: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column()
    started_at: Mapped[datetime | None] = mapped_column()
    finished_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    user = relationship("User", back_populates="tasks")
    sast_result = relationship("SastResult", back_populates="task", uselist=False, cascade="all, delete-orphan")
    dast_result = relationship("DastResult", back_populates="task", uselist=False, cascade="all, delete-orphan")
    sca_result = relationship("ScaResult", back_populates="task", uselist=False, cascade="all, delete-orphan")
    sast_issues = relationship("SastIssue", back_populates="task", cascade="all, delete-orphan")
    dast_issues = relationship("DastIssue", back_populates="task", cascade="all, delete-orphan")
    sca_issues = relationship("ScaIssue", back_populates="task", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        target_name = None
        if self.target_path:
            target_name = PurePosixPath(self.target_path.replace("\\", "/")).name
        return {
            "id": self.id,
            "user_task_no": self.user_task_no,
            "task_type": self.task_type.value,
            "task_name": self.task_name,
            "description": self.description,
            "status": self.status.value,
            "progress": self.progress,
            "report_path": self.report_path,
            "result_summary": localize_task_summary(self.result_summary),
            "scanner_engine": self.scanner_engine,
            "target_name": target_name,
            "target_url": self.target_url,
            "timeout_seconds": self.timeout_seconds,
            "authorization_confirmed": self.authorization_confirmed,
            "target_host": self.target_host,
            "target_ip": self.target_ip,
            "target_policy": self.target_policy,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "started_at": format_beijing_datetime(self.started_at),
            "finished_at": format_beijing_datetime(self.finished_at),
            "created_at": format_beijing_datetime(self.created_at),
        }


@event.listens_for(Task, "before_insert")
def _assign_user_task_no(mapper, connection, target: Task):
    if target.user_task_no is not None:
        return
    stmt = select(func.max(Task.user_task_no)).where(Task.user_id == target.user_id)
    max_value = connection.execute(stmt).scalar()
    target.user_task_no = int(max_value or 0) + 1
