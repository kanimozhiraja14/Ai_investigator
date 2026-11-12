import os
from urllib.parse import urlsplit


def is_production() -> bool:
    return os.getenv("APP_ENV", "development").strip().lower() == "production"


def get_allowed_origins() -> list[str]:
    origins = [
        origin.strip()
        for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
    if "*" in origins:
        raise ValueError("CORS_ALLOWED_ORIGINS must not contain a wildcard")
    return origins


def get_rate_limit() -> tuple[int, int]:
    try:
        requests = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "120"))
        window_seconds = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    except ValueError as exc:
        raise ValueError("Rate-limit settings must be integers") from exc
    if not 1 <= requests <= 100000 or not 1 <= window_seconds <= 86400:
        raise ValueError("Rate-limit settings are outside the supported bounds")
    return requests, window_seconds


def validate_environment() -> None:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env not in {"development", "test", "production"}:
        raise ValueError("APP_ENV must be development, test, or production")

    token = os.getenv("AI_INVESTIGATOR_API_TOKEN", "")
    if token and not 32 <= len(token) <= 4096:
        raise ValueError("AI_INVESTIGATOR_API_TOKEN must contain 32 to 4096 characters")
    if token and (not token.isascii() or any(char.isspace() for char in token)):
        raise ValueError("AI_INVESTIGATOR_API_TOKEN must be ASCII without whitespace")
    if is_production() and not token:
        raise ValueError("AI_INVESTIGATOR_API_TOKEN is required in production")

    origins = get_allowed_origins()
    for origin in origins:
        parsed = urlsplit(origin)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"}:
            raise ValueError("CORS origins must be scheme and host only")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("CORS origins must not contain credentials, query, or fragment")
        if is_production() and parsed.scheme != "https":
            raise ValueError("Production CORS origins must use HTTPS")
    get_rate_limit()
