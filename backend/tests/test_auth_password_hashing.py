import hashlib

import bcrypt
import pytest

from app.domain.auth.security import hash_password, validate_password_pepper, verify_password


def test_verify_password_accepts_legacy_sha256_prehashed_long_password():
    plain = "p" * 100
    legacy_prepared = hashlib.sha256(plain.encode("utf-8")).digest()
    legacy_hash = bcrypt.hashpw(legacy_prepared, bcrypt.gensalt()).decode("utf-8")
    assert verify_password(plain, legacy_hash)


def test_hash_and_verify_long_password_with_password_pepper(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PASSWORD_PEPPER", "test-password-pepper")
    plain = "x" * 100
    hashed = hash_password(plain)
    assert verify_password(plain, hashed)


def test_validate_password_pepper_requires_env_outside_dev_test(monkeypatch):
    monkeypatch.delenv("PASSWORD_PEPPER", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    with pytest.raises(RuntimeError):
        validate_password_pepper()
