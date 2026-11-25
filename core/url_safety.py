"""SSRF-safe HTTP fetching and untrusted external content fencing."""
from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlsplit

import aiohttp
from aiohttp.abc import AbstractResolver
from aiohttp.resolver import DefaultResolver


class UnsafeUrlError(ValueError):
    """Raised when a URL fails scheme, host, or public-IP SSRF checks."""


_METADATA_IPS = {
    ipaddress.ip_address("169.254.169.254"),
    ipaddress.ip_address("100.100.100.200"),
}

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _is_disallowed_ip(addr: ipaddress._BaseAddress) -> bool:
    if addr in _METADATA_IPS:
        return True
    return bool(
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
        or not addr.is_global
    )


def validate_public_http_url(raw_url: str, *, resolve_dns: bool = True) -> str:
    """Validate that ``raw_url`` is a public http(s) URL (no loopback/RFC1918/metadata IPs)."""
    if not isinstance(raw_url, str) or not raw_url.strip():
        raise UnsafeUrlError("URL is empty")
    candidate = raw_url.strip()
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlsplit(candidate)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise UnsafeUrlError(f"Unsupported URL scheme: {parsed.scheme!r}")
    if parsed.username or parsed.password:
        raise UnsafeUrlError("Credentials in URL are not allowed")
    hostname = (parsed.hostname or "").strip().lower()
    if not hostname or hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
        raise UnsafeUrlError(f"Disallowed hostname: {hostname!r}")

    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        literal_ip = None

    if literal_ip is not None:
        if _is_disallowed_ip(literal_ip):
            raise UnsafeUrlError(f"Disallowed non-public IP address: {literal_ip}")
        return candidate

    if resolve_dns:
        try:
            infos = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
        except socket.gaierror as exc:
            raise UnsafeUrlError(f"Could not resolve hostname {hostname!r}: {exc}") from exc
        if not infos:
            raise UnsafeUrlError(f"No DNS records for hostname {hostname!r}")
        for info in infos:
            sockaddr = info[4]
            ip_str = sockaddr[0]
            # Strip IPv6 scope id if present
            ip_str = ip_str.split("%", 1)[0]
            addr = ipaddress.ip_address(ip_str)
            if _is_disallowed_ip(addr):
                raise UnsafeUrlError(f"Hostname {hostname!r} resolves to non-public IP {addr}")

    return candidate


class _PublicOnlyResolver(AbstractResolver):
    """aiohttp DNS resolver that rejects non-public IPs at connection lookup time (defeats DNS rebinding)."""

    def __init__(self) -> None:
        self._inner = DefaultResolver()

    async def resolve(self, host: str, port: int = 0, family: int = socket.AF_INET) -> List[Dict[str, Any]]:
        records = await self._inner.resolve(host, port, family)
        if not records:
            raise UnsafeUrlError(f"No DNS records for hostname {host!r}")
        for rec in records:
            ip_str = str(rec.get("host") or "").split("%", 1)[0]
            addr = ipaddress.ip_address(ip_str)
            if _is_disallowed_ip(addr):
                raise UnsafeUrlError(f"Hostname {host!r} resolved to disallowed IP {addr} at connection time")
        return records

    async def close(self) -> None:
        await self._inner.close()


async def validate_public_http_url_async(raw_url: str, *, timeout_seconds: Optional[float] = None) -> str:
    """Validate ``raw_url`` without blocking the asyncio event loop during DNS resolution."""
    candidate = validate_public_http_url(raw_url, resolve_dns=False)
    parsed = urlsplit(candidate)
    hostname = (parsed.hostname or "").strip().lower()
    try:
        ipaddress.ip_address(hostname)
        return candidate
    except ValueError:
        pass

    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    loop = asyncio.get_running_loop()
    lookup = loop.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    try:
        infos = (
            await asyncio.wait_for(lookup, timeout=timeout_seconds)
            if timeout_seconds is not None
            else await lookup
        )
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"Could not resolve hostname {hostname!r}: {exc}") from exc
    if not infos:
        raise UnsafeUrlError(f"No DNS records for hostname {hostname!r}")
    for info in infos:
        sockaddr = info[4]
        ip_str = str(sockaddr[0]).split("%", 1)[0]
        addr = ipaddress.ip_address(ip_str)
        if _is_disallowed_ip(addr):
            raise UnsafeUrlError(f"Hostname {hostname!r} resolves to non-public IP {addr}")
    return candidate


