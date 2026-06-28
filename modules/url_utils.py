from urllib.parse import urlparse


def canonical_url(raw_url: str) -> str:
    if not raw_url or not raw_url.strip():
        return ""

    raw_url = raw_url.strip()

    if raw_url.lower() in {"homepage", "home"}:
        return ""

    if raw_url.startswith("/"):
        return ""

    if not raw_url.lower().startswith(("http://", "https://")):
        raw_url = "https://" + raw_url

    parsed = urlparse(raw_url)
    netloc = parsed.netloc.lower().replace("www.", "")
    path = parsed.path.rstrip("/").lower()
    return f"{netloc}{path}"


def exact_url_match(target_url: str, result_url: str) -> bool:
    return canonical_url(target_url) == canonical_url(result_url)
