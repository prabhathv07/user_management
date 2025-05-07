"""
Tests for the profile management feature.
"""
import json
import pytest
from datetime import date
from uuid import UUID
from fastapi import status, Depends
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user_model import User, UserRole
from app.dependencies import get_current_active_user, get_db
from app.main import app
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_get_own_profile(async_client: AsyncClient, db_session: AsyncSession, user_token):
    """Test retrieving the current user's profile."""
    response = await async_client.get("/api/me/profile", headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 200
    data = response.json()
    assert "email" in data
    assert "first_name" in data
    assert "last_name" in data


@pytest.mark.asyncio
async def test_update_own_profile(async_client: AsyncClient, db_session: AsyncSession, user_token):
    """Test updating the current user's profile."""
    update_data = {
        "first_name": "Updated",
        "last_name": "User",
        "bio": "This is my updated bio",
        "location": "New York",
        "phone_number": "123-456-7890"
    }
    
    response = await async_client.put("/api/me/profile", json=update_data, headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Updated"
    assert data["last_name"] == "User"
    assert data["bio"] == "This is my updated bio"
    assert data["location"] == "New York"
    assert data["phone_number"] == "123-456-7890"


@pytest.mark.asyncio
async def test_update_profile_section(async_client: AsyncClient, db_session: AsyncSession, user_token):
    """Test updating a specific section of the user's profile."""
    # Test updating basic info section
    basic_info = {
        "first_name": "Section",
        "last_name": "Update",
        "bio": "Updated via section API",
        "phone_number": "987-654-3210",
        "location": "San Francisco"
    }
    
    response = await async_client.put("/api/me/profile/basic_info", json=basic_info, headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Section"
    assert data["last_name"] == "Update"
    assert data["bio"] == "Updated via section API"
    assert data["phone_number"] == "987-654-3210"
    assert data["location"] == "San Francisco"
    
    # Test updating professional info section
    professional_info = {
        "skills": ["Python", "FastAPI", "SQLAlchemy"],
        "work_experience": [
            {
                "company": "Tech Corp",
                "position": "Senior Developer",
                "start_date": "2020-01-01",
                "end_date": "2023-01-01"
            }
        ],
        "education": [
            {
                "institution": "Tech University",
                "degree": "Computer Science",
                "graduation_year": 2019
            }
        ]
    }
    
    response = await async_client.put("/api/me/profile/professional_info", json=professional_info, headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 200
    data = response.json()
    assert "Python" in data["skills"]
    assert data["work_experience"][0]["company"] == "Tech Corp"
    assert data["education"][0]["institution"] == "Tech University"
    
    # Test updating preferences section
    preferences = {
        "interests": ["Coding", "Reading", "Hiking"],
        "preferred_language": "en",
        "timezone": "America/New_York"
    }
    
    response = await async_client.put("/api/me/profile/preferences", json=preferences, headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 200
    data = response.json()
    assert "Coding" in data["interests"]
    assert data["preferred_language"] == "en"
    assert data["timezone"] == "America/New_York"


@pytest.mark.asyncio
async def test_get_profile_completion(async_client: AsyncClient, db_session: AsyncSession, user_token):
    """Test retrieving profile completion details."""
    response = await async_client.get("/api/me/profile-completion", headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 200
    data = response.json()
    assert "overall_completion" in data
    assert "section_completion" in data
    assert "field_status" in data
    
    # Verify section structure
    assert "basic_info" in data["section_completion"]
    assert "professional_info" in data["section_completion"]
    assert "preferences" in data["section_completion"]
    
    # Verify field status structure
    assert "basic_info" in data["field_status"]
    assert "professional_info" in data["field_status"]
    assert "preferences" in data["field_status"]


@pytest.mark.asyncio
async def test_calculate_profile_completion(db_session: AsyncSession, user: User):
    """Test the profile completion calculation logic."""
    # Initial profile with minimal info
    user.calculate_profile_completion()
    initial_completion = user.profile_completion
    
    # Update with more profile information
    user.bio = "This is my detailed bio with lots of information about me."
    user.location = "New York"
    user.phone_number = "123-456-7890"
    user.date_of_birth = date(1990, 1, 1)
    user.skills = ["Python", "FastAPI", "SQLAlchemy"]
    user.interests = ["Coding", "Reading", "Hiking"]
    user.preferred_language = "en"
    user.timezone = "America/New_York"
    
    # Recalculate completion
    user.calculate_profile_completion()
    updated_completion = user.profile_completion
    
    # Completion should increase with more information
    assert updated_completion > initial_completion
    
    # Get detailed completion info
    completion_details = user.get_profile_completion_details()
    assert completion_details["overall_completion"] == updated_completion
    assert "section_completion" in completion_details
    assert len(completion_details["section_completion"]) == 3


@pytest.mark.asyncio
async def test_invalid_section_update(async_client: AsyncClient, db_session: AsyncSession, user_token):
    """Test updating an invalid profile section."""
    response = await async_client.put("/api/me/profile/invalid_section", json={"field": "value"}, headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 400
    assert "Invalid section" in response.json()["detail"]
