"""Minimal DB access layer — user/org/membership bootstrap + OIDC claim mapping.

Issues: #814 (DB-0.wp3 — bootstrap), #820 (OIDC-0.wp4 — claim mapping)
Depends on: #813 (migration runner), #812 (schema v1)

Public API:
- ``get_or_create_user_by_external_subject`` — bootstrap (create-or-find user + membership)
- ``get_or_create_default_org`` — auto_org bootstrap helper
- ``ensure_membership`` — idempotent membership upsert
- ``resolve_oidc_subject`` — read-only claim mapping: sub -> (user_id, org_id, roles)

## Bootstrap Policy

### User creation
- ``get_or_create_user_by_external_subject`` is idempotent.
  On first login (unknown ``external_subject``), a new ``users`` row is
  inserted.  Subsequent calls with the same subject return the existing row.

### Org / Membership creation
Two policies are supported, selected via ``org_policy``:

``"invite_only"`` (default — recommended for production):
  - No org is created automatically.
  - The caller *must* supply a valid ``org_id`` and call
    ``ensure_membership`` explicitly after validating the invitation.
  - ``get_or_create_user_by_external_subject`` with ``org_policy="invite_only"``
    (or no ``org_id``) creates the user row but does NOT create any org or
    membership.

``"auto_org"`` (development / single-tenant bootstrap):
  - If ``org_id`` is supplied the user is added to that org.
  - If ``org_id`` is *not* supplied, a default org (slug ``default``) is
    looked up or created and the user is added with role ``member``.
  - This policy is intentionally opt-in and **must not be enabled in
    production** without explicit acknowledgement.

### Log safety
- User ``id`` (UUID) and org ``id`` (UUID) are safe to log.
- ``external_subject`` (OIDC ``sub``) is considered PII; it is NOT emitted
  to logs.  Only the fingerprint (first 8 chars of sha256) may appear in
  debug output.
- No plaintext tokens, keys, or hashes are logged.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default org for auto_org bootstrap.
_DEFAULT_ORG_SLUG = "default"
_DEFAULT_ORG_DISPLAY_NAME = "Default Organization"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _subject_fingerprint(subject: str) -> str:
    """Return a short, non-reversible fingerprint of an OIDC subject.

    Safe to include in log lines — not the actual sub value.
    """
    return hashlib.sha256(subject.encode("utf-8")).hexdigest()[:8]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_or_create_user_by_external_subject(
    conn: Any,
    subject: str,
    *,
    email: str | None = None,
    org_id: str | None = None,
    org_policy: str = "invite_only",
    default_membership_role: str = "member",
) -> dict[str, Any]:
    """Look up a user by their OIDC ``sub``; create if not found.

    Args:
        conn:                    psycopg2 connection (must support cursor()).
        subject:                 Stable external identity (OIDC ``sub``).
        email:                   Optional email address (stored if provided).
        org_id:                  Optional UUID of an existing org to join.
        org_policy:              ``"invite_only"`` (default) or ``"auto_org"``.
        default_membership_role: Role to assign when ensuring membership
                                 (default: ``"member"``).

    Returns:
        dict with keys: ``id``, ``external_subject``, ``email``,
        ``created_at``, ``updated_at``, ``_created`` (bool — True if this
        call inserted the row).

    Raises:
        ValueError: if ``subject`` is empty or ``org_policy`` is unknown.
    """

    subject = str(subject or "").strip()
    if not subject:
        raise ValueError("subject must be non-empty")

    org_policy = str(org_policy or "").strip().lower()
    if org_policy not in ("invite_only", "auto_org"):
        raise ValueError(f"unknown org_policy: {org_policy!r}; use 'invite_only' or 'auto_org'")

    fp = _subject_fingerprint(subject)

    with conn.cursor() as cur:
        # --- Upsert user row ------------------------------------------------
        cur.execute(
            """
            INSERT INTO users (external_subject, email)
            VALUES (%s, %s)
            ON CONFLICT (external_subject) DO NOTHING
            RETURNING id, external_subject, email, created_at, updated_at
            """,
            (subject, email),
        )
        row = cur.fetchone()

        if row is not None:
            # Newly inserted.
            user = _row_to_user_dict(cur, row, created=True)
            logger.info(
                "db_access.user_created",
                extra={"user_id": str(user["id"]), "subject_fp": fp},
            )
        else:
            # Already exists — fetch.
            cur.execute(
                """
                SELECT id, external_subject, email, created_at, updated_at
                FROM users
                WHERE external_subject = %s
                """,
                (subject,),
            )
            existing_row = cur.fetchone()
            if existing_row is None:
                # Should not happen in normal operation.
                raise RuntimeError(
                    f"user with subject_fp={fp} disappeared between INSERT and SELECT"
                )
            user = _row_to_user_dict(cur, existing_row, created=False)
            logger.debug(
                "db_access.user_found",
                extra={"user_id": str(user["id"]), "subject_fp": fp},
            )

    # --- Org / Membership bootstrap -----------------------------------------
    if org_policy == "auto_org":
        resolved_org_id = org_id
        if resolved_org_id is None:
            default_org = get_or_create_default_org(conn)
            resolved_org_id = str(default_org["id"])
        ensure_membership(conn, resolved_org_id, str(user["id"]), role=default_membership_role)
    # invite_only: do nothing — caller handles org assignment explicitly.

    return user


def get_or_create_default_org(
    conn: Any,
    *,
    slug: str = _DEFAULT_ORG_SLUG,
    display_name: str = _DEFAULT_ORG_DISPLAY_NAME,
) -> dict[str, Any]:
    """Return (or create) the default organisation by slug.

    Intended for ``auto_org`` bootstrap scenarios only.  In production
    (``invite_only`` policy) this function should not be called.

    Args:
        conn:         psycopg2 connection.
        slug:         Unique org slug (default: ``"default"``).
        display_name: Human-readable org name for newly inserted rows.

    Returns:
        dict with keys: ``id``, ``slug``, ``display_name``, ``created_at``,
        ``updated_at``, ``_created`` (bool).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO organizations (slug, display_name)
            VALUES (%s, %s)
            ON CONFLICT (slug) DO NOTHING
            RETURNING id, slug, display_name, created_at, updated_at
            """,
            (slug, display_name),
        )
        row = cur.fetchone()
        if row is not None:
            org = _row_to_org_dict(cur, row, created=True)
            logger.info("db_access.org_created", extra={"org_id": str(org["id"]), "slug": slug})
            return org

        cur.execute(
            "SELECT id, slug, display_name, created_at, updated_at FROM organizations WHERE slug = %s",
            (slug,),
        )
        existing = cur.fetchone()
        if existing is None:
            raise RuntimeError(f"org slug={slug!r} disappeared between INSERT and SELECT")
        org = _row_to_org_dict(cur, existing, created=False)
        logger.debug("db_access.org_found", extra={"org_id": str(org["id"]), "slug": slug})
        return org


def ensure_membership(
    conn: Any,
    org_id: str,
    user_id: str,
    *,
    role: str = "member",
) -> dict[str, Any]:
    """Ensure a membership record exists for (org_id, user_id).

    Idempotent: if the record already exists the existing row is returned
    and no UPDATE is performed (role is not changed on conflict).

    Args:
        conn:    psycopg2 connection.
        org_id:  UUID of the target organization.
        user_id: UUID of the user.
        role:    Role to assign when *creating* a new membership row.

    Returns:
        dict with keys: ``id``, ``org_id``, ``user_id``, ``role``,
        ``created_at``, ``_created`` (bool — True if this call inserted).

    Raises:
        ValueError: if ``org_id`` or ``user_id`` are empty.
    """
    org_id = str(org_id or "").strip()
    user_id = str(user_id or "").strip()
    if not org_id:
        raise ValueError("org_id must be non-empty")
    if not user_id:
        raise ValueError("user_id must be non-empty")

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO memberships (org_id, user_id, role)
            VALUES (%s::uuid, %s::uuid, %s)
            ON CONFLICT (org_id, user_id) DO NOTHING
            RETURNING id, org_id, user_id, role, created_at
            """,
            (org_id, user_id, role),
        )
        row = cur.fetchone()
        if row is not None:
            membership = _row_to_membership_dict(cur, row, created=True)
            logger.info(
                "db_access.membership_created",
                extra={"org_id": org_id, "user_id": user_id, "role": role},
            )
            return membership

        cur.execute(
            """
            SELECT id, org_id, user_id, role, created_at
            FROM memberships
            WHERE org_id = %s::uuid AND user_id = %s::uuid
            """,
            (org_id, user_id),
        )
        existing = cur.fetchone()
        if existing is None:
            raise RuntimeError(
                f"membership org_id={org_id} user_id={user_id} disappeared between INSERT and SELECT"
            )
        membership = _row_to_membership_dict(cur, existing, created=False)
        logger.debug(
            "db_access.membership_exists",
            extra={"org_id": org_id, "user_id": user_id},
        )
        return membership


