# Profile Management Feature

## Overview

The Profile Management feature enhances the user management system by providing comprehensive user profile capabilities, including:

1. **Enhanced User Profiles**: Additional fields for personal and professional information
2. **Profile Completion Tracking**: Automatic calculation of profile completeness
3. **Self-Service Profile Updates**: User-friendly APIs for updating profile information
4. **Section-Based Updates**: Ability to update specific sections of a profile

## Database Schema Changes

The feature adds the following fields to the `users` table:

| Field Name | Type | Description |
|------------|------|-------------|
| twitter_profile_url | VARCHAR(255) | User's Twitter profile URL |
| personal_website_url | VARCHAR(255) | User's personal website URL |
| phone_number | VARCHAR(20) | User's phone number |
| date_of_birth | DATE | User's date of birth |
| location | VARCHAR(255) | User's location (city, country, etc.) |
| skills | JSONB | Array of user's professional skills |
| interests | JSONB | Array of user's personal interests |
| education | JSONB | Array of education history entries |
| work_experience | JSONB | Array of work experience entries |
| preferred_language | VARCHAR(50) | User's preferred language |
| timezone | VARCHAR(50) | User's timezone |
| profile_completion | INTEGER | Percentage of profile completion (0-100) |

Additionally, the `bio` field is changed from VARCHAR(500) to TEXT to allow for longer biographies.

## API Endpoints

### Get Current User Profile

```
GET /me/profile
```

Returns the current user's complete profile information.

**Response**: UserResponse object with all profile fields

### Update Current User Profile

```
PUT /me/profile
```

Updates the current user's profile with the provided information.

**Request Body**: UserUpdate object with fields to update
**Response**: Updated UserResponse object

### Update Profile Section

```
PUT /me/profile/{section}
```

Updates a specific section of the current user's profile.

**Path Parameters**:
- `section`: Section to update (basic_info, professional_info, preferences)

**Request Body**: ProfileSectionUpdate object with fields to update
**Response**: Updated UserResponse object

### Get Profile Completion Details

```
GET /me/profile-completion
```

Returns detailed information about the current user's profile completion status.

**Response**: ProfileCompletionDetails object with:
- `overall_completion`: Overall profile completion percentage
- `sections`: Array of section completion details
  - `name`: Section name
  - `completion_percentage`: Section completion percentage
  - `fields`: Array of field status objects
    - `name`: Field name
    - `completed`: Whether the field is completed
    - `importance`: Field importance weight

## Data Structures

### Education Entry

```json
{
  "institution": "University Name",
  "degree": "Degree Name",
  "field_of_study": "Field of Study",
  "graduation_year": 2020,
  "description": "Optional description"
}
```

### Work Experience Entry

```json
{
  "company": "Company Name",
  "position": "Job Title",
  "start_date": "2020-01-01",
  "end_date": "2023-01-01",
  "current": false,
  "description": "Job description"
}
```

### Skills and Interests

These are stored as simple arrays of strings:

```json
["Python", "FastAPI", "SQLAlchemy"]
```

## Profile Completion Calculation

Profile completion is calculated based on the presence and completeness of various profile fields. Fields are grouped into three sections:

1. **Basic Information** (40% weight)
   - First name, last name, email, bio, profile picture, phone, date of birth, location

2. **Professional Information** (40% weight)
   - LinkedIn profile, GitHub profile, Twitter profile, personal website, skills, work experience, education

3. **Preferences** (20% weight)
   - Interests, preferred language, timezone

The overall completion percentage is calculated as a weighted average of these sections.

## Implementation Details

### User Model

The User model has been enhanced with new fields and methods:

- `calculate_profile_completion()`: Calculates and updates the profile completion percentage
- `get_profile_completion_details()`: Returns detailed information about profile completion status

### User Service

The UserService class has been extended with methods for profile management:

- `get_profile_completion()`: Gets detailed profile completion information
- `update_profile_section()`: Updates a specific section of a user's profile

## Database Migration

To apply the database schema changes, run:

```bash
# For direct SQL application (if Alembic is not working)
psql postgresql://user:password@localhost/myappdb -f migrations/profile_management.sql

# For Alembic migration (when fixed)
alembic upgrade head
```

## Testing

Comprehensive tests have been added in `tests/test_profile_management.py` to verify the functionality of the profile management features.

Run the tests with:

```bash
pytest tests/test_profile_management.py -v
```
