from fastapi import Request
from fastapi.responses import JSONResponse

from app.middleware.request_context import REQUEST_ID_HEADER, REQUEST_ID_STATE_KEY


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, REQUEST_ID_STATE_KEY, None)
    payload = {
        "code": "internal_server_error",
        "message": "Internal server error.",
        "details": {},
        "request_id": request_id,
    }
    headers = {REQUEST_ID_HEADER: request_id} if request_id else {}
    return JSONResponse(status_code=500, content=payload, headers=headers)
