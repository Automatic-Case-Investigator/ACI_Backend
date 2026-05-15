from rest_framework import status
from rest_framework.response import Response


def error_response(
    code: str,
    message: str,
    details: dict | None = None,
    correlation_id: str | None = None,
    http_status: int = status.HTTP_400_BAD_REQUEST,
) -> Response:
    payload = {
        "code": code,
        "message": message,
        "details": details or {},
        "correlation_id": correlation_id or "",
    }
    return Response(payload, status=http_status)
