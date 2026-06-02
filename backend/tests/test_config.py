import warnings
import subprocess
import sys
from pathlib import Path

from flask_jwt_extended import create_access_token, decode_token


def test_jwt_token_round_trip_emits_no_key_length_warning(app):
    with app.app_context():
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            token = create_access_token(identity="1")
            decode_token(token)

    key_length_warnings = [item for item in caught if item.category.__name__ == "InsecureKeyLengthWarning"]
    assert not key_length_warnings


def test_importing_app_emits_no_dateutil_deprecation_warning():
    backend_dir = Path(__file__).resolve().parents[1]
    script = """
import warnings
warnings.simplefilter('always')
with warnings.catch_warnings(record=True) as caught:
    import app  # noqa: F401
dateutil_warnings = [
    item for item in caught
    if item.category is DeprecationWarning and 'utcfromtimestamp() is deprecated' in str(item.message)
]
print(len(dateutil_warnings))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "0", result.stdout