async def safe_fetch_url_text(
    session: Optional[aiohttp.ClientSession],
    url: str,
    *,
    timeout_seconds: float = 12.0,
    max_bytes: int = 2 * 1024 * 1024,
    max_redirects: int = 5,
    user_agent: str = "FlyweelContentEngine/1.0 (+https://github.com/openairlabs/flyweel-agentic-seo-aeo-engine)",
) -> Tuple[str, str, str]:
    """Fetch ``url`` with connection-bound SSRF DNS validation on every redirect hop and bounded body size.

    Returns ``(final_url, content_type, text)``.
    """
    deadline = time.monotonic() + timeout_seconds

    def _remaining() -> float:
        rem = deadline - time.monotonic()
        if rem <= 0:
            raise asyncio.TimeoutError(f"Timed out fetching {url}")
        return rem

    current = await validate_public_http_url_async(url, timeout_seconds=_remaining())
    req_timeout = aiohttp.ClientTimeout(total=_remaining(), connect=min(8.0, _remaining()))
    # Always bind real aiohttp sessions to _PublicOnlyResolver so connection-time DNS lookups cannot rebind to private IPs.
    has_safe_resolver = bool(
        session is not None
        and (
            not isinstance(session, aiohttp.ClientSession)
            or isinstance(getattr(getattr(session, "connector", None), "_resolver", None), _PublicOnlyResolver)
        )
    )
    own_session = not has_safe_resolver
    client = (
        session
        if has_safe_resolver
        else aiohttp.ClientSession(
            timeout=req_timeout,
            connector=aiohttp.TCPConnector(resolver=_PublicOnlyResolver()),
        )
    )
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/markdown, text/plain;q=0.9, text/html;q=0.8, application/xml;q=0.7, */*;q=0.5",
    }
    try:
        for _hop in range(max_redirects + 1):
            hop_rem = _remaining()
            hop_timeout = aiohttp.ClientTimeout(total=hop_rem, connect=min(8.0, hop_rem))
            async with client.get(current, headers=headers, timeout=hop_timeout, allow_redirects=False) as resp:
                if resp.status in {301, 302, 303, 307, 308}:
                    loc = resp.headers.get("Location")
                    if not loc:
                        raise UnsafeUrlError(f"Redirect HTTP {resp.status} missing Location header")
                    next_url = urljoin(current, loc)
                    current = await validate_public_http_url_async(next_url, timeout_seconds=_remaining())
                    continue
                resp.raise_for_status()
                content_type = (resp.headers.get("Content-Type") or "").lower()
                chunks = bytearray()
                async for chunk in resp.content.iter_chunked(16384):
                    chunks.extend(chunk)
                    if len(chunks) > max_bytes:
                        break
                encoding = resp.charset or "utf-8"
                text = bytes(chunks).decode(encoding, errors="replace")
                return current, content_type, text
        raise UnsafeUrlError(f"Exceeded maximum redirects ({max_redirects}) for {url}")
    finally:
        if own_session:
            await client.close()


def fence_untrusted_text(text: str, *, source: str = "external_web", max_chars: int = 40000) -> str:
    """Sanitize control characters and wrap untrusted external text so it cannot break XML prompt fences."""
    cleaned = _CONTROL_CHARS.sub("", str(text or ""))
    cleaned = re.sub(r"[\u200b-\u200f\u2060\ufeff]", "", cleaned)
    cleaned = re.sub(r"(?i)[<＜]/\s*untrusted_external_data\b[^>＞]*[>＞]|[<＜]\s*untrusted_external_data\b[^>＞]*[>＞]", "[stripped-tag]", cleaned)
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars] + "\n...[truncated]..."
    safe_source = re.sub(r'[^a-zA-Z0-9._:/-]+', '_', source)[:120]
    return f'<untrusted_external_data source="{safe_source}">\n{cleaned}\n</untrusted_external_data>'


__all__ = [
    "UnsafeUrlError",
    "fence_untrusted_text",
    "safe_fetch_url_text",
    "validate_public_http_url",
]
