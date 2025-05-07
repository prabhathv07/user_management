"""
Tests specifically designed to improve code coverage for user routes.
This module focuses on edge cases and error handling paths in the routes.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from app.models.user_model import User, UserRole
from app.schemas.user_schemas import UserCreate, UserUpdate, ProfileSectionUpdate
from app.routers.user_routes import (
    update_user_professional_status, get_user, update_user,
    update_profile_section, get_profile_completion,
    update_own_profile, verify_email, refresh_token
)
from app.services.user_service import UserService
from app.services.email_service import EmailService
from app.services.jwt_service import create_access_token, decode_token
from app.dependencies import get_settings


@pytest.mark.asyncio
async def test_get_user_not_found():
    """Test get_user when user is not found."""
    # Mock dependencies
    db = AsyncMock(spec=AsyncSession)
    request = MagicMock(spec=Request)
    token = "valid_token"
    current_user = {"user_id": "test-user", "role": "ADMIN"}
    
    # Mock UserService.get_by_id to return None
    with patch("app.routers.user_routes.UserService.get_by_id", return_value=None):
        # Call the endpoint and expect exception
        with pytest.raises(HTTPException) as excinfo:
            await get_user(uuid.uuid4(), request, db, token, current_user)
        
        # Assert
        assert excinfo.value.status_code == 404
        assert "User not found" in excinfo.value.detail


@pytest.mark.asyncio
async def test_update_user_not_found():
    """Test update_user when user is not found."""
    # Mock dependencies
    db = AsyncMock(spec=AsyncSession)
    request = MagicMock(spec=Request)
    token = "valid_token"
    current_user = {"user_id": "test-user", "role": "ADMIN"}
    user_update = UserUpdate(nickname="new_nickname")
    
    # Mock UserService.update to return None
    with patch("app.routers.user_routes.UserService.update", return_value=None):
        # Call the endpoint and expect exception
        with pytest.raises(HTTPException) as excinfo:
            await update_user(uuid.uuid4(), user_update, request, db, token, current_user)
        
        # Assert
        assert excinfo.value.status_code == 404
        assert "User not found" in excinfo.value.detail


@pytest.mark.asyncio
async def test_update_user_professional_status_not_found():
    """Test update_user_professional_status when user is not found."""
    # Mock dependencies
    db = AsyncMock(spec=AsyncSession)
    email_service = MagicMock()
    token = "valid_token"
    current_user = {"user_id": "test-user", "role": "ADMIN"}
    
    # Mock UserService.update_professional_status to return None
    with patch("app.routers.user_routes.UserService.update_professional_status", return_value=None):
        # Call the endpoint and expect exception
        with pytest.raises(HTTPException) as excinfo:
            await update_user_professional_status(
                uuid.uuid4(), True, db, email_service, token, current_user
            )
        
        # Assert
        assert excinfo.value.status_code == 404
        assert "User not found" in excinfo.value.detail


@pytest.mark.asyncio
async def test_update_profile_section_invalid_section():
    """Test update_profile_section with an invalid section name."""
    # Mock dependencies
    db = AsyncMock(spec=AsyncSession)
    current_user = MagicMock(spec=User)
    section_data = ProfileSectionUpdate()
    
    # Call the endpoint with an invalid section and expect exception
    with pytest.raises(HTTPException) as excinfo:
        await update_profile_section("invalid_section", section_data, current_user, db)
    
    # Assert
    assert excinfo.value.status_code == 400
    assert "Invalid section" in excinfo.value.detail


@pytest.mark.asyncio
async def test_update_profile_section_not_found():
    """Test update_profile_section when user is not found or update fails."""
    # Mock dependencies
    db = AsyncMock(spec=AsyncSession)
    current_user = MagicMock(spec=User)
    current_user.id = uuid.uuid4()
    section_data = ProfileSectionUpdate()
    
    # Mock UserService.update_profile_section to return None
    with patch("app.routers.user_routes.UserService.update_profile_section", return_value=None):
        # Call the endpoint and expect exception
        with pytest.raises(HTTPException) as excinfo:
            await update_profile_section("basic_info", section_data, current_user, db)
        
        # Assert
        assert excinfo.value.status_code == 404
        assert "User not found or update failed" in excinfo.value.detail


@pytest.mark.asyncio
async def test_get_profile_completion_not_found():
    """Test get_profile_completion when user is not found."""
    # Mock dependencies
    db = AsyncMock(spec=AsyncSession)
    current_user = MagicMock(spec=User)
    current_user.id = uuid.uuid4()
    
    # Mock UserService.get_profile_completion to return None
    with patch("app.routers.user_routes.UserService.get_profile_completion", return_value=None):
        # Call the endpoint and expect exception
        with pytest.raises(HTTPException) as excinfo:
            await get_profile_completion(current_user, db)
        
        # Assert
        assert excinfo.value.status_code == 404
        assert "User not found" in excinfo.value.detail


@pytest.mark.asyncio
async def test_update_own_profile_not_found():
    """Test update_own_profile when user is not found."""
    # Mock dependencies
    db = AsyncMock(spec=AsyncSession)
    current_user = MagicMock(spec=User)
    current_user.id = uuid.uuid4()
    update_data = UserUpdate(nickname="new_nickname")
    
    # Mock UserService.update to return None
    with patch("app.routers.user_routes.UserService.update", return_value=None):
        # Call the endpoint and expect exception
        with pytest.raises(HTTPException) as excinfo:
            await update_own_profile(update_data, current_user, db)
        
        # Assert
        assert excinfo.value.status_code == 404
        assert "User not found" in excinfo.value.detail


@pytest.mark.asyncio
async def test_verify_email_invalid_token():
    """Test verify_email with an invalid token."""
    # Mock dependencies
    db = AsyncMock(spec=AsyncSession)
    email_service = MagicMock(spec=EmailService)
    
    # Mock UserService.verify_email_with_token to return False
    with patch("app.routers.user_routes.UserService.verify_email_with_token", return_value=False):
        # Call the endpoint and expect exception
        with pytest.raises(HTTPException) as excinfo:
            await verify_email(uuid.uuid4(), "invalid_token", db, email_service)
        
        # Assert
        assert excinfo.value.status_code == 400
        assert "Invalid or expired verification token" in excinfo.value.detail


@pytest.mark.asyncio
async def test_refresh_token_invalid_token():
    """Test refresh_token with an invalid token."""
    # Mock dependencies
    db = AsyncMock(spec=AsyncSession)
    
    # Mock decode_token to raise an exception
    with patch("app.routers.user_routes.decode_token", side_effect=Exception("Invalid token")):
        # Call the endpoint and expect exception
        with pytest.raises(HTTPException) as excinfo:
            await refresh_token("invalid_token", db)
        
        # Assert
        assert excinfo.value.status_code == 401
        assert "Invalid token" in excinfo.value.detail


@pytest.mark.asyncio
async def test_refresh_token_missing_sub():
    """Test refresh_token with a token missing the 'sub' claim."""
    # Mock dependencies
    db = AsyncMock(spec=AsyncSession)
    
    # Mock decode_token to return a payload without 'sub'
    with patch("app.routers.user_routes.decode_token", return_value={}):
        # Call the endpoint and expect exception
        with pytest.raises(HTTPException) as excinfo:
            await refresh_token("token_without_sub", db)
        
        # Assert
        assert excinfo.value.status_code == 401
        assert "Invalid token" in excinfo.value.detail


@pytest.mark.asyncio
async def test_refresh_token_user_not_found():
    """Test refresh_token when user is not found."""
    # Mock dependencies
    db = AsyncMock(spec=AsyncSession)
    
    # Mock decode_token to return a valid payload
    with patch("app.routers.user_routes.decode_token", return_value={"sub": "test@example.com"}):
        # Mock UserService.get_by_email to return None
        with patch("app.routers.user_routes.UserService.get_by_email", return_value=None):
            # Call the endpoint and expect exception
            with pytest.raises(HTTPException) as excinfo:
                await refresh_token("valid_token", db)
            
            # Assert
            assert excinfo.value.status_code == 401
            assert "Invalid token" in excinfo.value.detail
