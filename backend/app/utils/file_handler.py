import shutil
import tarfile
import zipfile
from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.utils import secure_filename

from .exceptions import ApiError


def _safe_join(base_dir: Path, member_name: str) -> Path:
    destination = (base_dir / member_name).resolve()
    if not str(destination).startswith(str(base_dir.resolve())):
        raise ApiError("invalid archive content", code=40002, status_code=400)
    return destination


def save_upload(file_storage) -> str:
    filename = secure_filename(file_storage.filename or f"upload-{uuid4().hex}")
    upload_dir = Path(current_app.config["UPLOAD_DIR"])
    saved_path = upload_dir / f"{uuid4().hex}-{filename}"
    file_storage.save(saved_path)
    return str(saved_path)


def prepare_sast_target(saved_path: str) -> str:
    source = Path(saved_path)
    lowered = source.name.lower()
    if lowered.endswith(".py"):
        return str(source)
    if lowered.endswith(".zip"):
        return _extract_zip(source)
    if lowered.endswith(".tar.gz"):
        return _extract_tar_gz(source)
    raise ApiError("unsupported file type", code=40002, status_code=400)


def _extract_zip(source: Path) -> str:
    target_dir = source.parent / f"{source.stem}-extracted-{uuid4().hex}"
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as archive:
        for member in archive.infolist():
            _safe_join(target_dir, member.filename)
        archive.extractall(target_dir)
    return str(target_dir)


def _extract_tar_gz(source: Path) -> str:
    target_dir = source.parent / f"{source.name.replace('.tar.gz', '')}-extracted-{uuid4().hex}"
    target_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(source, "r:gz") as archive:
        for member in archive.getmembers():
            _safe_join(target_dir, member.name)
        archive.extractall(target_dir)
    return str(target_dir)


def cleanup_path(path: str | None):
    if not path:
        return
    target = Path(path)
    if target.is_dir():
        shutil.rmtree(target, ignore_errors=True)
    elif target.exists():
        target.unlink(missing_ok=True)
