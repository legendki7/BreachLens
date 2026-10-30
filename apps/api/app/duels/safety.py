from pydantic import JsonValue

SENSITIVE_METADATA_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "authorization",
        "authorization_header",
        "cookie",
        "hf_token",
        "password",
        "secret",
        "set_cookie",
        "token",
    }
)


def sanitize_metadata(value: JsonValue) -> JsonValue:
    """Drop credential-bearing metadata keys without altering assessment content."""

    if isinstance(value, dict):
        return {
            key: sanitize_metadata(child)
            for key, child in value.items()
            if key.strip().lower().replace("-", "_") not in SENSITIVE_METADATA_KEYS
        }
    if isinstance(value, list):
        return [sanitize_metadata(child) for child in value]
    return value
