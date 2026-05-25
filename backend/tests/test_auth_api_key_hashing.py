import hashlib

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from app.db.base import Base
from app.domain.auth.deps import get_current_user
from app.domain.auth.models import APIKey
from app.domain.auth.security import hash_api_key, hash_api_key_lookup, verify_api_key_hash


def _make_db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return session_local()


def _make_request_with_api_key(raw_key: str) -> Request:
    scope = {"type": "http", "headers": [(b"x-api-key", raw_key.encode("utf-8"))]}
    return Request(scope)


def test_hash_api_key_uses_versioned_salted_format(monkeypatch):
    monkeypatch.setenv("API_KEY_PEPPER", "test-pepper")
    monkeypatch.setenv("API_KEY_PBKDF2_ITERATIONS", "150000")

    raw = "api-key-123"
    hash_a = hash_api_key(raw)
    hash_b = hash_api_key(raw)

    algo, iters, salt_hex, digest_hex = hash_a.split("$")
    assert algo == "pbkdf2_sha256"
    assert iters == "150000"
    assert len(salt_hex) == 32
    assert len(digest_hex) == 64
    assert hash_a != hash_b
    assert verify_api_key_hash(raw, hash_a)


def test_hash_api_key_requires_explicit_dev_test_env_for_default_pepper(monkeypatch):
    monkeypatch.delenv("API_KEY_PEPPER", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)

    with pytest.raises(RuntimeError):
        hash_api_key("api-key-123")


def test_verify_api_key_hash_supports_legacy_pbkdf2_three_part_format(monkeypatch):
    monkeypatch.setenv("API_KEY_PEPPER", "legacy-pepper")

    raw = "legacy-pbkdf2-key"
    iterations = 120000
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        raw.encode("utf-8"),
        b"legacy-pepper",
        iterations,
    ).hex()
    stored = f"pbkdf2_sha256${iterations}${dk}"
    assert verify_api_key_hash(raw, stored)


def test_verify_api_key_hash_rejects_malformed_values(monkeypatch):
    monkeypatch.setenv("API_KEY_PEPPER", "test-pepper")

    assert not verify_api_key_hash("k", "pbkdf2_sha256$120000$abc$" + ("0" * 64))
    assert not verify_api_key_hash("k", "pbkdf2_sha256$999999999$" + ("00" * 16) + "$" + ("0" * 64))


def test_get_current_user_rejects_non_pbkdf2_api_key_hash_entries(monkeypatch):
    monkeypatch.setenv("API_KEY_PEPPER", "test-pepper")

    raw = "legacy-hash-format-key"
    db = _make_db_session()
    try:
        db.add(
            APIKey(
                name="legacy-admin",
                api_key_hash="a" * 64,
                is_active=True,
                is_admin=True,
            )
        )
        db.commit()

        try:
            get_current_user(_make_request_with_api_key(raw), creds=None, db=db)
            raise AssertionError("Expected HTTPException")
        except HTTPException as exc:
            assert exc.status_code == 401
    finally:
        db.close()


def test_get_current_user_accepts_pbkdf2_hashes_after_iteration_change(monkeypatch):
    monkeypatch.setenv("API_KEY_PEPPER", "pbkdf2-pepper")
    monkeypatch.setenv("API_KEY_PBKDF2_ITERATIONS", "150000")

    raw = "pbkdf2-admin-key"
    stored_hash = hash_api_key(raw)
    stored_lookup = hash_api_key_lookup(raw)

    db = _make_db_session()
    try:
        db.add(
            APIKey(
                name="pbkdf2-admin",
                api_key_lookup=stored_lookup,
                api_key_hash=stored_hash,
                is_active=True,
                is_admin=True,
            )
        )
        db.commit()

        monkeypatch.setenv("API_KEY_PBKDF2_ITERATIONS", "310000")
        user = get_current_user(_make_request_with_api_key(raw), creds=None, db=db)
        assert user.is_admin is True
        assert user.email == "api-key:pbkdf2-admin"
    finally:
        db.close()


def test_get_current_user_rejects_invalid_api_key(monkeypatch):
    monkeypatch.setenv("API_KEY_PEPPER", "test-pepper")
    db = _make_db_session()
    try:
        try:
            get_current_user(_make_request_with_api_key("wrong"), creds=None, db=db)
            raise AssertionError("Expected HTTPException")
        except HTTPException as exc:
            assert exc.status_code == 401
    finally:
        db.close()
