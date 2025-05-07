"""
Tests specifically designed to improve code coverage for dependencies.
This module focuses on edge cases and error handling paths in the dependencies.
"""

import pytest
import jwt
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_current_user, get_current_active_user, require_role,
    get_db, get_email_service, get_settings
)
from app.models.user_model import User, UserRole
from app.services.user_service import UserService
from app.services.jwt_service import create_access_token


def test_get_current_user_invalid_token():
    """get_current_user should raise when decode_token fails."""
    token = "invalid_token"
    with patch("app.dependencies.decode_token", return_value=None):
        with pytest.raises(HTTPException) as excinfo:
            get_current_user(token)
        assert excinfo.value.status_code == 401
        assert "Could not validate credentials" in excinfo.value.detail


def test_get_current_user_missing_sub():
    """If token payload lacks required claims, raise 401."""
    token = "token_without_sub"
    with patch("app.dependencies.decode_token", return_value={}):
        with pytest.raises(HTTPException):
            get_current_user(token)


def test_get_current_user_valid():
    """Valid token returns user dict."""
    token = "valid_token"
    payload = {"sub": "user@example.com", "role": "AUTHENTICATED"}
    with patch("app.dependencies.decode_token", return_value=payload):
        result = get_current_user(token)
        assert result == {"user_id": "user@example.com", "role": "AUTHENTICATED"}


@pytest.mark.asyncio
async def test_get_current_active_user_locked():
    """If DB returns locked user, dependency should raise."""
    db = AsyncMock(spec=AsyncSession)
    locked_user = MagicMock(spec=User)
    locked_user.is_active = False  
    with patch("app.services.user_service.UserService.get_by_email", return_value=locked_user):
        current_user = {"user_id": "user@example.com", "role": "AUTHENTICATED"}
        with pytest.raises(HTTPException):
            await get_current_active_user(db, current_user)


@pytest.mark.asyncio
async def test_get_current_active_user_not_found():
    """If user not found in DB, raise 404."""
    db = AsyncMock(spec=AsyncSession)
    with patch("app.services.user_service.UserService.get_by_email", return_value=None):
        current_user = {"user_id": "missing@example.com", "role": "AUTHENTICATED"}
        with pytest.raises(HTTPException) as excinfo:
            await get_current_active_user(db, current_user)
        assert excinfo.value.status_code == 404


def test_require_role_unauthorized():
    dependency = require_role(["ADMIN"])
    current_user = {"role": "AUTHENTICATED"}
    with pytest.raises(HTTPException) as excinfo:
        dependency(current_user)
    assert excinfo.value.status_code == 403
    assert "Operation not permitted" in excinfo.value.detail


def test_require_role_authorized():
    dependency = require_role(["ADMIN"])
    current_user = {"role": "ADMIN"}
    assert dependency(current_user) == current_user


def test_require_role_multiple_roles():
    dependency = require_role(["ADMIN", "MANAGER"])
    current_user = {"role": "MANAGER"}
    assert dependency(current_user) == current_user


def test_get_settings():
    """Test get_settings function."""
    # Call the function
    settings = get_settings()
    
    # Assert settings has expected attributes
    assert hasattr(settings, "database_url")
    assert hasattr(settings, "access_token_expire_minutes")
    assert hasattr(settings, "secret_key")
    assert hasattr(settings, "algorithm")
