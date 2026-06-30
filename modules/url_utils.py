import ipaddress
import socket
from urllib.parse import urlparse


_PRIVATE_SUBNETS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fd00::/8"),
    ipaddress.ip_network("fc00::/7"),
]


def resolve_and_validate_target(url: str) -> bool:
    """Resolve hostname to IPs and reject private/internal addresses.
    Returns True if the target is safe to request, False for private IPs.
    """
    try:
        hostname = urlparse(url).hostname
        if not hostname:
            return False
        addrs = socket.getaddrinfo(hostname, 80, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
        for family, _, _, _, sockaddr in addrs:
            ip_str = sockaddr[0]
            try:
                addr = ipaddress.ip_address(ip_str)
                for net in _PRIVATE_SUBNETS:
                    if addr in net:
                        return False
            except ValueError:
                continue
        return True
    except (socket.gaierror, OSError, ValueError):
        return False


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
