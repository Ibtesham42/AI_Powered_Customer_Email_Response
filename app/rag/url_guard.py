"""SSRF guard for outbound URL fetches (knowledge-base URL ingestion).

A user supplies the URL, so a naive fetch could be pointed at internal services
or the cloud metadata endpoint (169.254.169.254). ``validate_public_url`` allows
only http/https and only hosts that resolve exclusively to public IP addresses;
every other case raises ``UnsafeUrlError``.

Note: validation resolves DNS and checks the result, but the subsequent connect
re-resolves — a determined attacker could still attempt DNS rebinding. The fetch
path re-validates on every redirect hop; full rebinding protection (pinning the
validated IP on connect) is a later hardening step.
"""

import ipaddress
import socket
from urllib.parse import urlparse

_ALLOWED_SCHEMES = {"http", "https"}


class UnsafeUrlError(ValueError):
    """The URL is not safe to fetch (bad scheme or a non-public address)."""


def _is_public_ip(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    # Unwrap IPv4-mapped IPv6 (e.g. ::ffff:127.0.0.1) before judging.
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local  # includes 169.254.0.0/16 (cloud metadata)
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def validate_public_url(url: str) -> None:
    """Raise ``UnsafeUrlError`` unless ``url`` is http/https and every IP its
    host resolves to is public."""
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise UnsafeUrlError(
            f"URL scheme must be http or https, got {parsed.scheme or 'none'!r}"
        )

    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("URL has no host")

    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"could not resolve host {host!r}") from exc

    addresses = {info[4][0] for info in infos}
    if not addresses:
        raise UnsafeUrlError(f"host {host!r} did not resolve")

    for address in addresses:
        if not _is_public_ip(address):
            raise UnsafeUrlError(
                f"URL host {host!r} resolves to a non-public address ({address})"
            )
