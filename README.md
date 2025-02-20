# EasyModel

A simplified SQLModel-based ORM for async database operations in Python. EasyModel provides a clean and intuitive interface for common database operations while leveraging the power of SQLModel and SQLAlchemy.

## Features

- Easy-to-use async database operations
- Built on top of SQLModel and SQLAlchemy
- PostgreSQL support with asyncpg
- Common CRUD operations out of the box
- Session management with context managers
- Type hints for better IDE support
- Automatic `updated_at` field updates

## Installation

```bash
pip install easy-model
```

## Quick Start

```python
from easy_model import EasyModel, init_db
from sqlmodel import Field
from typing import Optional
from datetime import datetime

# Define your model
class User(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    email: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default=None)  # Will be automatically updated

# Initialize your database (creates all tables)
async def setup():
    await init_db()

# Use it in your async code
async def main():
    # Create a new user
    user = await User.insert({
        "username": "john_doe",
        "email": "john@example.com"
    })

    # Get user by id
    user = await User.get_by_id(1)

    # Get user by attribute
    user = await User.get_by_attribute(username="john_doe")

    # Update user - updated_at will be automatically set
    updated_user = await User.update(1, {
        "email": "new_email@example.com"
    })
    print(f"Last update: {updated_user.updated_at}")

    # Delete user
    success = await User.delete(1)
```

## Configuration

Set your database connection details using environment variables:

```bash
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=your_database
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
