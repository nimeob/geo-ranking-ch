#!/usr/bin/env python3
"""Smoke-check for the UI-owned login contract.

Verifies both contracts:
1) ``/login?next=...&reason=...`` is viable as an entrypoint and either
   - renders a UI HTML entry page with a ``start=1`` action, or
   - redirects directly into the login redirect chain,
2) ``/login?next=...&reason=...&start=1`` reaches an IdP authorize redirect.

The redirect chain may be either:
- direct redirect to authorize,
- one or more canonical ``/login`` hops before continuing, or
- UI-owned intermediate hop via ``/auth/login`` followed by authorize.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import socket
import sys
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


@dataclass(frozen=True)
class LoginEntryCheckResult:
    ok: bool
    status_code: int
    location: str
    request_url: str
    content_type: str
    reason: str


@dataclass(frozen=True)
class LoginStartCheckResult:
    ok: bool
    status_code: int
    location: str
    request_url: str
    reason: str


@dataclass(frozen=True)
class _HttpProbeResult:
    status_code: int
    location: str
    content_type: str
    body_preview: str


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


def _build_entry_request_url(base_url: str, *, next_path: str, reason: str) -> str:
    normalized_base = base_url.strip().rstrip("/")
    query = urlencode({"next": next_path, "reason": reason})
    return f"{normalized_base}/login?{query}"


def _build_start_request_url(base_url: str, *, next_path: str, reason: str) -> str:
    normalized_base = base_url.strip().rstrip("/")
    query = urlencode({"next": next_path, "reason": reason, "start": "1"})
    return f"{normalized_base}/login?{query}"


def _canonicalize_base_url_trailing_dot(raw_base_url: str) -> str:
    candidate = str(raw_base_url or "").strip()
    if not candidate:
        return ""

    try:
        parsed = urlsplit(candidate)
    except Exception:  # noqa: BLE001
        return candidate

    if not parsed.scheme or not parsed.netloc:
        return candidate

    host = str(parsed.hostname or "").strip().lower()
    if not host:
        return candidate

    canonical_host = host.rstrip(".")
    if canonical_host == host:
        return candidate

    userinfo = ""
    if parsed.username:
        userinfo = parsed.username
        if parsed.password:
            userinfo += f":{parsed.password}"
        userinfo += "@"

    port_segment = f":{parsed.port}" if parsed.port is not None else ""
    canonical_netloc = f"{userinfo}{canonical_host}{port_segment}"
    return urlunsplit(
        (
            parsed.scheme,
            canonical_netloc,
            parsed.path,
            parsed.query,
            parsed.fragment,
        )
    )


_TRANSIENT_HTTP_STATUSES = frozenset({408, 429, 502, 503, 504})
_REDIRECT_HTTP_STATUSES = frozenset({301, 302, 303, 307, 308})
_MAX_SAME_LOGIN_REDIRECT_HOPS = 4


def _is_redirect_status(status_code: int) -> bool:
    return int(status_code) in _REDIRECT_HTTP_STATUSES


def _resolve_retry_delay(
    *,
    retry_after_header: str,
    default_delay_seconds: float,
    max_retry_delay_seconds: float,
) -> float:
    retry_cap = max(0.0, float(max_retry_delay_seconds))
    fallback_delay = min(max(0.0, float(default_delay_seconds)), retry_cap)
    candidate = retry_after_header.strip()
    if not candidate:
        return fallback_delay

    try:
        return min(max(0.0, float(candidate)), retry_cap)
    except ValueError:
        pass

    try:
        retry_at = parsedate_to_datetime(candidate)
    except (TypeError, ValueError):
        return fallback_delay

    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)

    delta_seconds = (retry_at - datetime.now(timezone.utc)).total_seconds()
    if delta_seconds <= 0:
        return fallback_delay
    return min(delta_seconds, retry_cap)


def _iter_exception_chain(exc: Exception) -> list[Exception]:
    errors: list[Exception] = []
    seen: set[int] = set()
    current: Exception | None = exc

    while current is not None and id(current) not in seen:
        errors.append(current)
        seen.add(id(current))
        current = current.__cause__ or current.__context__

    return errors


def _normalize_reason_suffix(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower())
    cleaned = cleaned.strip("_")
    return cleaned or fallback


def _classify_request_failure(exc: Exception) -> str:
    errors = _iter_exception_chain(exc)
    messages = [str(item or "") for item in errors]
    combined_message = " ".join(messages).lower()

    if (
        any(isinstance(item, (TimeoutError, socket.timeout)) for item in errors)
        or "timed out" in combined_message
    ):
        return "request_failed_timeout_timed_out"

    if any(isinstance(item, socket.gaierror) for item in errors) or any(
        token in combined_message
        for token in (
            "name or service not known",
            "temporary failure in name resolution",
            "nodename nor servname provided",
            "getaddrinfo failed",
            "enotfound",
            "eai_again",
        )
    ):
        return "request_failed_dns_resolution"

    if any(
        isinstance(
            item,
            (
                ConnectionRefusedError,
                ConnectionResetError,
                ConnectionAbortedError,
                BrokenPipeError,
            ),
        )
        for item in errors
    ):
        connection_suffix = _normalize_reason_suffix(
            type(errors[0]).__name__, "connection"
        )
        return f"request_failed_connection_{connection_suffix}"

    if any(
        token in combined_message
        for token in (
            "connection refused",
            "connection reset",
            "connection aborted",
            "host is down",
            "no route to host",
            "network is unreachable",
            "econnrefused",
            "econnreset",
            "ehostunreach",
            "enetunreach",
        )
    ):
        if (
            "connection refused" in combined_message
            or "econnrefused" in combined_message
        ):
            return "request_failed_connection_refused"
        if "connection reset" in combined_message or "econnreset" in combined_message:
            return "request_failed_connection_reset"
        if "host is down" in combined_message or "no route to host" in combined_message:
            return "request_failed_connection_host_unreachable"
        if (
            "network is unreachable" in combined_message
            or "enetunreach" in combined_message
        ):
            return "request_failed_connection_network_unreachable"
        return "request_failed_connection_error"

    if any(
        token in combined_message
        for token in (
            "certificate",
            "cert_has_expired",
            "certificateverifyfailed",
            "certificate verify failed",
            "self signed",
            "x509",
            "ssl",
            "tls",
            "hostname mismatch",
            "doesn't match",
            "unable to get local issuer certificate",
        )
    ):
        if (
            "certificate has expired" in combined_message
            or "cert_has_expired" in combined_message
        ):
            return "request_failed_tls_cert_has_expired"
        if "self signed" in combined_message:
            return "request_failed_tls_self_signed_cert"
        if "unable to get local issuer certificate" in combined_message:
            return "request_failed_tls_untrusted_issuer"
        if (
            "hostname mismatch" in combined_message
            or "doesn't match" in combined_message
        ):
            return "request_failed_tls_hostname_mismatch"
        return "request_failed_tls_error"

    return "request_failed"


_NON_RETRYABLE_REQUEST_FAILURE_REASONS = frozenset(
    {
        "request_failed_tls_hostname_mismatch",
        "request_failed_tls_cert_has_expired",
        "request_failed_tls_self_signed_cert",
        "request_failed_tls_untrusted_issuer",
    }
)


def _is_non_retryable_request_failure(exc: Exception) -> bool:
    reason = _classify_request_failure(exc)
    return reason in _NON_RETRYABLE_REQUEST_FAILURE_REASONS


def _send_request_probe(
    *,
    request_url: str,
    timeout_seconds: float,
    max_attempts: int,
    retry_delay_seconds: float,
    max_retry_delay_seconds: float,
    read_body_preview: bool = False,
) -> _HttpProbeResult:
    req = Request(request_url, method="GET")
    opener = build_opener(_NoRedirect)

    attempts = max(1, int(max_attempts))
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            resp = opener.open(req, timeout=timeout_seconds)
            try:
                status = int(getattr(resp, "status", 0) or resp.getcode())
                location = str(resp.headers.get("Location") or "").strip()
                content_type = str(resp.headers.get("Content-Type") or "").strip()
                body_preview = ""
                if read_body_preview:
                    body_preview = resp.read(4096).decode("utf-8", errors="replace")
            finally:
                close_fn = getattr(resp, "close", None)
                if callable(close_fn):
                    close_fn()
            return _HttpProbeResult(
                status_code=status,
                location=location,
                content_type=content_type,
                body_preview=body_preview,
            )
        except HTTPError as exc:
            try:
                status = int(getattr(exc, "status", 0) or exc.getcode())
                headers = exc.headers or {}
                location = str(headers.get("Location") or "").strip()
                content_type = str(headers.get("Content-Type") or "").strip()
                retry_after_header = str(headers.get("Retry-After") or "").strip()
                body_preview = ""
                if read_body_preview and exc.fp is not None:
                    try:
                        body_preview = exc.read(4096).decode("utf-8", errors="replace")
                    except Exception:  # noqa: BLE001
                        body_preview = ""
            finally:
                exc.close()
            if status in _TRANSIENT_HTTP_STATUSES and attempt < attempts:
                time.sleep(
                    _resolve_retry_delay(
                        retry_after_header=retry_after_header,
                        default_delay_seconds=retry_delay_seconds,
                        max_retry_delay_seconds=max_retry_delay_seconds,
                    )
                )
                continue
            return _HttpProbeResult(
                status_code=status,
                location=location,
                content_type=content_type,
                body_preview=body_preview,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if _is_non_retryable_request_failure(exc):
                break
            if attempt >= attempts:
                break
            time.sleep(
                min(max(0.0, retry_delay_seconds), max(0.0, max_retry_delay_seconds))
            )

    raise RuntimeError(
        f"request_failed_after_retries(attempts={attempts}, timeout_seconds={timeout_seconds}): {last_error}"
    ) from last_error


def _send_request(
    *,
    request_url: str,
    timeout_seconds: float,
    max_attempts: int,
    retry_delay_seconds: float,
    max_retry_delay_seconds: float,
) -> tuple[int, str]:
    probe = _send_request_probe(
        request_url=request_url,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        retry_delay_seconds=retry_delay_seconds,
        max_retry_delay_seconds=max_retry_delay_seconds,
        read_body_preview=False,
    )
    return probe.status_code, probe.location


def _normalize_host_token(raw_host: str) -> str:
    candidate = str(raw_host or "").strip()
    if not candidate:
        return ""

    bare_candidate = candidate.strip("[]").lower()
    if ":" in bare_candidate and "://" not in candidate:
        try:
            ipaddress.ip_address(bare_candidate)
        except ValueError:
            pass
        else:
            return bare_candidate

    parsed = urlparse(candidate if "://" in candidate else f"//{candidate}")
    host = str(parsed.hostname or "").strip().lower()
    if host:
        return host.rstrip(".")

    return candidate.strip("[]").lower().rstrip(".")


def _expand_geo_host_variants(host: str) -> set[str]:
    normalized = str(host or "").strip().lower()
    if not normalized:
        return set()

    variants = {normalized}
    if "geo-ranking" in normalized:
        variants.add(normalized.replace("geo-ranking", "georanking"))
    if "georanking" in normalized:
        variants.add(normalized.replace("georanking", "geo-ranking"))
    return variants


def _parse_allowed_authorize_hosts(raw_hosts: str | None) -> set[str]:
    if not raw_hosts:
        return set()
    hosts: set[str] = set()
    for token in raw_hosts.split(","):
        normalized = _normalize_host_token(token)
        if not normalized:
            continue
        hosts.update(_expand_geo_host_variants(normalized))
    return hosts


def _derive_default_allowed_authorize_hosts(base_url: str) -> set[str]:
    parsed = urlparse(str(base_url or "").strip())
    host = _normalize_host_token(parsed.hostname or "")
    if not host:
        return set()

    if host in {"localhost", "localhost.localdomain"}:
        return set()

    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        return set()

    seed_hosts: list[str] = []
    if host.startswith("www.") and len(host) > 4:
        bare_host = host[4:]
        seed_hosts.append(f"auth.{bare_host}")
        seed_hosts.append(host)
    else:
        seed_hosts.append(f"auth.{host}")
        seed_hosts.append(host)

    allow_hosts: set[str] = set()
    for seed in seed_hosts:
        allow_hosts.update(_expand_geo_host_variants(seed))
    return allow_hosts


def _is_authorize_redirect(
    location: str, *, allowed_authorize_hosts: set[str] | None = None
) -> bool:
    parsed_location = urlparse(location)
    # Contract: redirect target must actually route to an authorize endpoint.
    # Keep matching flexible across IdP path variants (/oauth2/authorize, /oidc/authorize, ...)
    # but do not accept unrelated paths that only mention "authorize" in query params.
    if "authorize" not in parsed_location.path.lower():
        return False

    # Relative redirects (e.g. /oauth2/authorize) stay valid.
    if not parsed_location.netloc:
        return True

    if not allowed_authorize_hosts:
        return True

    observed_host = _normalize_host_token(parsed_location.hostname or "")
    return observed_host in allowed_authorize_hosts


def _is_auth_login_redirect(location: str) -> bool:
    return urlparse(location).path.rstrip("/").lower() == "/auth/login"


class _AnchorHrefCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for attr_name, attr_value in attrs:
            if attr_name.lower() == "href" and attr_value is not None:
                href = str(attr_value).strip()
                if href:
                    self.hrefs.append(href)
                return


def _validate_entry_start_link_query(
    *, body_preview: str, next_path: str, reason: str, request_url: str
) -> tuple[bool, str]:
    collector = _AnchorHrefCollector()
    collector.feed(body_preview)
    collector.close()

    has_start_link = False
    has_matching_origin = False
    has_matching_next = False

    for href in collector.hrefs:
        parsed = urlparse(href)
        normalized_path = parsed.path.rstrip("/").lower()
        if normalized_path and normalized_path != "/login":
            continue

        query = parse_qs(parsed.query, keep_blank_values=True)
        start_value = str((query.get("start") or [""])[0])
        if start_value != "1":
            continue

        has_start_link = True

        if not _is_same_origin_login_entry_href(href=href, request_url=request_url):
            continue

        has_matching_origin = True

        next_value = str((query.get("next") or [""])[0])
        if next_value != str(next_path):
            continue

        has_matching_next = True

        reason_value = str((query.get("reason") or [""])[0])
        if reason_value != str(reason):
            continue

        return True, "ok"

    if not has_start_link:
        if "start=1" in body_preview.lower():
            return True, "ok"
        return False, "entry_missing_start_link"

    if not has_matching_origin:
        return False, "entry_start_link_host_mismatch"

    if not has_matching_next:
        return False, "entry_start_link_next_mismatch"

    return False, "entry_start_link_reason_mismatch"


def _is_same_origin_login_entry_href(*, href: str, request_url: str) -> bool:
    parsed_href = urlparse(href)

    # Relative URLs are same-origin by definition in browser navigation.
    if not parsed_href.netloc:
        return True

    parsed_request = urlparse(request_url)
    request_host = _normalize_host_token(parsed_request.hostname or "")
    href_host = _normalize_host_token(parsed_href.hostname or "")
    if not request_host or not href_host:
        return False

    allowed_hosts = _expand_geo_host_variants(request_host)
    if href_host not in allowed_hosts:
        return False

    request_scheme = (parsed_request.scheme or "").strip().lower()
    href_scheme = (parsed_href.scheme or request_scheme).strip().lower()
    if request_scheme and href_scheme and href_scheme != request_scheme:
        return False

    default_port = {"http": 80, "https": 443}
    request_port = parsed_request.port or default_port.get(request_scheme)
    href_port = parsed_href.port or default_port.get(href_scheme)
    return request_port == href_port


def _validate_auth_login_redirect_query(
    *, location: str, next_path: str, reason: str, phase: str
) -> tuple[bool, str]:
    parsed = urlparse(location)
    query = parse_qs(parsed.query, keep_blank_values=True)

    next_value = str((query.get("next") or [""])[0])
    if next_value != str(next_path):
        return False, f"{phase}_auth_login_redirect_next_mismatch"

    reason_value = str((query.get("reason") or [""])[0])
    if reason_value != str(reason):
        return False, f"{phase}_auth_login_redirect_reason_mismatch"

    return True, "ok"


def _is_same_login_entry_redirect(
    *, location: str, next_path: str, reason: str, require_start: bool
) -> bool:
    parsed = urlparse(location)
    if parsed.path.rstrip("/").lower() != "/login":
        return False

    query = parse_qs(parsed.query, keep_blank_values=True)
    next_value = str((query.get("next") or [""])[0])
    if next_value != str(next_path):
        return False

    reason_value = str((query.get("reason") or [""])[0])
    if reason_value != str(reason):
        return False

    if require_start:
        start_value = str((query.get("start") or [""])[0])
        if start_value != "1":
            return False

    return True


def _is_login_unavailable_redirect(location: str) -> bool:
    return "reason=login_unavailable" in location.lower()


def _follow_same_login_redirects(
    *,
    phase: str,
    request_url: str,
    probe: _HttpProbeResult,
    next_path: str,
    reason: str,
    require_start: bool,
    timeout_seconds: float,
    max_attempts: int,
    retry_delay_seconds: float,
    max_retry_delay_seconds: float,
) -> tuple[str, _HttpProbeResult, str | None]:
    current_request_url = request_url
    current_probe = probe
    visited_request_urls = {current_request_url}

    for _ in range(_MAX_SAME_LOGIN_REDIRECT_HOPS):
        if not (
            _is_redirect_status(current_probe.status_code)
            and current_probe.location
            and _is_same_login_entry_redirect(
                location=current_probe.location,
                next_path=next_path,
                reason=reason,
                require_start=require_start,
            )
        ):
            return current_request_url, current_probe, None

        candidate_request_url = urljoin(current_request_url, current_probe.location)
        if candidate_request_url in visited_request_urls:
            return (
                current_request_url,
                current_probe,
                f"{phase}_same_login_redirect_loop_detected",
            )
        visited_request_urls.add(candidate_request_url)
        current_request_url = candidate_request_url
        current_probe = _send_request_probe(
            request_url=current_request_url,
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
            retry_delay_seconds=retry_delay_seconds,
            max_retry_delay_seconds=max_retry_delay_seconds,
            read_body_preview=(phase == "entry"),
        )

    if (
        _is_redirect_status(current_probe.status_code)
        and current_probe.location
        and _is_same_login_entry_redirect(
            location=current_probe.location,
            next_path=next_path,
            reason=reason,
            require_start=require_start,
        )
    ):
        return (
            current_request_url,
            current_probe,
            f"{phase}_same_login_redirect_hop_limit_exceeded",
        )

    return current_request_url, current_probe, None


def check_login_entry(
    *,
    base_url: str,
    next_path: str = "/gui",
    reason: str = "manual_login",
    timeout_seconds: float = 15.0,
    max_attempts: int = 3,
    retry_delay_seconds: float = 2.0,
    max_retry_delay_seconds: float = 10.0,
    allowed_authorize_hosts: set[str] | None = None,
) -> LoginEntryCheckResult:
    request_url = _build_entry_request_url(base_url, next_path=next_path, reason=reason)
    probe_request_url = request_url
    probe = _send_request_probe(
        request_url=probe_request_url,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        retry_delay_seconds=retry_delay_seconds,
        max_retry_delay_seconds=max_retry_delay_seconds,
        read_body_preview=True,
    )

    probe_request_url, probe, redirect_follow_error = _follow_same_login_redirects(
        phase="entry",
        request_url=probe_request_url,
        probe=probe,
        next_path=next_path,
        reason=reason,
        require_start=False,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        retry_delay_seconds=retry_delay_seconds,
        max_retry_delay_seconds=max_retry_delay_seconds,
    )
    if redirect_follow_error:
        return LoginEntryCheckResult(
            ok=False,
            status_code=probe.status_code,
            location=probe.location,
            request_url=probe_request_url,
            content_type=probe.content_type,
            reason=redirect_follow_error,
        )

    if _is_redirect_status(probe.status_code):
        if not probe.location:
            return LoginEntryCheckResult(
                ok=False,
                status_code=probe.status_code,
                location=probe.location,
                request_url=probe_request_url,
                content_type=probe.content_type,
                reason="entry_redirect_missing_location_header",
            )

        if _is_login_unavailable_redirect(probe.location):
            return LoginEntryCheckResult(
                ok=False,
                status_code=probe.status_code,
                location=probe.location,
                request_url=probe_request_url,
                content_type=probe.content_type,
                reason="entry_redirected_login_unavailable",
            )

        if _is_authorize_redirect(
            probe.location, allowed_authorize_hosts=allowed_authorize_hosts
        ):
            return LoginEntryCheckResult(
                ok=True,
                status_code=probe.status_code,
                location=probe.location,
                request_url=probe_request_url,
                content_type=probe.content_type,
                reason="ok_redirect",
            )

        if _is_auth_login_redirect(probe.location):
            auth_login_query_ok, auth_login_query_reason = (
                _validate_auth_login_redirect_query(
                    location=probe.location,
                    next_path=next_path,
                    reason=reason,
                    phase="entry",
                )
            )
            if not auth_login_query_ok:
                return LoginEntryCheckResult(
                    ok=False,
                    status_code=probe.status_code,
                    location=probe.location,
                    request_url=probe_request_url,
                    content_type=probe.content_type,
                    reason=auth_login_query_reason,
                )

            return LoginEntryCheckResult(
                ok=True,
                status_code=probe.status_code,
                location=probe.location,
                request_url=probe_request_url,
                content_type=probe.content_type,
                reason="ok_redirect",
            )

        return LoginEntryCheckResult(
            ok=False,
            status_code=probe.status_code,
            location=probe.location,
            request_url=probe_request_url,
            content_type=probe.content_type,
            reason="entry_redirect_non_login_target",
        )

    if probe.status_code != 200:
        return LoginEntryCheckResult(
            ok=False,
            status_code=probe.status_code,
            location=probe.location,
            request_url=probe_request_url,
            content_type=probe.content_type,
            reason=f"unexpected_entry_status_{probe.status_code}",
        )

    content_type = str(probe.content_type or "").lower()
    if "text/html" not in content_type:
        return LoginEntryCheckResult(
            ok=False,
            status_code=probe.status_code,
            location=probe.location,
            request_url=probe_request_url,
            content_type=probe.content_type,
            reason="entry_content_type_not_html",
        )

    entry_start_ok, entry_start_reason = _validate_entry_start_link_query(
        body_preview=probe.body_preview,
        next_path=next_path,
        reason=reason,
        request_url=probe_request_url,
    )
    if not entry_start_ok:
        return LoginEntryCheckResult(
            ok=False,
            status_code=probe.status_code,
            location=probe.location,
            request_url=probe_request_url,
            content_type=probe.content_type,
            reason=entry_start_reason,
        )

    return LoginEntryCheckResult(
        ok=True,
        status_code=probe.status_code,
        location=probe.location,
        request_url=probe_request_url,
        content_type=probe.content_type,
        reason="ok",
    )


def check_login_start(
    *,
    base_url: str,
    next_path: str = "/gui",
    reason: str = "manual_login",
    timeout_seconds: float = 15.0,
    max_attempts: int = 3,
    retry_delay_seconds: float = 2.0,
    max_retry_delay_seconds: float = 10.0,
    allowed_authorize_hosts: set[str] | None = None,
) -> LoginStartCheckResult:
    request_url = _build_start_request_url(base_url, next_path=next_path, reason=reason)
    current_request_url = request_url

    first_probe = _send_request_probe(
        request_url=current_request_url,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        retry_delay_seconds=retry_delay_seconds,
        max_retry_delay_seconds=max_retry_delay_seconds,
        read_body_preview=False,
    )

    current_request_url, first_probe, redirect_follow_error = (
        _follow_same_login_redirects(
            phase="start",
            request_url=current_request_url,
            probe=first_probe,
            next_path=next_path,
            reason=reason,
            require_start=True,
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
            retry_delay_seconds=retry_delay_seconds,
            max_retry_delay_seconds=max_retry_delay_seconds,
        )
    )
    first_status = first_probe.status_code
    first_location = first_probe.location
    if redirect_follow_error:
        return LoginStartCheckResult(
            ok=False,
            status_code=first_status,
            location=first_location,
            request_url=current_request_url,
            reason=redirect_follow_error,
        )

    if not _is_redirect_status(first_status):
        return LoginStartCheckResult(
            ok=False,
            status_code=first_status,
            location=first_location,
            request_url=current_request_url,
            reason=f"unexpected_start_status_{first_status}",
        )

    if not first_location:
        return LoginStartCheckResult(
            ok=False,
            status_code=first_status,
            location=first_location,
            request_url=current_request_url,
            reason="missing_location_header",
        )

    if _is_login_unavailable_redirect(first_location):
        return LoginStartCheckResult(
            ok=False,
            status_code=first_status,
            location=first_location,
            request_url=current_request_url,
            reason="login_unavailable_fallback",
        )

    if _is_authorize_redirect(
        first_location, allowed_authorize_hosts=allowed_authorize_hosts
    ):
        return LoginStartCheckResult(
            ok=True,
            status_code=first_status,
            location=first_location,
            request_url=current_request_url,
            reason="ok",
        )

    if not _is_auth_login_redirect(first_location):
        return LoginStartCheckResult(
            ok=False,
            status_code=first_status,
            location=first_location,
            request_url=current_request_url,
            reason="location_is_not_authorize_or_auth_login_redirect",
        )

    auth_login_query_ok, auth_login_query_reason = _validate_auth_login_redirect_query(
        location=first_location,
        next_path=next_path,
        reason=reason,
        phase="start",
    )
    if not auth_login_query_ok:
        return LoginStartCheckResult(
            ok=False,
            status_code=first_status,
            location=first_location,
            request_url=current_request_url,
            reason=auth_login_query_reason,
        )

    second_request_url = urljoin(current_request_url, first_location)
    second_status, second_location = _send_request(
        request_url=second_request_url,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        retry_delay_seconds=retry_delay_seconds,
        max_retry_delay_seconds=max_retry_delay_seconds,
    )

    if not _is_redirect_status(second_status):
        return LoginStartCheckResult(
            ok=False,
            status_code=second_status,
            location=second_location,
            request_url=current_request_url,
            reason=f"auth_login_hop_unexpected_status_{second_status}",
        )

    if not second_location:
        return LoginStartCheckResult(
            ok=False,
            status_code=second_status,
            location=second_location,
            request_url=current_request_url,
            reason="auth_login_hop_missing_location_header",
        )

    if _is_login_unavailable_redirect(second_location):
        return LoginStartCheckResult(
            ok=False,
            status_code=second_status,
            location=second_location,
            request_url=current_request_url,
            reason="auth_login_hop_login_unavailable_fallback",
        )

    if not _is_authorize_redirect(
        second_location, allowed_authorize_hosts=allowed_authorize_hosts
    ):
        return LoginStartCheckResult(
            ok=False,
            status_code=second_status,
            location=second_location,
            request_url=current_request_url,
            reason="auth_login_hop_non_authorize_redirect",
        )

    return LoginStartCheckResult(
        ok=True,
        status_code=second_status,
        location=second_location,
        request_url=current_request_url,
        reason="ok",
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke-check UI-owned login entry + login-start redirect contract"
    )
    parser.add_argument(
        "--base-url",
        default="",
        help="UI base URL, e.g. https://www.dev.georanking.ch",
    )
    parser.add_argument(
        "--ui-base-url",
        default="",
        help="Alias for --base-url",
    )
    parser.add_argument(
        "--next",
        default="/gui",
        dest="next_path",
        help="next path for login start (default: /gui)",
    )
    parser.add_argument(
        "--reason",
        default="manual_login",
        help="login reason query value (default: manual_login)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP timeout per attempt in seconds (default: 15)",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Max HTTP attempts per hop on transient request errors (default: 3)",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=2.0,
        help="Delay between retries in seconds (default: 2.0)",
    )
    parser.add_argument(
        "--max-retry-delay",
        type=float,
        default=10.0,
        help="Upper bound for effective retry sleep per attempt in seconds (default: 10.0)",
    )
    parser.add_argument(
        "--output-json",
        "--json-out",
        dest="output_json",
        help="Optional output path for machine-readable result",
    )
    parser.add_argument(
        "--expected-authorize-host",
        help=(
            "Optional comma-separated allow-list for absolute authorize redirect hosts "
            "(accepts hostnames, host:port, or full URLs; e.g. "
            "auth.dev.georanking.ch,www.dev.georanking.ch). Defaults to derived "
            "auth.<base-host> + <base-host> variants for non-local origins "
            "(localhost/IP origins keep host checks disabled)."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress stdout JSON payloads (artifacts via --output-json remain unchanged)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Backward-compatible no-op alias (stdout JSON is always emitted unless --quiet)",
    )
    return parser.parse_args(argv)


def _write_result(path: str, payload: dict[str, object]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _emit_payload(payload: dict[str, object], *, quiet: bool) -> None:
    if quiet:
        return
    print(json.dumps(payload, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])

    base_url = str(args.base_url or "").strip()
    ui_base_url = str(args.ui_base_url or "").strip()
    if not base_url and not ui_base_url:
        payload = {
            "ok": False,
            "phase": "request",
            "reason": "invalid_arguments:base_url_required",
            "request": {
                "base_url": base_url,
                "ui_base_url": ui_base_url,
            },
        }
        _emit_payload(payload, quiet=args.quiet)
        if args.output_json:
            _write_result(args.output_json, payload)
        return 2

    effective_base_url = _canonicalize_base_url_trailing_dot(base_url or ui_base_url)

    explicit_authorize_hosts = _parse_allowed_authorize_hosts(
        args.expected_authorize_host
    )
    if explicit_authorize_hosts:
        allowed_authorize_hosts = explicit_authorize_hosts
        expected_authorize_host_source = "argument"
    else:
        allowed_authorize_hosts = _derive_default_allowed_authorize_hosts(
            effective_base_url
        )
        expected_authorize_host_source = (
            "derived_default" if allowed_authorize_hosts else "none"
        )

    request_meta = {
        "base_url": effective_base_url,
        "ui_base_url": ui_base_url,
        "next": args.next_path,
        "reason": args.reason,
        "timeout": args.timeout,
        "max_attempts": args.max_attempts,
        "retry_delay": args.retry_delay,
        "max_retry_delay": args.max_retry_delay,
        "expected_authorize_host": sorted(allowed_authorize_hosts),
        "expected_authorize_host_source": expected_authorize_host_source,
    }

    try:
        entry_result = check_login_entry(
            base_url=effective_base_url,
            next_path=args.next_path,
            reason=args.reason,
            timeout_seconds=args.timeout,
            max_attempts=args.max_attempts,
            retry_delay_seconds=args.retry_delay,
            max_retry_delay_seconds=args.max_retry_delay,
            allowed_authorize_hosts=allowed_authorize_hosts,
        )
        if not entry_result.ok:
            payload = {
                "ok": False,
                "phase": "entry",
                "reason": entry_result.reason,
                "status_code": entry_result.status_code,
                "request_url": entry_result.request_url,
                "location": entry_result.location,
                "content_type": entry_result.content_type,
                "request": request_meta,
            }
            _emit_payload(payload, quiet=args.quiet)
            if args.output_json:
                _write_result(args.output_json, payload)
            return 1

        start_result = check_login_start(
            base_url=effective_base_url,
            next_path=args.next_path,
            reason=args.reason,
            timeout_seconds=args.timeout,
            max_attempts=args.max_attempts,
            retry_delay_seconds=args.retry_delay,
            max_retry_delay_seconds=args.max_retry_delay,
            allowed_authorize_hosts=allowed_authorize_hosts,
        )
    except Exception as exc:  # noqa: BLE001
        payload = {
            "ok": False,
            "phase": "request",
            "reason": _classify_request_failure(exc),
            "error": str(exc),
            "request": request_meta,
        }
        _emit_payload(payload, quiet=args.quiet)
        if args.output_json:
            _write_result(args.output_json, payload)
        return 1

    payload = {
        "ok": start_result.ok,
        "phase": "start",
        "reason": start_result.reason,
        "status_code": start_result.status_code,
        "request_url": start_result.request_url,
        "location": start_result.location,
        "request": request_meta,
        "entry": {
            "ok": entry_result.ok,
            "reason": entry_result.reason,
            "status_code": entry_result.status_code,
            "request_url": entry_result.request_url,
            "location": entry_result.location,
            "content_type": entry_result.content_type,
        },
    }
    _emit_payload(payload, quiet=args.quiet)
    if args.output_json:
        _write_result(args.output_json, payload)

    return 0 if start_result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
