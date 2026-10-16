from fastapi import Request


def client_meta(request: Request) -> tuple[str | None, str | None]:
    """Extract client IP and User-Agent from request.

    Prefers the first address in X-Forwarded-For when present (reverse proxy),
    otherwise falls back to request.client.host.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip() or None
    else:
        ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip, user_agent
