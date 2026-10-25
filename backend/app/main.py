import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from starlette.exceptions import HTTPException

from .config import settings
from .db import SessionLocal, uid
from .errors import APIError
from .observability import log, tracer
from .router import router

logging.basicConfig(level=logging.INFO, format="%(message)s")
# Provider/client libraries must not write request bodies or credential-bearing URLs.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

app = FastAPI(title="AgentGuard", version="0.1.0")
app.include_router(router)


def error_body(code, message, request_id, **details):
    return {
        "error": {"type": code.lower(), "code": code, "message": message, "request_id": request_id, **details}
    }


@app.exception_handler(APIError)
async def api_error(request: Request, exc: APIError):
    return JSONResponse(
        error_body(exc.code, exc.message, request.state.request_id, **exc.details),
        status_code=exc.status,
        headers={"Retry-After": "60"} if exc.status == 429 else None,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # Pydantic's raw errors include submitted passwords and prompts; never echo them.
    return JSONResponse(
        error_body("AG_INVALID_INPUT", "Invalid request payload.", request.state.request_id), status_code=422
    )


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return JSONResponse(
        error_body("AG_HTTP_" + str(exc.status_code), str(exc.detail), request.state.request_id),
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    log(
        "internal_error",
        request_id=getattr(request.state, "request_id", ""),
        exception_type=type(exc).__name__,
    )
    return JSONResponse(
        error_body("AG_INTERNAL_ERROR", "Internal server error.", getattr(request.state, "request_id", "")),
        status_code=500,
    )


class RequestBoundary:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id = uid("req_")
        scope.setdefault("state", {})["request_id"] = request_id
        headers = dict(scope["headers"])
        method = scope["method"]
        origin = headers.get(b"origin", b"").decode()
        cookie_auth = b"ag_session=" in headers.get(b"cookie", b"")
        console_login = scope["path"] == "/v1/console/auth/login"
        if (
            method not in ("GET", "HEAD", "OPTIONS")
            and (cookie_auth or console_login)
            and origin not in settings.console_origins
        ):
            return await JSONResponse(
                error_body("AG_CSRF_403", "Untrusted console origin.", request_id), status_code=403
            )(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > settings.max_body_bytes:
                return await JSONResponse(
                    error_body("AG_PAYLOAD_TOO_LARGE", "Request body exceeds the size limit.", request_id),
                    status_code=413,
                )(scope, receive, send)
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        async def response_send(message):
            if message["type"] == "http.response.start":
                message["headers"].extend(
                    [
                        (b"x-request-id", request_id.encode()),
                        (b"cache-control", b"no-store"),
                        (b"x-content-type-options", b"nosniff"),
                    ]
                )
            await send(message)

        with tracer.start_as_current_span("agentguard.http") as span:
            span.set_attribute("http.request.method", method)
            span.set_attribute("agentguard.request_id", request_id)
            await self.app(scope, replay_receive, response_send)


app.add_middleware(RequestBoundary)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.console_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["X-Request-ID"],
)


@app.get("/health")
def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), headers={"Content-Type": CONTENT_TYPE_LATEST})
