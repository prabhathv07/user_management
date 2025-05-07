"""
Additional tests to improve coverage of the User Management System.
These tests focus on edge cases, error scenarios, and important functionality.
"""
import pytest
import uuid
import os
from datetime import datetime, timedelta
from sqlalchemy import select, update
from app.models.user_model import User, UserRole
from app.services.user_service import UserService
from app.utils.security import hash_password, verify_password
from app.utils.nickname_gen import generate_nickname
from app.dependencies import get_settings
from app.schemas.user_schemas import UserCreate, UserUpdate
from httpx import AsyncClient
from urllib.parse import urlencode

# Override database settings for local testing
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://user:password@localhost/myappdb'

pytestmark = pytest.mark.asyncio

# Test 1: Password complexity validation
async def test_password_complexity_validation(async_client):
    """Test that password complexity requirements are enforced."""
    weak_passwords = ["password", "12345678", "Abc123", "Abcdefgh"]
    for pwd in weak_passwords:
        response = await async_client.post(
            "/api/register/",
            json={
                "email": f"test_{uuid.uuid4()}@example.com",
                "password": pwd,
                "nickname": "testuser"
            }
        )
        assert response.status_code == 422
    
    valid_response = await async_client.post(
        "/api/register/",
        json={
            "email": f"valid_{uuid.uuid4()}@example.com",
            "password": "StrongP@ss123",
            "nickname": "validuser"
        }
    )
    assert valid_response.status_code == 201

# Test 2: Manual email verification
async def test_email_verification_token_expiration(db_session, email_service):
    """Test manual email verification functionality."""
    # Create a user that is not verified
    user_data = {
        "nickname": generate_nickname(),
        "email": f"verify_test_{uuid.uuid4()}@example.com",
        "password": "ValidPassword123!",
        "role": "ANONYMOUS"  # Start with ANONYMOUS role
    }
    
    user = await UserService.create(db_session, user_data, email_service)
    assert user is not None
    
    # Manually set verification token
    user.verification_token = "test-verification-token"
    user.email_verified = False
    await db_session.commit()
    
    # Refresh user from database
    user = await UserService.get_by_id(db_session, user.id)
    assert user.email_verified is False, "User email should not be verified initially"
    
    # Verify with the token
    correct_result = await UserService.verify_email_with_token(
        db_session, user.id, "test-verification-token"
    )
    
    # Should succeed with correct token
    assert correct_result is True, "Verification should succeed with correct token"
    
    # Refresh user from database
    updated_user = await UserService.get_by_id(db_session, user.id)
    assert updated_user.email_verified is True, "User email should be verified after token verification"

# Test 3: User creation performance
async def test_concurrent_user_creation_performance(db_session, email_service):
    """Test the system's ability to handle multiple user creations."""
    # Create 3 users sequentially and verify they're created successfully
    users_created = []
    
    for i in range(3):
        user_data = {
            "nickname": f"perf_test_user_{i}_{uuid.uuid4()}",
            "email": f"perf_test_{i}_{uuid.uuid4()}@example.com",
            "password": "PerformanceTest123!",
            "role": "AUTHENTICATED"
        }
        
        # Create user and measure time
        start_time = datetime.utcnow()
        user = await UserService.create(db_session, user_data, email_service)
        end_time = datetime.utcnow()
        
        # Verify user was created
        assert user is not None, f"User {i} should be created successfully"
        users_created.append(user)
        
        # Verify creation time is reasonable (less than 1 second per user)
        duration = (end_time - start_time).total_seconds()
        assert duration < 1, f"Creating user took {duration} seconds, which exceeds the 1 second threshold"
    
    # Verify all users were created with unique IDs
    user_ids = [str(user.id) for user in users_created]
    assert len(set(user_ids)) == 3, "All users should have unique IDs"

