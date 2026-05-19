"""Basit Bearer token auth — Phase 2.5'te yeterli.

Environment:
    API_BEARER_TOKEN    — admin endpoints için
    PUBLIC_READ         — true ise GET endpoint'ler auth'suz

Phase 3'te Auth0/Clerk/Supabase Auth ile değiştirilebilir.
"""
from __future__ import annotations

import os

from fastapi import Header, HTTPException, status


def _expected_token() -> str | None:
    return os.environ.get("API_BEARER_TOKEN")


def _public_read() -> bool:
    return os.environ.get("PUBLIC_READ", "true").lower() in ("1", "true", "yes")


def require_bearer(authorization: str | None = Header(default=None)) -> str:
    """Admin-only endpoints için. Header: `Authorization: Bearer <token>`."""
    expected = _expected_token()
    if not expected:
        # Token ayarlanmamışsa development modunda izin ver
        return "dev"

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:].strip()
    if token != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid bearer token",
        )

    return token


def optional_bearer(authorization: str | None = Header(default=None)) -> str | None:
    """Read endpoint'ler — PUBLIC_READ true ise herkes, değilse token zorunlu."""
    if _public_read():
        return "public"
    return require_bearer(authorization)
