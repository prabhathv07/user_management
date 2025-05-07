from builtins import bool, int, str, dict
from datetime import datetime, date
from enum import Enum
import uuid
from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, func, Enum as SQLAlchemyEnum, Date, Text
)
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from typing import List, Optional

class UserRole(Enum):
    """Enumeration of user roles within the application, stored as ENUM in the database."""
    ANONYMOUS = "ANONYMOUS"
    AUTHENTICATED = "AUTHENTICATED"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"

class User(Base):
    """
    Represents a user within the application, corresponding to the 'users' table in the database.
    This class uses SQLAlchemy ORM for mapping attributes to database columns efficiently.
    
    Attributes:
        id (UUID): Unique identifier for the user.
        nickname (str): Unique nickname for privacy, required.
        email (str): Unique email address, required.
        email_verified (bool): Flag indicating if the email has been verified.
        hashed_password (str): Hashed password for security, required.
        first_name (str): Optional first name of the user.
        last_name (str): Optional first name of the user.

        bio (str): Optional biographical information.
        profile_picture_url (str): Optional URL to a profile picture.
        linkedin_profile_url (str): Optional LinkedIn profile URL.
        github_profile_url (str): Optional GitHub profile URL.
        twitter_profile_url (str): Optional Twitter/X profile URL.
        personal_website_url (str): Optional personal website URL.
        phone_number (str): Optional phone number.
        date_of_birth (date): Optional date of birth.
        location (str): Optional location/address.
        skills (JSONB): Optional JSON array of skills.
        interests (JSONB): Optional JSON array of interests.
        education (JSONB): Optional JSON array of education history.
        work_experience (JSONB): Optional JSON array of work experience.
        preferred_language (str): Optional preferred language.
        timezone (str): Optional timezone.
        profile_completion (int): Profile completion percentage.
        role (UserRole): Role of the user within the application.
        is_professional (bool): Flag indicating professional status.
        professional_status_updated_at (datetime): Timestamp of last professional status update.
        last_login_at (datetime): Timestamp of the last login.
        failed_login_attempts (int): Count of failed login attempts.
        is_locked (bool): Flag indicating if the account is locked.
        created_at (datetime): Timestamp when the user was created, set by the server.
        updated_at (datetime): Timestamp of the last update, set by the server.

    Methods:
        lock_account(): Locks the user account.
        unlock_account(): Unlocks the user account.
        verify_email(): Marks the user's email as verified.
        has_role(role_name): Checks if the user has a specified role.
        update_professional_status(status): Updates the professional status and logs the update time.
        calculate_profile_completion(): Calculates and updates the profile completion percentage.
        get_profile_completion_details(): Returns detailed information about profile completion status.
    """
    __tablename__ = "users"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nickname: Mapped[str] = Column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = Column(String(255), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = Column(String(100), nullable=True)
    last_name: Mapped[str] = Column(String(100), nullable=True)
    bio: Mapped[str] = Column(Text, nullable=True)
    profile_picture_url: Mapped[str] = Column(String(255), nullable=True)
    linkedin_profile_url: Mapped[str] = Column(String(255), nullable=True)
    github_profile_url: Mapped[str] = Column(String(255), nullable=True)
    twitter_profile_url: Mapped[str] = Column(String(255), nullable=True)
    personal_website_url: Mapped[str] = Column(String(255), nullable=True)
    phone_number: Mapped[str] = Column(String(20), nullable=True)
    date_of_birth: Mapped[date] = Column(Date, nullable=True)
    location: Mapped[str] = Column(String(255), nullable=True)
    skills: Mapped[dict] = Column(JSONB, nullable=True, default=dict)
    interests: Mapped[dict] = Column(JSONB, nullable=True, default=dict)
    education: Mapped[dict] = Column(JSONB, nullable=True, default=dict)
    work_experience: Mapped[dict] = Column(JSONB, nullable=True, default=dict)
    preferred_language: Mapped[str] = Column(String(50), nullable=True)
    timezone: Mapped[str] = Column(String(50), nullable=True)
    profile_completion: Mapped[int] = Column(Integer, default=0)
    role: Mapped[UserRole] = Column(SQLAlchemyEnum(UserRole, name='UserRole', create_constraint=True), nullable=False)
    is_professional: Mapped[bool] = Column(Boolean, default=False)
    professional_status_updated_at: Mapped[datetime] = Column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime] = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts: Mapped[int] = Column(Integer, default=0)
    is_locked: Mapped[bool] = Column(Boolean, default=False)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    verification_token = Column(String, nullable=True)
    email_verified: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    hashed_password: Mapped[str] = Column(String(255), nullable=False)


    def __repr__(self) -> str:
        """Provides a readable representation of a user object."""
        return f"<User {self.nickname}, Role: {self.role.name}>"

    def lock_account(self):
        self.is_locked = True

    def unlock_account(self):
        self.is_locked = False

    def verify_email(self):
        self.email_verified = True

    def has_role(self, role_name: UserRole) -> bool:
        return self.role == role_name

    def update_professional_status(self, status: bool):
        """Updates the professional status and logs the update time."""
        self.is_professional = status
        self.professional_status_updated_at = func.now()
        
    def calculate_profile_completion(self) -> int:
        """Calculates and updates the profile completion percentage based on filled profile fields."""
        # Define fields that contribute to profile completion
        profile_fields = [
            self.first_name, self.last_name, self.bio, self.profile_picture_url,
            self.linkedin_profile_url, self.github_profile_url, self.twitter_profile_url,
            self.personal_website_url, self.phone_number, self.date_of_birth,
            self.location, self.skills, self.interests, self.education,
            self.work_experience, self.preferred_language, self.timezone
        ]
        
        # Count non-empty fields
        filled_fields = sum(1 for field in profile_fields if field)
        
        # Calculate percentage (rounded to nearest integer)
        total_fields = len(profile_fields)
        completion_percentage = round((filled_fields / total_fields) * 100)
        
        # Update the profile_completion field
        self.profile_completion = completion_percentage
        
        return completion_percentage
    
    def get_profile_completion_details(self) -> dict:
        """Returns detailed information about profile completion status."""
        # Define all profile fields and their completion status
        profile_fields = {
            "basic_info": {
                "first_name": bool(self.first_name),
                "last_name": bool(self.last_name),
                "profile_picture": bool(self.profile_picture_url),
                "bio": bool(self.bio),
                "phone_number": bool(self.phone_number),
                "date_of_birth": bool(self.date_of_birth),
                "location": bool(self.location),
            },
            "professional_info": {
                "linkedin_profile": bool(self.linkedin_profile_url),
                "github_profile": bool(self.github_profile_url),
                "twitter_profile": bool(self.twitter_profile_url),
                "personal_website": bool(self.personal_website_url),
                "skills": bool(self.skills),
                "work_experience": bool(self.work_experience),
                "education": bool(self.education),
            },
            "preferences": {
                "interests": bool(self.interests),
                "preferred_language": bool(self.preferred_language),
                "timezone": bool(self.timezone),
            }
        }
        
        # Calculate completion percentage for each section
        section_completion = {}
        for section, fields in profile_fields.items():
            completed = sum(1 for field_complete in fields.values() if field_complete)
            total = len(fields)
            section_completion[section] = round((completed / total) * 100)
        
        return {
            "overall_completion": self.profile_completion,
            "section_completion": section_completion,
            "field_status": profile_fields
        }