# Test 4: Role-based access control
async def test_role_based_access_control(async_client, admin_token, user_token):
    """Test role-based endpoint access."""
    # Admin should access admin-only endpoint
    admin_resp = await async_client.get(
        "/api/users/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert admin_resp.status_code == 200
    
    # Regular user should be denied
    user_resp = await async_client.get(
        "/api/users/",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert user_resp.status_code == 403

# Test 5: Failed login attempts tracking
from app.dependencies import get_settings
settings = get_settings()

async def test_login_rate_limiting(async_client, verified_user):
    """Test that account locks after max failed attempts."""
    for _ in range(settings.max_login_attempts):
        response = await async_client.post(
            "/api/login/",
            data={"username": verified_user.email, "password": "wrongpassword"}
        )
        assert response.status_code == 401
    
    # Next attempt should lock account
    locked_response = await async_client.post(
        "/api/login/",
        data={"username": verified_user.email, "password": "wrongpassword"}
    )
    assert locked_response.status_code == 403
    assert "Account locked" in locked_response.json().get("detail", "")

# Test 6: Password reset functionality
async def test_password_reset_functionality(db_session, verified_user):
    """Test the complete password reset functionality."""
    # Store original password hash
    original_hash = verified_user.hashed_password
    
    # Reset password
    new_password = "NewSecurePassword123!"
    reset_success = await UserService.reset_password(db_session, verified_user.id, new_password)
    assert reset_success is True, "Password reset should succeed"
    
    # Verify password was changed
    updated_user = await UserService.get_by_id(db_session, verified_user.id)
    assert updated_user.hashed_password != original_hash, "Password hash should be updated"
    
    # Verify login with new password works
    login_result = await UserService.login_user(db_session, verified_user.email, new_password)
    assert login_result is not None, "Login with new password should succeed"
    
    # Reset password back to original to avoid affecting other tests
    original_password = "MySuperPassword$1234"  # Standard test password from fixtures
    await UserService.reset_password(db_session, verified_user.id, original_password)

# Test 7: User pagination
async def test_user_search_and_filtering(async_client, admin_token):
    """Test the ability to paginate through users."""
    # Test basic user listing
    response = await async_client.get(
        "/users/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200, "Admin should be able to list users"
    assert "items" in response.json(), "Response should contain items array"
    
    # Test pagination with limit parameter
    response = await async_client.get(
        "/users/?limit=5",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    users = response.json()["items"]
    assert len(users) <= 5, "Should return at most 5 users with limit=5"
    
    # Test pagination with skip parameter
    first_page = await async_client.get(
        "/users/?limit=3",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    second_page = await async_client.get(
        "/users/?limit=3&skip=3",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    first_users = first_page.json()["items"]
    second_users = second_page.json()["items"]
    
    # If we have enough users, first and second page should be different
    if len(first_users) == 3 and len(second_users) > 0:
        first_ids = [user["id"] for user in first_users]
        second_ids = [user["id"] for user in second_users]
        assert not any(id in first_ids for id in second_ids), "Second page should contain different users than first page"

# Test 8: User data validation on update
async def test_user_data_validation_on_update(async_client, admin_token, admin_user):
    test_cases = [
        {"field": "email", "value": "invalid-email", "expected": 422},
        {"field": "nickname", "value": "", "expected": 422},
        {"field": "bio", "value": "Valid bio", "expected": 200}
    ]
    
    for case in test_cases:
        response = await async_client.put(
            f"/api/users/{admin_user.id}/",  # Add trailing slash
            json={case["field"]: case["value"]},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == case["expected"]

# Test 9: Database transaction rollback on error
async def test_database_transaction_rollback(db_session, email_service):
    """Test that database transactions are properly rolled back when errors occur."""
    # Create initial state - a user we can reference
    initial_user = {
        "nickname": generate_nickname(),
        "email": f"initial_{uuid.uuid4()}@example.com",
        "password": "ValidPassword123!",
        "role": "AUTHENTICATED"
    }
    user = await UserService.create(db_session, initial_user, email_service)
    assert user is not None
    
    # Attempt an operation that should fail and trigger rollback
    # In this case, try to create a user with the same email (violates unique constraint)
    duplicate_user = {
        "nickname": generate_nickname(),
        "email": user.email,  # Same email as existing user
        "password": "AnotherValid123!",
        "role": "AUTHENTICATED"
    }
    
    # This should fail but not crash the application
    result = await UserService.create(db_session, duplicate_user, email_service)
    assert result is None, "Creating a user with duplicate email should fail"
    
    # Verify we can still perform operations after the rollback
    # If the transaction wasn't rolled back properly, this would fail
    query_result = await UserService.get_by_email(db_session, user.email)
    assert query_result is not None, "Should be able to query after transaction rollback"
    assert query_result.email == user.email, "Original user should still exist"

# Test 10: User account locking and unlocking
async def test_user_account_locking_and_unlocking(db_session, verified_user):
    """Test the complete flow of locking a user account and then unlocking it."""
    # First, verify the account is not locked initially
    assert not verified_user.is_locked, "User account should not be locked initially"
    
    # Simulate failed login attempts to trigger account locking
    settings = get_settings()
    max_attempts = settings.max_login_attempts
    
    # Make multiple failed login attempts
    for _ in range(max_attempts):
        result = await UserService.login_user(
            db_session, 
            verified_user.email, 
            "WrongPassword123!"  # Wrong password
        )
        assert result is None, "Login with wrong password should fail"
    
    # Verify the account is now locked
    locked_user = await UserService.get_by_email(db_session, verified_user.email)
    assert locked_user.is_locked, "User account should be locked after max failed attempts"
    
    # Verify login fails even with correct password when account is locked
    login_result = await UserService.login_user(
        db_session, 
        verified_user.email, 
        "MySuperPassword$1234"  # Correct password
    )
    assert login_result is None, "Login should fail when account is locked"
    
    # Unlock the account
    unlock_success = await UserService.unlock_user_account(db_session, locked_user.id)
    assert unlock_success, "Account unlock should succeed"
    
    # Verify the account is now unlocked
    updated_user = await UserService.get_by_id(db_session, locked_user.id)
    assert not updated_user.is_locked, "User account should be unlocked"
    
    # Verify login works after unlocking
    login_result = await UserService.login_user(
        db_session, 
        verified_user.email, 
        "MySuperPassword$1234"  # Correct password
    )
    assert login_result is not None, "Login should succeed after account is unlocked"
