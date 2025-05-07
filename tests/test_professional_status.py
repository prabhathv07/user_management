"""
Tests for the professional status upgrade feature.
"""
import pytest
from datetime import datetime, timezone
from uuid import UUID
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user_model import User, UserRole
from app.services.user_service import UserService
from app.services.email_service import EmailService
from app.utils.template_manager import TemplateManager
import uuid

pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_update_professional_status_service(db_session, user, mocker):
    """Test updating a user's professional status via the service."""
    # Mock the email service to avoid sending actual emails
    mock_email_service = mocker.MagicMock(spec=EmailService)
    mock_email_service.send_professional_status_notification = mocker.AsyncMock()
    
    # Verify user is not professional initially
    assert not user.is_professional
    assert user.professional_status_updated_at is None
    
    # Update to professional status
    updated_user = await UserService.update_professional_status(
        db_session, user.id, True, mock_email_service
    )
    
    # Verify user was updated
    assert updated_user is not None
    assert updated_user.is_professional
    assert updated_user.professional_status_updated_at is not None
    
    # Verify notification was sent
    mock_email_service.send_professional_status_notification.assert_called_once_with(updated_user)
    
    # Update back to non-professional
    updated_user = await UserService.update_professional_status(
        db_session, user.id, False, mock_email_service
    )
    
    # Verify user was updated
    assert updated_user is not None
    assert not updated_user.is_professional
    
    # Verify no additional notification was sent (only sent when upgrading to professional)
    assert mock_email_service.send_professional_status_notification.call_count == 1


@pytest.mark.asyncio
async def test_update_professional_status_endpoint_as_admin(async_client, db_session, admin_token, user):
    """Test updating a user's professional status via the API endpoint as admin."""
    response = await async_client.put(
        f"/api/users/{user.id}/professional-status",
        json={"is_professional": True},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["is_professional"] is True
    
    # Verify database was updated
    updated_user = await UserService.get_by_id(db_session, user.id)
    assert updated_user.is_professional
    assert updated_user.professional_status_updated_at is not None


@pytest.mark.asyncio
async def test_update_professional_status_endpoint_as_manager(async_client, db_session, manager_token, user):
    """Test updating a user's professional status via the API endpoint as manager."""
    response = await async_client.put(
        f"/api/users/{user.id}/professional-status",
        json={"is_professional": True},
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["is_professional"] is True
    
    # Verify database was updated
    updated_user = await UserService.get_by_id(db_session, user.id)
    assert updated_user.is_professional
    assert updated_user.professional_status_updated_at is not None


@pytest.mark.asyncio
async def test_update_professional_status_endpoint_as_regular_user(async_client, user_token, user):
    """Test that regular users cannot update professional status."""
    response = await async_client.put(
        f"/api/users/{user.id}/professional-status",
        json={"is_professional": True},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    # Regular users should not have permission
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_professional_status_nonexistent_user(async_client, admin_token):
    """Test updating professional status for a non-existent user."""
    non_existent_id = "00000000-0000-0000-0000-000000000000"
    response = await async_client.put(
        f"/api/users/{non_existent_id}/professional-status",
        json={"is_professional": True},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_professional_status_notification_email(db_session, user, mocker):
    """Test that the email notification is correctly formatted and sent."""
    # Create a real template manager but mock the SMTP client
    template_manager = TemplateManager()
    mock_smtp_client = mocker.MagicMock()
    
    # Create email service with mocked SMTP client
    email_service = EmailService(template_manager)
    email_service.smtp_client = mock_smtp_client
    
    # Set professional status updated timestamp
    user.professional_status_updated_at = datetime.now(timezone.utc)
    
    # Send notification
    await email_service.send_professional_status_notification(user)
    
    # Verify email was sent with correct parameters
    mock_smtp_client.send_email.assert_called_once()
    args = mock_smtp_client.send_email.call_args[0]
    
    # Check subject contains "Professional Status Upgrade"
    assert "Professional Status Upgrade" in args[0]
    
    # Check content contains congratulations message
    assert "Congratulations" in args[1]
    
    # Check email was sent to the correct user
    assert user.email == args[2]
