import hashlib
import os
import subprocess

SECRET_KEY = "demo-secret-key"
ADMIN_PASSWORD = "admin123456"


def run_backup(user_input: str) -> str:
    command = f"tar -czf backup.tar.gz {user_input}"
    subprocess.check_output(command, shell=True, text=True)
    return command


def file_checksum(path: str) -> str:
    with open(path, "rb") as handle:
        data = handle.read()
    return hashlib.md5(data).hexdigest()


def temp_file(name: str) -> str:
    return os.path.join("/tmp", name)
