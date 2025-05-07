"""
Search schema for user search and filtering functionality.

This module defines the Pydantic models used for searching and filtering users.
"""

from builtins import bool, str
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.user_model import UserRole

class UserSearchParams(BaseModel):
    """
    Schema for user search parameters.
    
    This model defines the parameters that can be used to search and filter users.
    """
    search_term: Optional[str] = Field(None, description="General search term to match against name, email, or nickname")
    role: Optional[UserRole] = Field(None, description="Filter by user role")
    email_verified: Optional[bool] = Field(None, description="Filter by email verification status")
    is_locked: Optional[bool] = Field(None, description="Filter by account lock status")
    created_after: Optional[datetime] = Field(None, description="Filter users created after this date")
    created_before: Optional[datetime] = Field(None, description="Filter users created before this date")
    
    class Config:
        """Configuration for the UserSearchParams model."""
        json_schema_extra = {
            "example": {
                "search_term": "john",
                "role": "AUTHENTICATED",
                "email_verified": True,
                "is_locked": False,
                "created_after": "2023-01-01T00:00:00Z",
                "created_before": "2023-12-31T23:59:59Z"
            }
        }
