from fastapi import Request
from fastapi.responses import JSONResponse

from app.middleware.request_context import REQUEST_ID_HEADER, REQUEST_ID_STATE_KEY


class AuthError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


async def auth_exception_handler(request: Request, exc: AuthError) -> JSONResponse:
    request_id = getattr(request.state, REQUEST_ID_STATE_KEY, None)
    payload = {
        "code": exc.code,
        "message": exc.message,
        "details": {},
        "request_id": request_id,
    }
    headers = {REQUEST_ID_HEADER: request_id} if request_id else {}
    if exc.status_code == 401:
        headers["WWW-Authenticate"] = "Bearer"
    return JSONResponse(status_code=exc.status_code, content=payload, headers=headers)
