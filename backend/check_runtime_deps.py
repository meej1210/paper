import importlib
import shutil
import socket
from typing import Iterable

MODULES = [
    ("flask", "Flask"),
    ("sqlalchemy", "SQLAlchemy"),
    ("redis", "redis-py"),
    ("celery", "Celery"),
    ("weasyprint", "WeasyPrint"),
    ("pymysql", "PyMySQL"),
    ("bandit", "Bandit Python package"),
]

COMMANDS = [
    ("bandit", "Bandit CLI"),
    ("wapiti", "Wapiti CLI"),
]

PORTS = [
    ("127.0.0.1", 3306, "MySQL default port"),
    ("127.0.0.1", 6379, "Redis default port"),
    ("127.0.0.1", 5000, "Backend API default port"),
    ("127.0.0.1", 5173, "Frontend Vite default port"),
    ("127.0.0.1", 3000, "Juice Shop default port"),
    ("127.0.0.1", 3100, "Juice Shop fallback port"),
]


def check_module(module_name: str) -> tuple[bool, str]:
    try:
        importlib.import_module(module_name)
        return True, "ok"
    except Exception as exc:  # pragma: no cover - diagnostics only
        return False, f"{type(exc).__name__}: {exc}"


def check_command(command: str) -> tuple[bool, str]:
    path = shutil.which(command)
    return (path is not None, path or "not found")


def check_port(host: str, port: int) -> tuple[bool, str]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.4)
    try:
        sock.connect((host, port))
        return True, "open"
    except Exception as exc:  # pragma: no cover - diagnostics only
        return False, type(exc).__name__
    finally:
        sock.close()


def emit_section(title: str, rows: Iterable[tuple[str, bool, str]]) -> None:
    print(f"\n[{title}]")
    for label, ok, detail in rows:
        status = "OK" if ok else "MISSING"
        print(f"- {label}: {status} ({detail})")


def main() -> int:
    module_rows = [(label, *check_module(name)) for name, label in MODULES]
    command_rows = [(label, *check_command(name)) for name, label in COMMANDS]
    port_rows = [(label, *check_port(host, port)) for host, port, label in PORTS]

    emit_section("Python modules", module_rows)
    emit_section("Commands", command_rows)
    emit_section("Ports", port_rows)

    print("\n[Notes]")
    print("- WeasyPrint Python package may be importable while Windows GTK/Pango native libraries are still incomplete.")
    print("- If PDF export still returns 501, inspect the exact WeasyPrint import error shown by backend startup or runtime logs.")
    print("- Port checks are informational only; closed ports may simply mean the service is not started yet.")

    failed = [row for row in module_rows + command_rows if not row[1]]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
