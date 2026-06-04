from fastapi import FastAPI

from app.api_errors import unhandled_exception_handler
from app.core.logging import configure_logging
from app.middleware.request_context import RequestContextMiddleware


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(title="MercadoIA API")
    app.add_middleware(RequestContextMiddleware)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
