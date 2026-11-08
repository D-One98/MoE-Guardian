import base64
import hashlib
import hmac
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.repositories.governance_repo import GovernanceRepository
from app.schemas.contracts import DemoRole
from app.services.seed_data import DEMO_ORG_ID

ORG_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,64}$")


@dataclass(frozen=True)
class TenantContext:
    org_id: str
    user_id: str
    role: Optional[DemoRole]
    is_demo_fallback: bool
    auth_mode: str


def _b64url_decode(segment: str) -> bytes:
    rem = len(segment) % 4
    if rem > 0:
        segment += "=" * (4 - rem)
    return base64.urlsafe_b64decode(segment.encode("ascii"))


def create_hs256_jwt(payload: Dict[str, Any], secret: str) -> str:
    """
    Utility for generating standards-compliant HS256 JWTs for local/integration testing.
    """
    header = {"alg": "HS256", "typ": "JWT"}
    h_b64 = base64.urlsafe_b64encode(
        json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).rstrip(b"=").decode("ascii")
    p_b64 = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).rstrip(b"=").decode("ascii")
    signing_input = f"{h_b64}.{p_b64}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    s_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")
    return f"{h_b64}.{p_b64}.{s_b64}"


def verify_supabase_jwt(
    token: str,
    jwt_secret: str,
    expected_issuer: Optional[str] = None,
    expected_audience: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Verifies a Bearer JWT's cryptographic signature (HS256), expiration (exp),
    not-before (nbf), issuer (iss), audience (aud), and subject (sub).
    Fails closed on any malformed, unsigned, expired, or mismatched claim.
    """
    if not jwt_secret or not jwt_secret.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "JWT_SECRET_NOT_CONFIGURED",
                "message": "Server JWT verification secret (SUPABASE_JWT_SECRET) is not configured.",
            },
        )

    parts = token.strip().split(".")
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "MALFORMED_JWT", "message": "Bearer token is not a valid 3-part JWT."},
        )

    header_b64, payload_b64, signature_b64 = parts
    try:
        header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
        claims = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        provided_sig = _b64url_decode(signature_b64)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "INVALID_JWT_ENCODING", "message": "Failed to decode JWT segments."},
        ) from exc

    if not isinstance(header, dict) or not isinstance(claims, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "INVALID_JWT_STRUCTURE", "message": "JWT header and payload must be JSON objects."},
        )

    alg = header.get("alg")
    if alg != "HS256":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNSUPPORTED_JWT_ALG", "message": f"Unsupported or insecure JWT algorithm '{alg}'. Expected HS256."},
        )

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(
        jwt_secret.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    if not hmac.compare_digest(provided_sig, expected_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "INVALID_JWT_SIGNATURE", "message": "JWT cryptographic signature verification failed."},
        )

    now_ts = int(time.time())

    # Validate expiration (exp is mandatory)
    exp = claims.get("exp")
    if not isinstance(exp, (int, float)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "MISSING_JWT_EXP", "message": "JWT is missing required numeric 'exp' claim."},
        )
    if now_ts >= int(exp):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "EXPIRED_JWT", "message": "JWT token has expired."},
        )

    # Validate not-before (nbf) if present
    nbf = claims.get("nbf")
    if nbf is not None:
        if not isinstance(nbf, (int, float)) or now_ts < int(nbf):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "JWT_NOT_YET_VALID", "message": "JWT 'nbf' claim is in the future."},
            )

    # Validate issuer (iss) if configured
    if expected_issuer and expected_issuer.strip():
        iss = claims.get("iss")
        if iss != expected_issuer.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "INVALID_JWT_ISSUER", "message": "JWT issuer ('iss') does not match expected issuer."},
            )

    # Validate audience (aud) if configured
    if expected_audience and expected_audience.strip():
        target_aud = expected_audience.strip()
        aud: Union[str, list, None] = claims.get("aud")
        aud_valid = (
            (isinstance(aud, str) and aud == target_aud)
            or (isinstance(aud, list) and target_aud in aud)
        )
        if not aud_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "INVALID_JWT_AUDIENCE", "message": "JWT audience ('aud') does not match expected audience."},
            )

    # Validate subject (sub)
    sub = claims.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "MISSING_JWT_SUB", "message": "JWT is missing required non-empty 'sub' (user_id) claim."},
        )

    return claims


def _bind_postgres_rls_context(db: Session, org_id: str, user_id: str, role: str) -> None:
    """
    Sets transaction-local PostgreSQL session variables for Row-Level Security (RLS) defence-in-depth
    when connected to a PostgreSQL database. Safe no-op on SQLite.
    """
    bind = db.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        db.execute(
            text(
                "SELECT set_config('app.current_org_id', :org_id, true), "
                "set_config('app.current_user_id', :user_id, true), "
                "set_config('app.current_role', :role, true)"
            ),
            {"org_id": org_id, "user_id": user_id, "role": role},
        )


def get_tenant_context(
    authorization: Optional[str] = Header(default=None),
    x_demo_org_id: Optional[str] = Header(default=None, alias="X-Demo-Org-Id"),
    db: Session = Depends(get_db),
) -> TenantContext:
    """
    Server-side tenant resolution & authentication boundary:
    1. If a Bearer token is supplied OR if REQUIRE_VERIFIED_TENANT_AUTH=true (or APP_ENV=production),
       verifies the JWT signature, iss, aud, exp, and sub.
    2. Looks up the authenticated user's active organisation membership and role in the
       server-side `organization_memberships` table (never trusting client-supplied org_id or role).
    3. Only when REQUIRE_VERIFIED_TENANT_AUTH=false in non-production environments and no Bearer
       token is provided, falls back to the clearly labelled demo simulation context.
    """
    app_env = os.getenv("APP_ENV", settings.app_env).lower()
    require_auth = (
        os.getenv("REQUIRE_VERIFIED_TENANT_AUTH", str(settings.require_verified_tenant_auth)).lower() == "true"
        or app_env == "production"
    )

    has_bearer = bool(authorization and authorization.strip().lower().startswith("bearer "))

    if require_auth or has_bearer:
        if not has_bearer or authorization is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "UNAUTHORIZED_TENANT_CONTEXT",
                    "message": "Bearer JWT token is required for authenticated tenant access.",
                },
            )

        raw_token = authorization.strip()[7:].strip()
        jwt_secret = os.getenv("SUPABASE_JWT_SECRET", settings.supabase_jwt_secret)
        jwt_issuer = os.getenv("SUPABASE_JWT_ISSUER", settings.supabase_jwt_issuer)
        jwt_audience = os.getenv("SUPABASE_JWT_AUDIENCE", settings.supabase_jwt_audience)

        claims = verify_supabase_jwt(
            token=raw_token,
            jwt_secret=jwt_secret,
            expected_issuer=jwt_issuer if jwt_issuer else None,
            expected_audience=jwt_audience if jwt_audience else None,
        )

        user_id = claims["sub"].strip()
        repo = GovernanceRepository(db)

        # If the client requests a specific tenant via header or JWT claim, verify active server-side membership!
        requested_org: Optional[str] = None
        if x_demo_org_id is not None and x_demo_org_id.strip():
            requested_org = x_demo_org_id.strip()
        elif isinstance(claims.get("org_id"), str) and claims["org_id"].strip():
            requested_org = claims["org_id"].strip()

        if requested_org is not None:
            if not ORG_ID_PATTERN.match(requested_org):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": "INVALID_ORG_ID", "message": "Invalid organisation identifier format."},
                )
            membership = repo.get_active_membership(user_id=user_id, org_id=requested_org)
        else:
            active_memberships = repo.list_active_memberships_for_user(user_id=user_id)
            if len(active_memberships) > 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "AMBIGUOUS_TENANT_MEMBERSHIP_SELECTION_REQUIRED",
                        "message": (
                            f"Authenticated user '{user_id}' belongs to multiple active organisations. "
                            "Explicitly specify the target organisation via 'X-Demo-Org-Id' header or JWT 'org_id' claim."
                        ),
                    },
                )
            membership = active_memberships[0] if len(active_memberships) == 1 else None

        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "TENANT_MEMBERSHIP_DENIED",
                    "message": f"Authenticated user '{user_id}' has no active server-side membership for the requested organisation.",
                },
            )

        verified_role = DemoRole(membership.role)
        _bind_postgres_rls_context(db, membership.org_id, user_id, verified_role.value)

        return TenantContext(
            org_id=membership.org_id,
            user_id=user_id,
            role=verified_role,
            is_demo_fallback=False,
            auth_mode="VERIFIED_JWT_SERVER_MEMBERSHIP",
        )

    # Demo fallback (strictly non-production when REQUIRE_VERIFIED_TENANT_AUTH=false)
    if x_demo_org_id is not None:
        cleaned_org = x_demo_org_id.strip()
        if not ORG_ID_PATTERN.match(cleaned_org):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_ORG_ID_HEADER",
                    "message": "X-Demo-Org-Id must be 3-64 alphanumeric, dash, or underscore characters.",
                },
            )
        return TenantContext(
            org_id=cleaned_org,
            user_id="demo-admin-sim",
            role=None,
            is_demo_fallback=True,
            auth_mode="DEMO_HEADER_SCOPED_SIMULATION",
        )

    return TenantContext(
        org_id=DEMO_ORG_ID,
        user_id="demo-default-user",
        role=None,
        is_demo_fallback=True,
        auth_mode="DEMO_DEFAULT_ORG_SIMULATION",
    )