# ---------------------------------------------------------------------------
# OIDC Subject Resolution  (Issue: #820 — OIDC-0.wp4)
# ---------------------------------------------------------------------------

def resolve_oidc_subject(
    conn: Any,
    subject: str,
) -> dict[str, Any] | None:
    """Resolve an OIDC ``sub`` claim to internal user + org/role context.

    This is the canonical "claim-mapping" function used by the auth layer to
    turn an incoming JWT ``sub`` into an actionable identity:

        (subject) -> { user_id, org_id, roles, memberships }

    Behaviour:
    - Returns ``None`` if the subject is unknown (user not yet registered).
      The auth layer MUST treat ``None`` as a 401/403 (user not found /
      no access).
    - If the user exists but has **no membership**, returns a dict with
      ``org_id=None`` and ``roles=[]``.  The auth layer MUST treat this as
      a 403 (user exists but has no org — invite not yet accepted or
      invite_only policy: no auto-org).
    - If the user has **one membership** (common case), returns that org's
      id and role list.
    - If the user has **multiple memberships**, all are returned in
      ``memberships``; ``org_id`` and ``roles`` reflect the **first** record
      (oldest by ``created_at``).  Callers that need multi-org support should
      inspect ``memberships`` directly and pick the correct org from request
      context (e.g. a header or token claim).

    ## Policy (invite_only vs auto_org)
    This function is a **read-only lookup** — it never creates users or orgs.
    Policy enforcement (whether to auto-create on miss) belongs to the
    registration / bootstrap path (``get_or_create_user_by_external_subject``).
    The auth layer should:
    - ``invite_only`` (production default): return 403 if ``org_id`` is
      ``None`` (user has no membership → invite not accepted).
    - ``auto_org`` (dev/single-tenant): in the bootstrap path, ensure
      membership via ``get_or_create_user_by_external_subject`` before the
      first protected request; after that, ``resolve_oidc_subject`` returns
      the created membership.

    Args:
        conn:    psycopg2 connection.
        subject: Stable external identity from the OIDC JWT (``sub`` claim).
                 Must be non-empty.

    Returns:
        ``None`` if the subject is not found, otherwise a dict:
        - ``user_id``    (str UUID)
        - ``org_id``     (str UUID | None)
        - ``roles``      (list[str])
        - ``memberships`` (list[dict] — each has ``org_id``, ``role``, ``id``)

    Raises:
        ValueError: if ``subject`` is empty.
    """
    subject = str(subject or "").strip()
    if not subject:
        raise ValueError("subject must be non-empty")

    fp = _subject_fingerprint(subject)

    with conn.cursor() as cur:
        # Step 1: look up user by external_subject.
        cur.execute(
            """
            SELECT id, external_subject, email, created_at, updated_at
            FROM users
            WHERE external_subject = %s
            """,
            (subject,),
        )
        user_row = cur.fetchone()

    if user_row is None:
        logger.debug(
            "db_access.resolve_subject_not_found",
            extra={"subject_fp": fp},
        )
        return None

    # Build user dict manually (cursor is closed after 'with' block above).
    # We only need the id; re-use the column order from the SELECT above.
    user_id = str(user_row[0])

    logger.debug(
        "db_access.resolve_subject_found",
        extra={"user_id": user_id, "subject_fp": fp},
    )

    # Step 2: fetch all memberships for this user (ordered oldest first).
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, org_id, user_id, role, created_at
            FROM memberships
            WHERE user_id = %s::uuid
            ORDER BY created_at ASC
            """,
            (user_id,),
        )
        rows = cur.fetchall()
        col_names = _col_names(cur)

    memberships = [dict(zip(col_names, row)) for row in rows]
    # Stringify UUIDs for consistency.
    for m in memberships:
        m["id"] = str(m["id"])
        m["org_id"] = str(m["org_id"])
        m["user_id"] = str(m["user_id"])

    if memberships:
        primary = memberships[0]
        org_id: str | None = primary["org_id"]
        roles: list[str] = [m["role"] for m in memberships]
        logger.debug(
            "db_access.resolve_memberships_found",
            extra={"user_id": user_id, "count": len(memberships)},
        )
    else:
        org_id = None
        roles = []
        logger.info(
            "db_access.resolve_no_membership",
            extra={"user_id": user_id},
        )

    return {
        "user_id": user_id,
        "org_id": org_id,
        "roles": roles,
        "memberships": memberships,
    }


# ---------------------------------------------------------------------------
# Row → dict helpers
# ---------------------------------------------------------------------------

def _col_names(cursor: Any) -> list[str]:
    """Return column names from cursor.description."""
    return [desc[0] for desc in cursor.description]


def _row_to_user_dict(cursor: Any, row: tuple, *, created: bool) -> dict[str, Any]:
    cols = _col_names(cursor)
    d = dict(zip(cols, row))
    d["_created"] = created
    return d


def _row_to_org_dict(cursor: Any, row: tuple, *, created: bool) -> dict[str, Any]:
    cols = _col_names(cursor)
    d = dict(zip(cols, row))
    d["_created"] = created
    return d


def _row_to_membership_dict(cursor: Any, row: tuple, *, created: bool) -> dict[str, Any]:
    cols = _col_names(cursor)
    d = dict(zip(cols, row))
    d["_created"] = created
    return d
