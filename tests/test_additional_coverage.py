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
    """Test that password complexity requirements are enforced during registration."""
    # Test with various invalid passwords
    test_cases = [
        # Test short password
        {"password": "short"},
        # Test password without uppercase
        {"password": "nouppercase123!"},
        # Test password without lowercase
        {"password": "NOLOWERCASE123!"},
        # Test password without numbers
        {"password": "NoSpecialChars"},
        # Test password without special characters
        {"password": "NoSpecialChars123"}
    ]
    
    for case in test_cases:
        user_data = {
            "nickname": generate_nickname(),
            "email": f"test_{uuid.uuid4()}@example.com",
            "password": case["password"],
            "role": "AUTHENTICATED"  # Add required role field
        }
        
        response = await async_client.post("/register/", json=user_data)
        # Verify that invalid passwords are rejected with 422 status code
        assert response.status_code == 422, f"Expected validation error for password: {case['password']}"
        # Verify response contains error details
        assert "detail" in response.json(), "Error details missing in response"

# Test 2: Email verification expiration
async def test_email_verification_token_expiration(db_session, email_service):
    """Test that email verification tokens expire after the configured time."""
    # Create a user with a verification token
    user_data = {
        "nickname": generate_nickname(),
        "email": f"expiry_test_{uuid.uuid4()}@example.com",
        "password": "ValidPassword123!",
    }
    
    user = await UserService.create(db_session, user_data, email_service)
    assert user is not None
    
    # Set the verification token creation time to be older than the expiration time
    settings = get_settings()
    expiration_hours = settings.verification_token_expire_hours
    
    # Update the token creation time to be older than expiration
    token_created_at = datetime.utcnow() - timedelta(hours=expiration_hours + 1)
    
    # Update the user's token creation time directly in the database
    stmt = update(User).where(User.id == user.id).values(
        verification_token_created_at=token_created_at
    )
    await db_session.execute(stmt)
    await db_session.commit()
    
    # Attempt to verify with the token (should fail due to expiration)
    result = await UserService.verify_email_with_token(
        db_session, user.id, user.verification_token
    )
    
    assert result is False, "Verification should fail with an expired token"

# Test 3: Concurrent user creation performance
async def test_concurrent_user_creation_performance(db_session, email_service):
    """Test the system's ability to handle concurrent user creation."""
    import asyncio
    
    # Create 5 users concurrently
    async def create_user(index):
        user_data = {
            "nickname": f"concurrent_user_{index}_{uuid.uuid4()}",
            "email": f"concurrent{index}_{uuid.uuid4()}@example.com",
            "password": f"ConcurrentTest123!_{index}",
            "role": UserRole.AUTHENTICATED.name
        }
        return await UserService.create(db_session, user_data, email_service)
    
    # Create 5 users concurrently and measure time
    start_time = datetime.utcnow()
    users = await asyncio.gather(*[create_user(i) for i in range(5)])
    end_time = datetime.utcnow()
    
    # Verify all users were created
    assert all(user is not None for user in users), "All users should be created successfully"
    
    # Verify performance is reasonable (should take less than 2 seconds for 5 users)
    duration = (end_time - start_time).total_seconds()
    assert duration < 2, f"Creating 5 users took {duration} seconds, which exceeds the 2 second threshold"

# Test 4: User role-based access control
async def test_role_based_access_control(async_client, admin_token, manager_token, user_token):
    """Test that different user roles have appropriate access to endpoints."""
    # Define endpoints and expected access by role
    endpoints = [
        # (endpoint, method, admin_access, manager_access, user_access)
        ("/users/", "GET", 200, 200, 403),
        ("/roles/", "GET", 200, 200, 403),
        ("/metrics/", "GET", 200, 200, 403),
    ]
    
    for endpoint, method, admin_status, manager_status, user_status in endpoints:
        # Test admin access
        admin_response = await async_client.request(
            method, 
            endpoint, 
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_response.status_code == admin_status, f"Admin should get {admin_status} for {method} {endpoint}"
        
        # Test manager access
        manager_response = await async_client.request(
            method, 
            endpoint, 
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert manager_response.status_code == manager_status, f"Manager should get {manager_status} for {method} {endpoint}"
        
        # Test user access
        user_response = await async_client.request(
            method, 
            endpoint, 
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert user_response.status_code == user_status, f"User should get {user_status} for {method} {endpoint}"

# Test 5: Rate limiting for login attempts
async def test_login_rate_limiting(async_client, verified_user):
    """Test that login attempts are rate-limited to prevent brute force attacks."""
    # Attempt multiple rapid login requests
    form_data = {
        "username": verified_user.email,
        "password": "WrongPassword123!"  # Intentionally wrong
    }
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    # Make 10 rapid login attempts
    responses = []
    for _ in range(10):
        response = await async_client.post(
            "/login/", 
            data=urlencode(form_data), 
            headers=headers
        )
        responses.append(response)
    
    # Check if rate limiting was applied (some responses should be 429 Too Many Requests)
    rate_limited = any(response.status_code == 429 for response in responses)
    assert rate_limited, "Rate limiting should be applied after multiple rapid login attempts"

# Test 6: Password reset functionality
async def test_password_reset_functionality(db_session, user):
    """Test the complete password reset functionality."""
    # Store original password hash
    original_hash = user.hashed_password
    
    # Reset password
    new_password = "NewSecurePassword123!"
    reset_success = await UserService.reset_password(db_session, user.id, new_password)
    assert reset_success is True, "Password reset should succeed"
    
    # Verify password was changed
    updated_user = await UserService.get_by_id(db_session, user.id)
    assert updated_user.hashed_password != original_hash, "Password hash should be updated"
    
    # Verify login with new password works
    login_result = await UserService.login_user(db_session, user.email, new_password)
    assert login_result is not None, "Login with new password should succeed"
    
    # Verify login with old password fails
    old_password = "MySuperPassword$1234"  # Assuming this is the original password
    login_result = await UserService.login_user(db_session, user.email, old_password)
    assert login_result is None, "Login with old password should fail"

# Test 7: User search and filtering
async def test_user_search_and_filtering(async_client, admin_token, users_with_same_role_50_users):
    """Test the ability to search and filter users by various criteria."""
    # Test search by email domain
    response = await async_client.get(
        "/users/?email_domain=example.com",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    users = response.json()["items"]
    assert all("example.com" in user["email"] for user in users), "All returned users should have example.com email domain"
    
    # Test search by role
    response = await async_client.get(
        "/users/?role=AUTHENTICATED",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    users = response.json()["items"]
    assert all(user["role"] == "AUTHENTICATED" for user in users), "All returned users should have AUTHENTICATED role"
    
    # Test pagination
    response = await async_client.get(
        "/users/?skip=10&limit=5",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    users = response.json()["items"]
    assert len(users) == 5, "Should return exactly 5 users with limit=5"

# Test 8: User data validation on update
async def test_user_data_validation_on_update(async_client, admin_token, admin_user):
    """Test that user data validation works correctly during updates."""
    # Test cases with invalid data for updates
    test_cases = [
        {"field": "email", "value": "invalid-email", "expected_code": 422},
        {"field": "github_profile_url", "value": "not-a-url", "expected_code": 422},
        {"field": "linkedin_profile_url", "value": "not-a-url", "expected_code": 422},
    ]
    
    for case in test_cases:
        update_data = {case["field"]: case["value"]}
        response = await async_client.put(
            f"/users/{admin_user.id}", 
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == case["expected_code"], f"Expected validation error for {case['field']}: {case['value']}"

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
