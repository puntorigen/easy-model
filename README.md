# EasyModel

A simplified SQLModel-based ORM for async database operations in Python. EasyModel provides a clean and intuitive interface for common database operations while leveraging the power of SQLModel and SQLAlchemy.

## Features

- Easy-to-use async database operations
- Built on top of SQLModel and SQLAlchemy
- Support for both PostgreSQL and SQLite databases
- Common CRUD operations out of the box
- Session management with context managers
- Type hints for better IDE support
- Automatic `created_at` and `updated_at` field management

## Installation

```bash
pip install async-easy-model
```

## Quick Start

```python
from async_easy_model import EasyModel, init_db, db_config
from sqlmodel import Field
from typing import Optional
from datetime import datetime

# Configure your database (choose one)
# For SQLite:
db_config.configure_sqlite("database.db")
# For PostgreSQL:
db_config.configure_postgres(
    user="your_user",
    password="your_password",
    host="localhost",
    port="5432",
    database="your_database"
)

# Define your model
class User(EasyModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    email: str
    # Note: created_at and updated_at fields are automatically included
    # and managed by EasyModel, so you don't need to define them.

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
    
    # Update user - updated_at will be automatically set
    updated_user = await User.update(1, {
        "email": "new_email@example.com"
    })
    print(f"Last update: {updated_user.updated_at}")

    # Delete user
    success = await User.delete(1)
```

## Configuration

You can configure the database connection in two ways:

### 1. Using Environment Variables

For PostgreSQL:
```bash
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=your_database
```

For SQLite:
```bash
SQLITE_FILE=database.db
```

### 2. Using Configuration Methods

For PostgreSQL:
```python
from async_easy_model import db_config

db_config.configure_postgres(
    user="your_user",
    password="your_password",
    host="localhost",
    port="5432",
    database="your_database"
)
```

For SQLite:
```python
from async_easy_model import db_config

db_config.configure_sqlite("database.db")
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
