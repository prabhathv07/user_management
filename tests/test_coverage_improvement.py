"""
Tests specifically designed to improve code coverage in the User Management System.
This module focuses on edge cases and error handling paths that might not be covered
by the existing test suite.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.user_model import User, UserRole
from app.services.user_service import UserService
from app.services.email_service import EmailService
from app.dependencies import get_settings
from app.routers.user_routes import update_user_professional_status, get_user, update_user


@pytest.mark.asyncio
async def test_user_service_update_professional_status_error_handling(db_session):
    """Test error handling in update_professional_status when user is not found."""
    # Create a non-existent user ID
    non_existent_id = uuid.uuid4()
    
    # Mock email service
    email_service = MagicMock()
    email_service.send_email = AsyncMock()
    
    # Call the method with a non-existent user ID
    result = await UserService.update_professional_status(
        db_session, non_existent_id, True, email_service
    )
    
    # Assert the result is None (user not found)
    assert result is None
    
    # Verify email service was not called
    email_service.send_email.assert_not_called()


@pytest.mark.asyncio
async def test_user_service_update_professional_status_email_exception(db_session, user):
    """Test handling of email exceptions in update_professional_status."""
    # Mock email service that raises an exception
    email_service = MagicMock()
    email_service.send_email = AsyncMock(side_effect=Exception("Email sending failed"))
    
    # Call the method with a valid user
    result = await UserService.update_professional_status(
        db_session, user.id, True, email_service
    )
    
    # Assert the user was still updated despite email failure
    assert result is not None
    assert result.is_professional is True
    
    # The implementation might handle the exception differently than we expect
    # The important part is that the user was updated successfully


@pytest.mark.asyncio
async def test_user_service_get_by_email_not_found(db_session):
    """Test get_by_email when email doesn't exist."""
    non_existent_email = "nonexistent@example.com"
    
    result = await UserService.get_by_email(db_session, non_existent_email)
    
    assert result is None


@pytest.mark.asyncio
async def test_user_service_verify_email_with_invalid_token(db_session, user):
    """Test verify_email_with_token with an invalid token."""
    # Set a verification token for the user
    user.verification_token = "valid_token"
    await db_session.commit()
    
    # Try to verify with an invalid token
    result = await UserService.verify_email_with_token(db_session, user.id, "invalid_token")
    
    # Assert verification failed
    assert result is False
    
    # Verify user's email is still not verified
    refreshed_user = await UserService.get_by_id(db_session, user.id)
    assert refreshed_user.email_verified is False


@pytest.mark.asyncio
async def test_user_service_update_section_invalid_section(db_session, user):
    """Test update_profile_section with an invalid section name."""
    invalid_section = "invalid_section"
    section_data = {"key": "value"}
    
    result = await UserService.update_profile_section(db_session, user.id, invalid_section, section_data)
    
    # Should return None for invalid section
    assert result is None


@pytest.mark.asyncio
async def test_user_service_register_user_duplicate_email(db_session, user, email_service):
    """Test register_user with a duplicate email."""
    # Try to register with an existing email
    user_data = {
        "nickname": "new_user",
        "email": user.email,  # Use existing email to trigger duplicate
        "password": "ValidPassword123!"
    }
    
    result = await UserService.register_user(db_session, user_data, email_service)
    
    # Should return None for duplicate email
    assert result is None


@pytest.mark.asyncio
async def test_user_service_list_users_with_skip_limit(db_session):
    """Test list_users with skip and limit parameters."""
    # Get total count first
    total_count = await UserService.count(db_session)
    
    # Skip first user, limit to 1 user
    users = await UserService.list_users(db_session, skip=1, limit=1)
    
    # Should return exactly 1 user if there are at least 2 users
    if total_count >= 2:
        assert len(users) == 1
    
    # Skip all users
    users = await UserService.list_users(db_session, skip=total_count, limit=10)
    
    # Should return empty list
    assert len(users) == 0


@pytest.mark.asyncio
async def test_user_service_get_profile_completion_user_not_found(db_session):
    """Test get_profile_completion when user is not found."""
    non_existent_id = uuid.uuid4()
    
    result = await UserService.get_profile_completion(db_session, non_existent_id)
    
    # Should return None when user is not found
    assert result is None


@pytest.mark.asyncio
async def test_user_service_is_account_locked_user_not_found(db_session):
    """Test is_account_locked when user is not found."""
    non_existent_email = "nonexistent@example.com"
    
    result = await UserService.is_account_locked(db_session, non_existent_email)
    
    # Should return False when user is not found
    assert result is False


@pytest.mark.asyncio
async def test_user_service_unlock_account_user_not_found(db_session):
    """Test unlock_user_account when user is not found."""
    non_existent_id = uuid.uuid4()
    
    result = await UserService.unlock_user_account(db_session, non_existent_id)
    
    # Should return False when user is not found
    assert result is False
