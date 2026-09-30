import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

import httpx
import jwt
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("gateway")

REQUEST_ID_HEADER = "X-Request-Id"
HOP_BY_HOP = {"host", "content-length", "connection", "transfer-encoding"}
TIMEOUT_SECONDS = 10.0

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", "").split(",")
    if o.strip()
] or ["http://localhost:5173"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = httpx.AsyncClient(timeout=TIMEOUT_SECONDS)
    try:
        yield
    finally:
        await app.state.client.aclose()


app = FastAPI(title="Habit Tracker Gateway", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[REQUEST_ID_HEADER],
)

JWT_SECRET = os.environ["JWT_SECRET"]
SERVICES = {
    "users": os.environ["USERS_URL"],
    "habits": os.environ["HABITS_URL"],
    "tracking": os.environ["TRACKING_URL"],
    "insights": os.environ["INSIGHTS_URL"],
}

# Paths reachable without a valid JWT: (service, normalized path).
# Login/register/refresh/logout and the password-reset flow are the only
# unauthenticated entries — refresh and logout carry their own credential
# (the reset endpoints are rate-limited by the users service).
PUBLIC_PATHS = {
    ("users", "register"),
    ("users", "login"),
    ("users", "refresh"),
    ("users", "logout"),
    ("users", "forgot-password"),
    ("users", "reset-password"),
}


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
    start = time.perf_counter()
    response = await call_next(request)
    response.headers[REQUEST_ID_HEADER] = request_id
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %s %.1fms rid=%s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        request_id,
    )
    return response


def decode_user(request: Request) -> int | None:
    """Return the authenticated user id, or None. Never trusts client headers."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        payload = jwt.decode(auth[7:], JWT_SECRET, algorithms=["HS256"])
        return int(payload["sub"])
    except Exception:
        return None


@app.get("/health")
async def health():
    """Aggregate liveness of every downstream service."""
    client: httpx.AsyncClient = app.state.client
    checks: dict[str, str] = {}
    all_ok = True
    for name, base_url in SERVICES.items():
        try:
            resp = await client.get(f"{base_url}/health")
            ok = resp.status_code == 200
        except Exception:
            ok = False
        checks[name] = "up" if ok else "down"
        all_ok = all_ok and ok
    status = 200 if all_ok else 503
    return JSONResponse(
        {"status": "ok" if all_ok else "degraded", "services": checks},
        status_code=status,
    )


@app.api_route(
    "/api/{service}/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
async def proxy(service: str, path: str, request: Request):
    if service not in SERVICES:
        raise HTTPException(404, "Unknown service")

    normalized_path = path.strip("/")
    user_id = decode_user(request)
    if (
        (service, normalized_path) not in PUBLIC_PATHS
        and user_id is None
    ):
        raise HTTPException(401, "Authentication required")

    body = await request.body()
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in HOP_BY_HOP
        and k.lower() != "x-user-id"  # never forwarded from the client
        and k.lower() != REQUEST_ID_HEADER.lower()
    }
    if user_id is not None:
        headers["X-User-Id"] = str(user_id)

    client: httpx.AsyncClient = app.state.client
    try:
        resp = await client.request(
            request.method,
            f"{SERVICES[service]}/{normalized_path}",
            content=body,
            headers=headers,
            params=request.query_params,
        )
    except httpx.HTTPError:
        raise HTTPException(502, f"Service {service} unavailable") from None

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type"),
    )
