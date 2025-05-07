from builtins import ValueError, any, bool, str, dict
from pydantic import BaseModel, EmailStr, Field, validator, root_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum
import uuid
import re
from app.models.user_model import UserRole
from app.utils.nickname_gen import generate_nickname


def validate_url(url: Optional[str]) -> Optional[str]:
    if url is None:
        return url
    url_regex = r'^https?:\/\/[^\s/$.?#].[^\s]*$'
    if not re.match(url_regex, url):
        raise ValueError('Invalid URL format')
    return url

class UserBase(BaseModel):
    email: EmailStr = Field(..., example="john.doe@example.com")
    nickname: Optional[str] = Field(None, min_length=3, pattern=r'^[\w-]+$', example=generate_nickname())
    first_name: Optional[str] = Field(None, example="John")
    last_name: Optional[str] = Field(None, example="Doe")
    bio: Optional[str] = Field(None, example="Experienced software developer specializing in web applications.")
    profile_picture_url: Optional[str] = Field(None, example="https://example.com/profiles/john.jpg")
    linkedin_profile_url: Optional[str] = Field(None, example="https://linkedin.com/in/johndoe")
    github_profile_url: Optional[str] = Field(None, example="https://github.com/johndoe")
    twitter_profile_url: Optional[str] = Field(None, example="https://twitter.com/johndoe")
    personal_website_url: Optional[str] = Field(None, example="https://johndoe.com")
    phone_number: Optional[str] = Field(None, example="+1234567890")
    date_of_birth: Optional[date] = Field(None, example="1990-01-01")
    location: Optional[str] = Field(None, example="New York, NY")
    skills: Optional[List[str]] = Field(None, example=["Python", "FastAPI", "SQL"])
    interests: Optional[List[str]] = Field(None, example=["Programming", "Reading", "Hiking"])
    education: Optional[List[Dict[str, Any]]] = Field(None, example=[
        {"institution": "University of Example", "degree": "Computer Science", "year": "2015"}
    ])
    work_experience: Optional[List[Dict[str, Any]]] = Field(None, example=[
        {"company": "Example Corp", "position": "Software Engineer", "start_date": "2016-01", "end_date": "2020-12"}
    ])
    preferred_language: Optional[str] = Field(None, example="English")
    timezone: Optional[str] = Field(None, example="America/New_York")
    profile_completion: Optional[int] = Field(None, example=85)
    role: UserRole

    _validate_urls = validator('profile_picture_url', 'linkedin_profile_url', 'github_profile_url', 
                             'twitter_profile_url', 'personal_website_url', pre=True, allow_reuse=True)(validate_url)
 
    class Config:
        from_attributes = True

class UserCreate(UserBase):
    email: EmailStr = Field(..., example="john.doe@example.com")
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[^A-Za-z0-9]', v):
            raise ValueError('Password must contain at least one special character')
        return v

class UserUpdate(UserBase):
    email: Optional[EmailStr] = Field(None, example="john.doe@example.com")
    nickname: Optional[str] = Field(None, min_length=3, pattern=r'^[\w-]+$', example="john_doe123")
    first_name: Optional[str] = Field(None, example="John")
    last_name: Optional[str] = Field(None, example="Doe")
    bio: Optional[str] = Field(None, example="Experienced software developer specializing in web applications.")
    profile_picture_url: Optional[str] = Field(None, example="https://example.com/profiles/john.jpg")
    linkedin_profile_url: Optional[str] = Field(None, example="https://linkedin.com/in/johndoe")
    github_profile_url: Optional[str] = Field(None, example="https://github.com/johndoe")
    twitter_profile_url: Optional[str] = Field(None, example="https://twitter.com/johndoe")
    personal_website_url: Optional[str] = Field(None, example="https://johndoe.com")
    phone_number: Optional[str] = Field(None, example="+1234567890")
    date_of_birth: Optional[date] = Field(None, example="1990-01-01")
    location: Optional[str] = Field(None, example="New York, NY")
    skills: Optional[List[str]] = Field(None, example=["Python", "FastAPI", "SQL"])
    interests: Optional[List[str]] = Field(None, example=["Programming", "Reading", "Hiking"])
    education: Optional[List[Dict[str, Any]]] = Field(None, example=[
        {"institution": "University of Example", "degree": "Computer Science", "year": "2015"}
    ])
    work_experience: Optional[List[Dict[str, Any]]] = Field(None, example=[
        {"company": "Example Corp", "position": "Software Engineer", "start_date": "2016-01", "end_date": "2020-12"}
    ])
    preferred_language: Optional[str] = Field(None, example="English")
    timezone: Optional[str] = Field(None, example="America/New_York")
    role: Optional[str] = Field(None, example="AUTHENTICATED")

    @root_validator(pre=True)
    def check_at_least_one_value(cls, values):
        if not any(values.values()):
            raise ValueError("At least one field must be provided for update")
        return values

