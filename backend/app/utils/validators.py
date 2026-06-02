import ipaddress
import socket
from urllib.parse import urlparse

from email_validator import EmailNotValidError, validate_email

from .exceptions import ApiError


LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def validate_register_payload(payload: dict):
    required = ["username", "email", "password"]
    missing = [field for field in required if not payload.get(field)]
    if missing:
        raise ApiError("invalid parameters", code=40001, status_code=400, errors={field: "required" for field in missing})

    if not 3 <= len(payload["username"]) <= 32:
        raise ApiError("invalid parameters", code=40001, status_code=400, errors={"username": "length must be 3-32"})

    if not 8 <= len(payload["password"]) <= 64:
        raise ApiError("invalid parameters", code=40001, status_code=400, errors={"password": "length must be 8-64"})

    try:
        validate_email(payload["email"], check_deliverability=False)
    except EmailNotValidError as exc:
        raise ApiError("invalid parameters", code=40001, status_code=400, errors={"email": str(exc)}) from exc


def validate_login_payload(payload: dict):
    if not payload.get("username") or not payload.get("password"):
        raise ApiError("invalid parameters", code=40001, status_code=400, errors={"username": "required", "password": "required"})


def _normalize_host(value: str) -> str:
    return value.strip().lower()


def _is_explicit_local_host(hostname: str, allowed_hosts: tuple[str, ...]) -> bool:
    normalized_allowed_hosts = {_normalize_host(host) for host in allowed_hosts if host.strip()}
    if hostname in LOCAL_HOSTS or hostname in normalized_allowed_hosts:
        return True

    try:
        ip_address = ipaddress.ip_address(hostname)
    except ValueError:
        return False

    if ip_address.is_loopback:
        return True

    return str(ip_address) in normalized_allowed_hosts


def _resolve_target_ip(hostname: str) -> str | None:
    try:
        return str(ipaddress.ip_address(hostname))
    except ValueError:
        pass

    if hostname == "localhost":
        return "127.0.0.1"

    try:
        return socket.gethostbyname(hostname)
    except OSError:
        return None


def _classify_target_policy(
    hostname: str,
    resolved_ip: str | None,
    allowed_hosts: tuple[str, ...],
    *,
    allow_private_networks: bool,
    allow_public_targets: bool,
) -> tuple[bool, str | None, str]:
    normalized_allowed_hosts = {_normalize_host(host) for host in allowed_hosts if host.strip()}
    if hostname in LOCAL_HOSTS:
        return True, "localhost", "explicit localhost target"
    if hostname in normalized_allowed_hosts:
        return True, "allowed_host", "hostname is in DAST_ALLOWED_HOSTS"

    ip_address = None
    for candidate in (hostname, resolved_ip):
        if not candidate:
            continue
        try:
            ip_address = ipaddress.ip_address(candidate)
            break
        except ValueError:
            continue

    if ip_address and ip_address.is_loopback:
        return True, "localhost", "resolved target is loopback"
    if resolved_ip and resolved_ip in normalized_allowed_hosts:
        return True, "allowed_host", "resolved IP is in DAST_ALLOWED_HOSTS"
    if ip_address and ip_address.is_private and allow_private_networks:
        return True, "private_network", "private network targets are enabled"
    if allow_public_targets:
        return True, "public_allowed", "public targets are enabled"
    return False, None, "only localhost, private networks when enabled, or explicitly configured test targets are allowed"


def _is_public_target(target_context: dict) -> bool:
    if target_context.get("policy") == "public_allowed":
        return True
    for candidate in (target_context.get("hostname"), target_context.get("resolved_ip")):
        if not candidate:
            continue
        try:
            ip_address = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        return not (ip_address.is_loopback or ip_address.is_private)
    return False


def validate_dast_payload(
    payload: dict,
    default_timeout: int,
    max_timeout: int,
    *,
    allowed_hosts: tuple[str, ...] = (),
    allow_private_networks: bool = False,
    allow_public_targets: bool = False,
    public_max_timeout: int | None = None,
):
    target_url = (payload.get("target_url") or "").strip()
    parsed = urlparse(target_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ApiError("invalid target url", code=40004, status_code=400, errors={"target_url": "must be a valid http or https url"})

    hostname = _normalize_host(parsed.hostname or "")
    if not hostname:
        raise ApiError("invalid target url", code=40004, status_code=400, errors={"target_url": "hostname is required"})

    authorization_confirmed = payload.get("authorization_confirmed") is True
    if not authorization_confirmed:
        raise ApiError(
            "authorization confirmation required",
            code=40001,
            status_code=400,
            errors={"authorization_confirmed": "required"},
        )

    resolved_ip = _resolve_target_ip(hostname)
    host_allowed, policy, reason = _classify_target_policy(
        hostname,
        resolved_ip,
        allowed_hosts,
        allow_private_networks=allow_private_networks,
        allow_public_targets=allow_public_targets,
    )
    target_context = {
        "hostname": hostname,
        "resolved_ip": resolved_ip,
        "policy": policy,
        "authorization_confirmed": authorization_confirmed,
        "allowed_reason": reason if host_allowed else None,
        "reject_reason": None if host_allowed else reason,
    }

    if not host_allowed:
        raise ApiError(
            "target url not allowed",
            code=40004,
            status_code=400,
            errors={"target_url": reason},
        )

    timeout = payload.get("timeout", default_timeout)
    try:
        timeout = int(timeout)
    except (TypeError, ValueError) as exc:
        raise ApiError("invalid parameters", code=40001, status_code=400, errors={"timeout": "must be integer"}) from exc

    if timeout < 1 or timeout > max_timeout:
        raise ApiError("invalid parameters", code=40001, status_code=400, errors={"timeout": f"must be between 1 and {max_timeout}"})

    if public_max_timeout and _is_public_target(target_context):
        timeout = min(timeout, public_max_timeout)
        target_context["public_low_intensity"] = True
        target_context["public_max_timeout"] = public_max_timeout
    else:
        target_context["public_low_intensity"] = False

    return target_url, timeout, target_context


def validate_upload(filename: str, file_size_bytes: int, allowed_extensions: tuple[str, ...], max_size_mb: int):
    lowered = filename.lower()
    if not any(lowered.endswith(ext) for ext in allowed_extensions):
        raise ApiError("unsupported file type", code=40002, status_code=400)

    if file_size_bytes <= 0:
        raise ApiError("empty file", code=40001, status_code=400, errors={"file": "empty file"})

    max_size = max_size_mb * 1024 * 1024
    if file_size_bytes > max_size:
        raise ApiError("file size exceeds limit", code=40003, status_code=400)
