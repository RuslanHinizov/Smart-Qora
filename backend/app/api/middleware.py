import logging
import time

from asgi_correlation_id import correlation_id
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import request_id_var

logger = logging.getLogger("app.access")


class AccessLogMiddleware:
    """Pure-ASGI access log. One structured line per request; bridges the
    correlation id into the log formatter. Not BaseHTTPMiddleware, so it never
    buffers streaming responses (the MJPEG endpoint depends on this).
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        token = request_id_var.set(correlation_id.get())
        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            logger.info("http_request", extra={
                "method": scope.get("method", ""),
                "path": scope.get("path", ""),
                "status": status_code,
                "duration_ms": round((time.perf_counter() - start) * 1000, 1),
            })
            request_id_var.reset(token)
