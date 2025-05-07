"""
Test file to increase coverage for user routes module.

This file contains tests for endpoints in user_routes.py that have low coverage.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import Request, HTTPException
from uuid import uuid4, UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.routers.user_routes import verify_email, register, login, list_users, create_user, delete_user, update_user, get_user
from app.schemas.user_schemas import UserCreate, UserUpdate
from app.models.user_model import User, UserRole
from app.services.user_service import UserService
from app.services.email_service import EmailService


class TestUserRoutes:
    """Tests for the user routes module."""

    @pytest.mark.asyncio
    async def test_verify_email_success(self, monkeypatch):
        """Test successful email verification."""
        # Mock dependencies
        mock_db = MagicMock(spec=AsyncSession)
        mock_email_service = MagicMock(spec=EmailService)
        
        # Mock UserService.verify_email_with_token to return True
        async def mock_verify(*args, **kwargs):
            return True
        
        monkeypatch.setattr(UserService, "verify_email_with_token", mock_verify)
        
        # Call the endpoint
        user_id = uuid4()
        token = "valid-token"
        response = await verify_email(user_id, token, mock_db, mock_email_service)
        
        # Assert
        assert response == {"message": "Email verified successfully"}

    @pytest.mark.asyncio
    async def test_verify_email_failure(self, monkeypatch):
        """Test failed email verification."""
        # Mock dependencies
        mock_db = MagicMock(spec=AsyncSession)
        mock_email_service = MagicMock(spec=EmailService)
        
        # Mock UserService.verify_email_with_token to return False
        async def mock_verify(*args, **kwargs):
            return False
        
        monkeypatch.setattr(UserService, "verify_email_with_token", mock_verify)
        
        # Call the endpoint and expect exception
        user_id = uuid4()
        token = "invalid-token"
        
        with pytest.raises(HTTPException) as excinfo:
            await verify_email(user_id, token, mock_db, mock_email_service)
        
        # Assert
        assert excinfo.value.status_code == 400
        assert "Invalid or expired verification token" in excinfo.value.detail

    @pytest.mark.asyncio
    async def test_register_success(self, monkeypatch):
        """Test successful user registration."""
        # Mock dependencies
        mock_db = MagicMock(spec=AsyncSession)
        mock_email_service = MagicMock(spec=EmailService)
        
        # Mock UserCreate instead of creating an actual instance
        user_data = MagicMock(spec=UserCreate)
        user_data.email = "test@example.com"
        user_data.password = "Password123!"
        user_data.model_dump.return_value = {
            "email": "test@example.com",
            "password": "Password123!",
            "role": "AUTHENTICATED"
        }
        
        # Mock user object to return
        mock_user = User(
            id=uuid4(),
            nickname="testuser",
            first_name="Test",
            last_name="User",
            email="test@example.com",
            hashed_password="hashed_password",
            role=UserRole.AUTHENTICATED,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Mock UserService.register_user to return the mock user
        async def mock_register(*args, **kwargs):
            return mock_user
        
        monkeypatch.setattr(UserService, "register_user", mock_register)
        
        # Call the endpoint
        response = await register(user_data, mock_db, mock_email_service)
        
        # Assert
        assert response == mock_user

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, monkeypatch):
        """Test registration with duplicate email."""
        # Mock dependencies
        mock_db = MagicMock(spec=AsyncSession)
        mock_email_service = MagicMock(spec=EmailService)
        
        # Mock UserCreate instead of creating an actual instance
        user_data = MagicMock(spec=UserCreate)
        user_data.email = "existing@example.com"
        user_data.password = "Password123!"
        user_data.model_dump.return_value = {
            "email": "existing@example.com",
            "password": "Password123!",
            "role": "AUTHENTICATED"
        }
        
        # Mock UserService.register_user to return None (email exists)
        async def mock_register(*args, **kwargs):
            return None
        
        monkeypatch.setattr(UserService, "register_user", mock_register)
        
        # Call the endpoint and expect exception
        with pytest.raises(HTTPException) as excinfo:
            await register(user_data, mock_db, mock_email_service)
        
        # Assert
        assert excinfo.value.status_code == 400
        assert "Email already exists" in excinfo.value.detail

    @pytest.mark.asyncio
    async def test_login_success(self, monkeypatch):
        """Test successful login."""
        # Mock dependencies
        mock_db = MagicMock(spec=AsyncSession)
        
        # Mock form data
        form_data = MagicMock()
        form_data.username = "test@example.com"
        form_data.password = "Password123!"
        
        # Mock user object to return
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.role.name = "AUTHENTICATED"
        
        # Mock UserService methods
        async def mock_is_locked(*args, **kwargs):
            return False
        
        async def mock_login(*args, **kwargs):
            return mock_user
        
        monkeypatch.setattr(UserService, "is_account_locked", mock_is_locked)
        monkeypatch.setattr(UserService, "login_user", mock_login)
        
        # Mock create_access_token
        with patch("app.routers.user_routes.create_access_token") as mock_create_token:
            mock_create_token.return_value = "test_token"
            
            # Call the endpoint
            response = await login(form_data, mock_db)
            
            # Assert
            assert response == {"access_token": "test_token", "token_type": "bearer"}
            mock_create_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_account_locked(self, monkeypatch):
        """Test login with locked account."""
        # Mock dependencies
        mock_db = MagicMock(spec=AsyncSession)
        
        # Mock form data
        form_data = MagicMock()
        form_data.username = "locked@example.com"
        form_data.password = "Password123!"
        
        # Mock UserService.is_account_locked to return True
        async def mock_is_locked(*args, **kwargs):
            return True
        
        monkeypatch.setattr(UserService, "is_account_locked", mock_is_locked)
        
        # Call the endpoint and expect exception
        with pytest.raises(HTTPException) as excinfo:
            await login(form_data, mock_db)
        
        # Assert
        assert excinfo.value.status_code == 400
        assert "Account locked" in excinfo.value.detail

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, monkeypatch):
        """Test login with invalid credentials."""
        # Mock dependencies
        mock_db = MagicMock(spec=AsyncSession)
        
        # Mock form data
        form_data = MagicMock()
        form_data.username = "test@example.com"
        form_data.password = "WrongPassword"
        
        # Mock UserService methods
        async def mock_is_locked(*args, **kwargs):
            return False
        
        async def mock_login(*args, **kwargs):
            return None
        
        monkeypatch.setattr(UserService, "is_account_locked", mock_is_locked)
        monkeypatch.setattr(UserService, "login_user", mock_login)
        
        # Call the endpoint and expect exception
        with pytest.raises(HTTPException) as excinfo:
            await login(form_data, mock_db)
        
        # Assert
        assert excinfo.value.status_code == 401
        assert "Incorrect email or password" in excinfo.value.detail

    @pytest.mark.asyncio
    async def test_list_users(self, monkeypatch):
        """Test listing users."""
        # Mock dependencies
        mock_db = MagicMock(spec=AsyncSession)
        mock_request = MagicMock(spec=Request)
        mock_current_user = {"user_id": "test-user", "role": "ADMIN"}
        
        # Mock user objects to return
        mock_users = [
            User(
                id=uuid4(),
                nickname=f"user{i}",
                first_name=f"First{i}",
                last_name=f"Last{i}",
                email=f"user{i}@example.com",
                hashed_password="hashed_password",
                role=UserRole.AUTHENTICATED,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            for i in range(3)
        ]
        
        # Mock UserService methods
        async def mock_count(*args, **kwargs):
            return 3
        
        async def mock_list_users(*args, **kwargs):
            return mock_users
        
        monkeypatch.setattr(UserService, "count", mock_count)
        monkeypatch.setattr(UserService, "list_users", mock_list_users)
        
        # Mock generate_pagination_links
        with patch("app.routers.user_routes.generate_pagination_links") as mock_gen_links:
            mock_gen_links.return_value = {"self": "/users?skip=0&limit=10"}
            
            # Call the endpoint
            response = await list_users(mock_request, 0, 10, mock_db, mock_current_user)
            
            # Assert
            assert response.total == 3
            assert len(response.items) == 3
            assert response.page == 1
            assert response.size == 3
            # Check if links exist in the response dictionary instead of as an attribute
            # This is because UserListResponse doesn't have a links field in its model
            mock_gen_links.assert_called_once_with(mock_request, 0, 10, 3)
