import click
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, User
from app.database import get_db
import csv

@click.group()
def cli():
    pass

@cli.command()
@click.option('--confirm', is_flag=True, help='Confirm database reset')
def reset_db(confirm):
    """Drop all tables and recreate"""
    if confirm:
        engine = create_engine('postgresql://postgres:postgres@localhost:5432/app')
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        click.echo('Database reset complete!')
    else:
        click.echo('Add --confirm to execute reset')

@cli.command()
@click.argument('email')
@click.argument('new_role')
def change_role(email, new_role):
    """Change user role"""
    db = next(get_db())
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.role = new_role
        db.commit()
        click.echo(f'Updated {email} role to {new_role}')
    else:
        click.echo('User not found')

@cli.command()
@click.argument('csv_path')
def import_users(csv_path):
    """Bulk import users from CSV"""
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            db = next(get_db())
            for row in reader:
                user = User(
                    email=row['email'],
                    hashed_password=row['password'],
                    role=row.get('role', 'authenticated')
                )
                db.add(user)
            db.commit()
        click.echo(f'Imported {reader.line_num - 1} users')
    except Exception as e:
        click.echo(f'Error: {str(e)}')

if __name__ == '__main__':
    cli()
