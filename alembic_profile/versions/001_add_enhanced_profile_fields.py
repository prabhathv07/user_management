"""Add enhanced profile fields

Revision ID: 001
Revises: 
Create Date: 2025-05-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to the users table
    op.add_column('users', sa.Column('twitter_profile_url', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('personal_website_url', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('phone_number', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('date_of_birth', sa.Date(), nullable=True))
    op.add_column('users', sa.Column('location', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('skills', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('users', sa.Column('interests', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('users', sa.Column('education', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('users', sa.Column('work_experience', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('users', sa.Column('preferred_language', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('timezone', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('profile_completion', sa.Integer(), nullable=True, server_default='0'))
    
    # Change bio column type from String(500) to Text for longer bios
    op.alter_column('users', 'bio', type_=sa.Text(), existing_type=sa.String(length=500))


def downgrade() -> None:
    # Revert bio column type back to String(500)
    op.alter_column('users', 'bio', type_=sa.String(length=500), existing_type=sa.Text())
    
    # Drop all the new columns
    op.drop_column('users', 'profile_completion')
    op.drop_column('users', 'timezone')
    op.drop_column('users', 'preferred_language')
    op.drop_column('users', 'work_experience')
    op.drop_column('users', 'education')
    op.drop_column('users', 'interests')
    op.drop_column('users', 'skills')
    op.drop_column('users', 'location')
    op.drop_column('users', 'date_of_birth')
    op.drop_column('users', 'phone_number')
    op.drop_column('users', 'personal_website_url')
    op.drop_column('users', 'twitter_profile_url')
