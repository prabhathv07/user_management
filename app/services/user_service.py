from builtins import Exception, bool, classmethod, int, str
from datetime import datetime, timezone
import secrets
from typing import Optional, Dict, List, Any
from pydantic import ValidationError
from sqlalchemy import func, null, update, select, or_, and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_email_service, get_settings
from app.models.user_model import User
from app.schemas.user_schemas import UserCreate, UserUpdate
from app.utils.nickname_gen import generate_nickname
from app.utils.security import generate_verification_token, hash_password, verify_password
from uuid import UUID
from app.services.email_service import EmailService
from app.models.user_model import UserRole
import logging

settings = get_settings()
logger = logging.getLogger(__name__)

class UserService:
    @classmethod
    async def _execute_query(cls, session: AsyncSession, query):
        try:
            result = await session.execute(query)
            await session.commit()
            return result
        except SQLAlchemyError as e:
            logger.error(f"Database error: {e}")
            await session.rollback()
            return None

    @classmethod
    async def _fetch_user(cls, session: AsyncSession, **filters) -> Optional[User]:
        query = select(User).filter_by(**filters)
        result = await session.execute(query)
        return result.scalars().first()

    @classmethod
    async def get_by_id(cls, session: AsyncSession, user_id: UUID) -> Optional[User]:
        return await cls._fetch_user(session, id=user_id)

    @classmethod
    async def get_by_nickname(cls, session: AsyncSession, nickname: str) -> Optional[User]:
        return await cls._fetch_user(session, nickname=nickname)

    @classmethod
    async def get_by_email(cls, session: AsyncSession, email: str) -> Optional[User]:
        return await cls._fetch_user(session, email=email)

    @classmethod
    async def create(cls, session: AsyncSession, user_data: Dict[str, str], email_service: EmailService) -> Optional[User]:
        try:
            validated_data = UserCreate(**user_data).model_dump()
            existing_user = await cls.get_by_email(session, validated_data['email'])
            if existing_user:
                logger.error("User with given email already exists.")
                return None
            validated_data['hashed_password'] = hash_password(validated_data.pop('password'))
            new_user = User(**validated_data)
            new_nickname = generate_nickname()
            while await cls.get_by_nickname(session, new_nickname):
                new_nickname = generate_nickname()
            new_user.nickname = new_nickname
            logger.info(f"User Role: {new_user.role}")
            user_count = await cls.count(session)
            new_user.role = UserRole.ADMIN if user_count == 0 else UserRole.ANONYMOUS            
            if new_user.role == UserRole.ADMIN:
                new_user.email_verified = True

            else:
                new_user.verification_token = generate_verification_token()
                await email_service.send_verification_email(new_user)

            session.add(new_user)
            await session.commit()
            return new_user
        except ValidationError as e:
            logger.error(f"Validation error during user creation: {e}")
            return None

    @classmethod
    async def update(cls, session: AsyncSession, user_id: UUID, update_data: Dict[str, str]) -> Optional[User]:
        try:
            validated_data = UserUpdate(**update_data).model_dump(exclude_unset=True)

            if 'password' in validated_data:
                validated_data['hashed_password'] = hash_password(validated_data.pop('password'))
            
            # Handle JSON fields properly
            for field in ['skills', 'interests', 'education', 'work_experience']:
                if field in validated_data and validated_data[field] is not None:
                    # Ensure these are stored as proper JSON
                    if isinstance(validated_data[field], str):
                        try:
                            import json
                            validated_data[field] = json.loads(validated_data[field])
                        except json.JSONDecodeError:
                            # If not valid JSON, store as a single-item list
                            validated_data[field] = [validated_data[field]]
            
            query = update(User).where(User.id == user_id).values(**validated_data).execution_options(synchronize_session="fetch")
            await cls._execute_query(session, query)
            
            # Fetch the updated user
            user = await cls.get_by_id(session, user_id)
            if user:
                # Calculate and update profile completion percentage
                user.calculate_profile_completion()
                session.add(user)
                await session.commit()
                return user
            else:
                logger.error(f"User {user_id} not found after update attempt.")
            return None
        except Exception as e:  # Broad exception handling for debugging
            logger.error(f"Error during user update: {e}")
            return None

    @classmethod
    async def delete(cls, session: AsyncSession, user_id: UUID) -> bool:
        user = await cls.get_by_id(session, user_id)
        if not user:
            logger.info(f"User with ID {user_id} not found.")
            return False
        await session.delete(user)
        await session.commit()
        return True

    @classmethod
    async def list_users(cls, session: AsyncSession, skip: int = 0, limit: int = 10) -> List[User]:
        query = select(User).offset(skip).limit(limit)
        result = await cls._execute_query(session, query)
        return result.scalars().all() if result else []

    @classmethod
    async def register_user(cls, session: AsyncSession, user_data: Dict[str, str], get_email_service) -> Optional[User]:
        return await cls.create(session, user_data, get_email_service)
    

    @classmethod
    async def login_user(cls, session: AsyncSession, email: str, password: str) -> Optional[User]:
        user = await cls.get_by_email(session, email)
        if user:
            if user.email_verified is False:
                return None
            if user.is_locked:
                return None
            if verify_password(password, user.hashed_password):
                user.failed_login_attempts = 0
                user.last_login_at = datetime.now(timezone.utc)
                session.add(user)
                await session.commit()
                return user
            else:
                await cls.increment_failed_login_attempts(session, user)
        return None

    @classmethod
    async def is_account_locked(cls, session: AsyncSession, email: str) -> bool:
        user = await cls.get_by_email(session, email)
        return user.is_locked if user else False


    @classmethod
    async def reset_password(cls, session: AsyncSession, user_id: UUID, new_password: str) -> bool:
        hashed_password = hash_password(new_password)
        user = await cls.get_by_id(session, user_id)
        if user:
            user.hashed_password = hashed_password
            user.failed_login_attempts = 0  # Resetting failed login attempts
            user.is_locked = False  # Unlocking the user account, if locked
            session.add(user)
            await session.commit()
            return True
        return False

    @classmethod
    async def verify_email_with_token(cls, session: AsyncSession, user_id: UUID, token: str) -> bool:
        user = await cls.get_by_id(session, user_id)
        if user and user.verification_token == token:
            user.email_verified = True
            user.verification_token = None  # Clear the token once used
            user.role = UserRole.AUTHENTICATED
            session.add(user)
            await session.commit()
            return True
        return False

    @classmethod
    async def count(cls, session: AsyncSession) -> int:
        """
        Count the number of users in the database.

        :param session: The AsyncSession instance for database access.
        :return: The count of users.
        """
        query = select(func.count()).select_from(User)
        result = await session.execute(query)
        count = result.scalar()
        return count
    
    @classmethod
    async def unlock_user_account(cls, session: AsyncSession, user_id: UUID) -> bool:
        user = await cls.get_by_id(session, user_id)
        if user and user.is_locked:
            user.is_locked = False
            user.failed_login_attempts = 0  # Optionally reset failed login attempts
            session.add(user)
            await session.commit()
            return True
        return False
        
    @classmethod
    async def search_users(cls, session: AsyncSession, search_params: Dict[str, Any], skip: int = 0, limit: int = 10) -> List[User]:
        """
        Search for users based on various criteria.
        
        Parameters:
        - session: Database session
        - search_params: Dictionary containing search parameters
            - search_term: General search term to match against name, email, or nickname
            - role: Filter by user role (ADMIN, MANAGER, AUTHENTICATED, etc.)
            - email_verified: Filter by email verification status (True/False)
            - is_locked: Filter by account lock status (True/False)
            - created_after: Filter users created after this date
            - created_before: Filter users created before this date
        - skip: Number of records to skip (for pagination)
        - limit: Maximum number of records to return
        
        Returns:
        - List of User objects matching the search criteria
        """
        try:
            # Start with a base query
            query = select(User)
            
            # Apply filters based on search parameters
            filters = []
            
            # General search term (searches across multiple fields)
            if "search_term" in search_params and search_params["search_term"]:
                search_term = f"%{search_params['search_term']}%"
                term_filter = or_(
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                    User.email.ilike(search_term),
                    User.nickname.ilike(search_term)
                )
                filters.append(term_filter)
            
            # Role filter
            if "role" in search_params and search_params["role"]:
                filters.append(User.role == search_params["role"])
            
            # Email verification status
            if "email_verified" in search_params and search_params["email_verified"] is not None:
                filters.append(User.email_verified == search_params["email_verified"])
            
            # Account lock status
            if "is_locked" in search_params and search_params["is_locked"] is not None:
                filters.append(User.is_locked == search_params["is_locked"])
            
            # Date range filters
            if "created_after" in search_params and search_params["created_after"]:
                filters.append(User.created_at >= search_params["created_after"])
                
            if "created_before" in search_params and search_params["created_before"]:
                filters.append(User.created_at <= search_params["created_before"])
            
            # Apply all filters to the query
            if filters:
                query = query.filter(and_(*filters))
            
            # Apply pagination
            query = query.offset(skip).limit(limit)
            
            # Execute the query
            result = await session.execute(query)
            return result.scalars().all() if result else []
            
        except Exception as e:
            logger.error(f"Error during user search: {e}")
            return []
    
    @classmethod
    async def get_profile_completion(cls, session: AsyncSession, user_id: UUID) -> Optional[dict]:
        """
        Get detailed profile completion information for a user.
        
        Parameters:
        - session: Database session
        - user_id: UUID of the user
        
        Returns:
        - Dictionary with profile completion details or None if user not found
        """
        user = await cls.get_by_id(session, user_id)
        if not user:
            return None
            
        # Calculate current profile completion
        user.calculate_profile_completion()
        
        # Get detailed completion information
        completion_details = user.get_profile_completion_details()
        
        return completion_details
    
    @classmethod
    async def update_profile_section(cls, session: AsyncSession, user_id: UUID, section: str, section_data: Dict[str, Any]) -> Optional[User]:
        """
        Update a specific section of a user's profile.
        
        Parameters:
        - session: Database session
        - user_id: UUID of the user
        - section: Section to update ('basic_info', 'professional_info', 'preferences')
        - section_data: Dictionary containing the data for the section
        
        Returns:
        - Updated User object or None if user not found or update failed
        """
        user = await cls.get_by_id(session, user_id)
        if not user:
            return None
            
        try:
            # Map section to corresponding fields
            section_field_map = {
                'basic_info': [
                    'first_name', 'last_name', 'bio', 'profile_picture_url',
                    'phone_number', 'date_of_birth', 'location'
                ],
                'professional_info': [
                    'linkedin_profile_url', 'github_profile_url', 'twitter_profile_url',
                    'personal_website_url', 'skills', 'work_experience', 'education'
                ],
                'preferences': [
                    'interests', 'preferred_language', 'timezone'
                ]
            }
            
            # Check if section is valid
            if section not in section_field_map:
                logger.error(f"Invalid profile section: {section}")
                return None
                
            # Filter data to only include fields in the specified section
            update_data = {k: v for k, v in section_data.items() if k in section_field_map[section]}
            
            # Update user with filtered data
            return await cls.update(session, user_id, update_data)
            
        except Exception as e:
            logger.error(f"Error updating profile section {section}: {e}")
            return None
    
    @classmethod
    async def count_search_results(cls, session: AsyncSession, search_params: Dict[str, Any]) -> int:
        """
        Count the number of users matching the search criteria.
        
        Parameters:
        - session: Database session
        - search_params: Dictionary containing search parameters (same as search_users)
        
        Returns:
        - Total count of matching users
        """
        try:
            # Start with a base query
            query = select(func.count()).select_from(User)
            
            # Apply filters based on search parameters
            filters = []
            
            # General search term
            if "search_term" in search_params and search_params["search_term"]:
                search_term = f"%{search_params['search_term']}%"
                term_filter = or_(
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                    User.email.ilike(search_term),
                    User.nickname.ilike(search_term)
                )
                filters.append(term_filter)
            
            # Role filter
            if "role" in search_params and search_params["role"]:
                filters.append(User.role == search_params["role"])
            
            # Email verification status
            if "email_verified" in search_params and search_params["email_verified"] is not None:
                filters.append(User.email_verified == search_params["email_verified"])
            
            # Account lock status
            if "is_locked" in search_params and search_params["is_locked"] is not None:
                filters.append(User.is_locked == search_params["is_locked"])
            
            # Date range filters
            if "created_after" in search_params and search_params["created_after"]:
                filters.append(User.created_at >= search_params["created_after"])
                
            if "created_before" in search_params and search_params["created_before"]:
                filters.append(User.created_at <= search_params["created_before"])
            
            # Apply all filters to the query
            if filters:
                query = query.filter(and_(*filters))
            
            # Execute the query
            result = await session.execute(query)
            count = result.scalar()
            return count or 0
            
        except Exception as e:
            logger.error(f"Error during search result count: {e}")
            return 0

    @classmethod
    async def increment_failed_login_attempts(cls, db: AsyncSession, user: User) -> None:
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.max_login_attempts:
            user.is_locked = True
        await db.commit()
        await db.refresh(user)
        
    @classmethod
    async def update_professional_status(cls, session: AsyncSession, user_id: UUID, is_professional: bool, email_service: EmailService = None) -> Optional[User]:
        """
        Update a user's professional status and send notification if status is upgraded to professional.
        
        Parameters:
        - session: Database session
        - user_id: UUID of the user
        - is_professional: New professional status
        - email_service: Optional email service for sending notifications
        
        Returns:
        - Updated User object or None if user not found or update failed
        """
        try:
            user = await cls.get_by_id(session, user_id)
            if not user:
                logger.error(f"User with ID {user_id} not found")
                return None
                
            # Determine if we need to notify the user (only when upgrading)
            send_notification = not user.is_professional and is_professional

            # Update the status and timestamp
            user.update_professional_status(is_professional)

            # Persist changes
            await session.commit()
            await session.refresh(user)

            # Send notification after commit to avoid transactional side-effects
            if send_notification and email_service:
                try:
                    await email_service.send_professional_status_notification(user)
                except Exception as e:
                    logger.error(f"Failed to send notification: {e}")
                    
            return user
        except Exception as e:
            logger.error(f"Error updating professional status: {e}")
            await session.rollback()
            return None
