import os
import httpx
import jwt
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

app = FastAPI(title="Habit Tracker Gateway")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

JWT_SECRET = os.environ["JWT_SECRET"]
SERVICES = {
    "users": os.environ["USERS_URL"],
    "habits": os.environ["HABITS_URL"],
    "tracking": os.environ["TRACKING_URL"],
    "insights": os.environ["INSIGHTS_URL"],
}

PUBLIC_PATHS = {("users", "register"), ("users", "login")}


def get_user_id(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        payload = jwt.decode(auth[7:], JWT_SECRET, algorithms=["HS256"])
        return int(payload["sub"])
    except Exception:
        return None


@app.api_route(
    "/api/{service}/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
async def proxy(service: str, path: str, request: Request):
    if service not in SERVICES:
        raise HTTPException(404, "Unknown service")

    user_id = get_user_id(request)
    if (service, path) not in PUBLIC_PATHS and user_id is None:
        raise HTTPException(401, "Authentication required")

    body = await request.body()
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length")
    }
    if user_id is not None:
        headers["X-User-Id"] = str(user_id)

    async with httpx.AsyncClient() as client:
        resp = await client.request(
            request.method,
            f"{SERVICES[service]}/{path}",
            content=body,
            headers=headers,
            params=request.query_params,
        )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type"),
    )
