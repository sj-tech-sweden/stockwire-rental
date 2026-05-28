import pytest

from app.domain.auth.security import hash_password, validate_password_pepper, verify_password


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
