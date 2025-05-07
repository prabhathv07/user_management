"""
Tests specifically designed to improve code coverage for user services.
This module focuses on edge cases and error handling paths in the services.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException

from app.models.user_model import User, UserRole
from app.services.user_service import UserService
from app.services.email_service import EmailService


@pytest.mark.asyncio
async def test_user_service_create_with_validation_error():
    """Test create method with validation error."""
    # Create user data with invalid email
    user_data = {
        "nickname": "exception_user",
        "email": "not-an-email",  # Invalid email format
        "password": "ValidPassword123!",
        "role": UserRole.AUTHENTICATED.name
    }
    
    # Mock db and email service
    db_session = AsyncMock(spec=AsyncSession)
    email_service = MagicMock()
    
    # Call the method with invalid data to trigger ValidationError
    result = await UserService.create(db_session, user_data, email_service)
    
    # Assert result is None due to validation exception
    assert result is None


@pytest.mark.asyncio
async def test_user_service_update_with_exception(db_session, user):
    """Test update method with database exception."""
    # Create update data
    update_data = {
        "nickname": "updated_exception_user",
    }
    
    # Mock db_session.commit to raise an exception
    with patch.object(db_session, 'commit', side_effect=SQLAlchemyError("Database error")):
        # Call the method
        result = await UserService.update(db_session, user.id, update_data)
        
        # Assert result is None due to exception
        assert result is None


@pytest.mark.asyncio
async def test_user_service_delete_not_found():
    """Test delete method when user not found."""
    # Setup
    db_session = AsyncMock(spec=AsyncSession)
    user_id = uuid.uuid4()
    
    # Mock user not found
    with patch.object(UserService, 'get_by_id', return_value=None):
        # Call the method
        result = await UserService.delete(db_session, user_id)
        
        # Assert result is False when user not found
        assert result is False


@pytest.mark.asyncio
async def test_user_service_register_user_with_exception(db_session):
    """Test register_user method with database exception."""
    # Create user data
    user_data = {
        "nickname": "register_exception",
        "email": "register_exception@example.com",
        "password": "ValidPassword123!"
    }
    
    # Mock email service
    email_service = MagicMock()
    
    # Mock db_session.commit to raise an exception
    with patch.object(db_session, 'commit', side_effect=SQLAlchemyError("Database error")):
        # Call the method
        result = await UserService.register_user(db_session, user_data, email_service)
        
        # Assert result is None due to exception
        assert result is None


@pytest.mark.asyncio
async def test_user_service_verify_email_with_invalid_token(db_session, user):
    """Test verify_email_with_token method with invalid token."""
    # Set a verification token for the user
    user.verification_token = "valid_token"
    await db_session.commit()
    
    # Call the method with incorrect token
    result = await UserService.verify_email_with_token(db_session, user.id, "invalid_token")
    
    # Assert result is False with wrong token
    assert result is False


@pytest.mark.asyncio
async def test_user_service_login_user_with_exception(db_session, user):
    """Test login_user method with database exception."""
    # Mock db_session.commit to raise an exception
    with patch.object(db_session, 'commit', side_effect=SQLAlchemyError("Database error")):
        # Call the method
        result = await UserService.login_user(db_session, user.email, "password")
        
        # Assert result is None due to exception
        assert result is None


@pytest.mark.asyncio
async def test_user_service_reset_password_user_not_found():
    """Test reset_password method when user not found."""
    # Setup
    db_session = AsyncMock(spec=AsyncSession)
    user_id = uuid.uuid4()
    
    # Mock user not found
    with patch.object(UserService, 'get_by_id', return_value=None):
        # Call the method
        result = await UserService.reset_password(db_session, user_id, "NewPassword123!")
        
        # Assert result is False when user not found
        assert result is False


@pytest.mark.asyncio
async def test_user_service_update_profile_section_basic_info(db_session, user):
    """Test update_profile_section method with basic_info section."""
    # Create section data
    section_data = {
        "first_name": "Updated",
        "last_name": "User",
        "bio": "Updated bio"
    }
    
    # Call the method
    result = await UserService.update_profile_section(db_session, user.id, "basic_info", section_data)
    
    # Assert
    assert result is not None
    assert result.first_name == "Updated"
    assert result.last_name == "User"
    assert result.bio == "Updated bio"


@pytest.mark.asyncio
async def test_user_service_update_profile_section_professional_info(db_session, user):
    """Test update_profile_section method with professional_info section."""
    # Create section data
    section_data = {
        "skills": ["Python", "FastAPI"],
        "work_experience": [{"company": "Example Inc", "position": "Developer"}]
    }
    
    # Call the method
    result = await UserService.update_profile_section(db_session, user.id, "professional_info", section_data)
    
    # Assert
    assert result is not None
    assert result.skills == ["Python", "FastAPI"]
    assert result.work_experience == [{"company": "Example Inc", "position": "Developer"}]


@pytest.mark.asyncio
async def test_user_service_update_profile_section_preferences(db_session, user):
    """Test update_profile_section method with preferences section."""
    # Create section data
    section_data = {
        "preferred_language": "English",
        "timezone": "UTC"
    }
    
    # Call the method
    result = await UserService.update_profile_section(db_session, user.id, "preferences", section_data)
    
    # Assert
    assert result is not None
    assert result.preferred_language == "English"
    assert result.timezone == "UTC"


@pytest.mark.asyncio
async def test_user_service_get_profile_completion(db_session, user):
    """Test get_profile_completion method."""
    # Update user with some profile data
    user.first_name = "Test"
    user.last_name = "User"
    user.bio = "Test bio"
    user.skills = ["Python"]
    await db_session.commit()
    
    # Call the method
    completion_details = await UserService.get_profile_completion(db_session, user.id)
    
    # Assert
    assert completion_details is not None
    assert "overall_completion" in completion_details
    assert completion_details["overall_completion"] > 0
    assert completion_details["overall_completion"] <= 100


@pytest.mark.asyncio
async def test_user_service_get_profile_completion_fields(db_session, user):
    """Test fields returned by get_profile_completion method."""
    # Update user with some profile data
    user.first_name = "Test"
    user.last_name = "User"
    await db_session.commit()
    
    # Call the method
    details = await UserService.get_profile_completion(db_session, user.id)
    
    # Assert
    assert details is not None
    assert "overall_completion" in details
    assert "section_completion" in details
    assert "field_status" in details
