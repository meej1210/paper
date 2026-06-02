from flask import jsonify


def success_response(data=None, message="ok", status_code=200):
    return jsonify({"code": 0, "message": message, "data": data or {}}), status_code


def error_response(code: int, message: str, errors=None, status_code=400):
    payload = {"code": code, "message": message}
    if errors:
        payload["errors"] = errors
    return jsonify(payload), status_code
