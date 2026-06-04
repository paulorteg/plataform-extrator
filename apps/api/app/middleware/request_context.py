import logging
import re
import time
from typing import Optional
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

REQUEST_ID_HEADER = "X-Request-Id"
REQUEST_ID_STATE_KEY = "request_id"
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

logger = logging.getLogger("mercadoia.api.request")


def normalize_request_id(value: Optional[str]) -> str:
    if value:
        request_id = value.strip()
        if _REQUEST_ID_PATTERN.fullmatch(request_id):
            return request_id
    return str(uuid4())


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
        setattr(request.state, REQUEST_ID_STATE_KEY, request_id)

        started_at = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)

        response.headers[REQUEST_ID_HEADER] = request_id

        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response
