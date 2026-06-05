from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api_errors import unhandled_exception_handler
from app.api.routes.auth import router as auth_router
from app.api.routes.audit import router as audit_router
from app.api.routes.billing import router as billing_router
from app.api.routes.documents import router as documents_router
from app.api.routes.occurrences import router as occurrences_router
from app.api.routes.organizations import router as organizations_router
from app.api.routes.processing_jobs import router as processing_jobs_router
from app.api.routes.usage import router as usage_router
from app.api.routes.users import router as users_router
from app.auth.errors import AuthError, auth_exception_handler
from app.core.config import get_cors_allowed_origins
from app.core.logging import configure_logging
from app.middleware.request_context import RequestContextMiddleware


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(title="MercadoIA API")
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_allowed_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Organization-Id",
            "X-Request-Id",
        ],
    )
    app.add_exception_handler(AuthError, auth_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")
    app.include_router(billing_router, prefix="/api/v1")
    app.include_router(documents_router, prefix="/api/v1")
    app.include_router(occurrences_router, prefix="/api/v1")
    app.include_router(organizations_router, prefix="/api/v1")
    app.include_router(processing_jobs_router, prefix="/api/v1")
    app.include_router(usage_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