class UserResponse(UserBase):
    id: uuid.UUID = Field(..., example=uuid.uuid4())
    email: EmailStr = Field(..., example="john.doe@example.com")
    nickname: Optional[str] = Field(None, min_length=3, pattern=r'^[\w-]+$', example=generate_nickname())    
    is_professional: Optional[bool] = Field(default=False, example=True)
    profile_completion: Optional[int] = Field(None, example=85)
    role: UserRole

class LoginRequest(BaseModel):
    email: str = Field(..., example="john.doe@example.com")
    password: str = Field(..., example="Secure*1234")

class ErrorResponse(BaseModel):
    error: str = Field(..., example="Not Found")
    details: Optional[str] = Field(None, example="The requested resource was not found.")

class ProfileCompletionSection(BaseModel):
    """Schema for profile completion section details."""
    basic_info: int = Field(..., example=85)
    professional_info: int = Field(..., example=60)
    preferences: int = Field(..., example=33)


class ProfileFieldStatus(BaseModel):
    """Schema for profile field completion status."""
    basic_info: Dict[str, bool] = Field(...)
    professional_info: Dict[str, bool] = Field(...)
    preferences: Dict[str, bool] = Field(...)


class ProfileSectionUpdate(BaseModel):
    """Schema for updating a specific section of a user's profile."""
    # Basic info fields
    first_name: Optional[str] = Field(None, example="John")
    last_name: Optional[str] = Field(None, example="Doe")
    bio: Optional[str] = Field(None, example="Experienced software developer specializing in web applications.")
    profile_picture_url: Optional[str] = Field(None, example="https://example.com/profiles/john.jpg")
    phone_number: Optional[str] = Field(None, example="+1234567890")
    date_of_birth: Optional[date] = Field(None, example="1990-01-01")
    location: Optional[str] = Field(None, example="New York, NY")
    
    # Professional info fields
    linkedin_profile_url: Optional[str] = Field(None, example="https://linkedin.com/in/johndoe")
    github_profile_url: Optional[str] = Field(None, example="https://github.com/johndoe")
    twitter_profile_url: Optional[str] = Field(None, example="https://twitter.com/johndoe")
    personal_website_url: Optional[str] = Field(None, example="https://johndoe.com")
    skills: Optional[List[str]] = Field(None, example=["Python", "FastAPI", "SQL"])
    education: Optional[List[Dict[str, Any]]] = Field(None, example=[
        {"institution": "University of Example", "degree": "Computer Science", "year": "2015"}
    ])
    work_experience: Optional[List[Dict[str, Any]]] = Field(None, example=[
        {"company": "Example Corp", "position": "Software Engineer", "start_date": "2016-01", "end_date": "2020-12"}
    ])
    
    # Preferences fields
    interests: Optional[List[str]] = Field(None, example=["Programming", "Reading", "Hiking"])
    preferred_language: Optional[str] = Field(None, example="English")
    timezone: Optional[str] = Field(None, example="America/New_York")
    
    _validate_urls = validator('profile_picture_url', 'linkedin_profile_url', 'github_profile_url', 
                             'twitter_profile_url', 'personal_website_url', pre=True, allow_reuse=True)(validate_url)


class ProfileCompletionDetails(BaseModel):
    """Schema for detailed profile completion information."""
    overall_completion: int = Field(..., example=65)
    section_completion: ProfileCompletionSection
    field_status: ProfileFieldStatus


class PaginationParams(BaseModel):
    """Schema for pagination parameters."""
    page: int = Field(1, ge=1, description="Page number, starting from 1")
    size: int = Field(10, ge=1, le=100, description="Number of items per page")


class UserSearchParams(BaseModel):
    """Schema for user search parameters."""
    email: Optional[str] = Field(None, description="Email to search for")
    nickname: Optional[str] = Field(None, description="Nickname to search for")
    name: Optional[str] = Field(None, description="Name (first or last) to search for")
    role: Optional[str] = Field(None, description="Role to filter by")
    created_after: Optional[datetime] = Field(None, description="Filter users created after this date")
    created_before: Optional[datetime] = Field(None, description="Filter users created before this date")
    sort_by: Optional[str] = Field("created_at", description="Field to sort by")
    sort_order: Optional[str] = Field("desc", description="Sort order (asc or desc)")


class UserListResponse(BaseModel):
    items: List[UserResponse] = Field(..., example=[{
        "id": uuid.uuid4(), "nickname": generate_nickname(), "email": "john.doe@example.com",
        "first_name": "John", "bio": "Experienced developer", "role": "AUTHENTICATED",
        "last_name": "Doe", "profile_completion": 85,
        "profile_picture_url": "https://example.com/profiles/john.jpg", 
        "linkedin_profile_url": "https://linkedin.com/in/johndoe", 
        "github_profile_url": "https://github.com/johndoe"
    }])
    total: int = Field(..., example=100)
    page: int = Field(..., example=1)
    size: int = Field(..., example=10)
